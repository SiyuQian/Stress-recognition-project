from django.shortcuts import render
from . import tasks
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from demoapp.models import Request, Response, Uuid
from django.db import transaction
from django.db.models import Avg
from demoapp.utils import validate_http_request_method, create_json_response, normalize_data, round_floats, get_time_diff, generate_csv
import neurokit2 as nk
import pandas as pd
import json
import logging
import numpy as np
import matplotlib.pyplot as plt

# Get an instance of a logger
logger = logging.getLogger(__name__)

@csrf_exempt
def index(request):
    return render(request, "index.html")

@csrf_exempt
def uuid_index(request):
    status_code = 200
    status = 'success'
    message = ''

    if validate_http_request_method(request, 'POST', True) == False :
        return create_json_response(400, 'error', message = 'Bad request! This API endpoint only handles POST request.')

    body_unicode = request.body.decode('utf-8')

    # validate if the request body is in JSON format
    try:
        # { "uuid": "33d84b2a-9e39-11eb-a8b3-0242ac130003" }
        body = json.loads(body_unicode)
    except Exception as e:
        logger.error(str(e))
        return create_json_response(400, 'error', message = 'Bad request! The request data have to be in a valid JSON format.')

    uuid = Uuid.objects.filter(uuid = body['uuid'])

    logger.info('checking UUID availaliy')

    # UUID is valid
    if uuid.count() == 0 :
        try:
            uuid = Uuid(uuid = body['uuid'])
            uuid.save()
        except Exception as e:
            return create_json_response(status_code, 'error', message = str(e))

        status = 'success'
        message = 'The UUID is vaild.'
    else:
        # UUID is invalid
        status = 'error'
        message = 'The UUID already existed.'

    return create_json_response(status_code, status, message = message)

@csrf_exempt
def stress_index(request):
    # success HTTP status code as default value
    status_code         = 200
    sample_rate         = 50
    mode                = 'hrv'
    diff                = 0
    message             = ''
    dataframe           = None
    hr_threshold        = 1.05
    base_data_length    = 21
    hrv_threshold       = 1.09
    status              = 'success'
    status_basic        = 'success'
    status_sliding      = 'success'
    data                = {}
    
    if validate_http_request_method(request, 'POST', True) == False:
        return create_json_response(400, 'error', message = 'Bad request! This API endpoint only handles POST request.')

    try:
        # Handle the request from the client-end
        body_unicode = request.body.decode('utf-8')

        # Convert the json into a dataframe
        body = json.loads(body_unicode)

        # Convert the json into a dataframe for further processing
        dataframe = pd.DataFrame.from_dict(body)

        request_model = Request()
        request_model.device = dataframe['Device'].iloc[0]
        request_model.hr = round(dataframe['HR'].astype(int).mean(axis=0), 2)
        request_model.time = 0
        request_model.timedate = 0
        request_model.uuid = dataframe['uuid'].iloc[0]
        request_model.ppg = round(dataframe['PPG'].astype(float).mean(axis=0), 2)
        request_model.save()

    except Exception as e:
        return create_json_response(500, 'error', data = { 'raw_request_body': request.data }, message = str(e))

    # @todo: validate the mode value, the mode parameter should be optional
    mode = request.GET.get('mode')

    # Get the first value of the device column (as the device code value will never change from a same device)
    device_code = dataframe['Device'].iloc[0]

    # Get the first value of the uuid column (as the device code value will never change from a same experiment)
    uuid = dataframe['uuid'].iloc[0]
    filtered_response = Response.objects.filter(device_code=device_code, uuid=uuid)

    # Calculate the average hear rate based on HR column
    hr_mean = round(dataframe['HR'].astype(float).mean(axis=0), 2)
    # Calculate the HRV RMSSD value from the base data (first n mins, e.g. 5)
    hrv_rmssd_mean = list(filtered_response[1:base_data_length].aggregate(Avg('hrv_rmssd')).values())[0]
    base_hr_mean = list(filtered_response[1:base_data_length].aggregate(Avg('mean')).values())[0]

    if mode == 'hr' :
        # compare the mean value with recent request
        if filtered_response.count() > 0 :
            # extract the recent mean
            diff = hr_mean - base_hr_mean

        # if the changes is bigger than the pre-defined threshold
        if diff >= hr_threshold  :
            status = 'warning'
            message = 'HRV RMSSD has been changed significantly. You probably under stress.'

        data = {
            'mode': mode,
            'device': device_code,
            'uuid': uuid,
            'HR_MEAN': hr_mean
        }
    elif mode == 'hrv':
        # logger.info('==================')
        # logger.info(dataframe['PPG'])
        # logger.info(type(dataframe['PPG']))
        # logger.info(dataframe.dtypes)
        # logger.info(dataframe['PPG'].astype(float).div(1000000).to_numpy())
        # logger.info(type(dataframe['PPG'].astype(float).div(1000000)))
        # logger.info('==================')
        ppd_std = dataframe['PPG'].astype(float).std(skipna = True)
        ppg_mean = dataframe['PPG'].astype(float).mean(skipna = True)

        normalized_ppg_data = dataframe['PPG'].astype(float).apply(normalize_data, mean = ppg_mean, std = ppd_std)

        # logger.info(normalized_ppg_data)

        # Clear the noise
        ppg_clean = nk.ppg_clean(normalized_ppg_data, sampling_rate=sample_rate)

        # Peaks
        peaks = nk.ppg_findpeaks(ppg_clean, sampling_rate=sample_rate)

        # Compute HRV indices
        try:
            hrv_indices = nk.hrv(peaks, sampling_rate=sample_rate, show=False)
        except ValueError:
            status = 'error'
            message = 'Please wear the polarOH1 properly.'
            data = {
                'mode': mode,
                'device': device_code,
                'uuid': uuid,
                'hr_mean': hr_mean
            }
            data['message'] = message
            return create_json_response(status_code, status, data, message = message)

        result = hrv_indices.to_json()
        parsed = json.loads(result)

        # compare the mean value with recent request
        if filtered_response.count() > base_data_length :
            # Method: Comparing with Base Line
            # extract the recent mean
            if parsed['HRV_RMSSD']['0'] * hrv_threshold < hrv_rmssd_mean and hr_mean > base_hr_mean * hr_threshold:
                status = 'basic_warning'
                status_basic = 'basic_warning'
                message = 'HRV RMSSD has been changed significantly. You probably under stress.'

            sliding_window_size = base_data_length
            sliding_window_entry = filtered_response.count() - base_data_length

            hrv_rmssd_sliding_window_mean = list(filtered_response[sliding_window_entry:sliding_window_entry + sliding_window_size].aggregate(Avg('hrv_rmssd')).values())[0]
            hr_sliding_window_mean = list(filtered_response[sliding_window_entry:sliding_window_entry + sliding_window_size].aggregate(Avg('mean')).values())[0]
            
            # Method: Sliding window
            if parsed['HRV_RMSSD']['0'] * hrv_threshold < hrv_rmssd_sliding_window_mean and hr_mean > hr_sliding_window_mean * hr_threshold:
                status = 'sliding_warning'
                status_sliding = 'sliding_warning'
                message = 'HRV RMSSD has been changed significantly. You probably under stress.'
        
        data = {
            'mode': mode,
            'device': device_code,
            'uuid': uuid,
            'hr_mean': hr_mean,
            'HRV': parsed
        }

    # add message into the data dict
    data['message'] = message

    mean_value = hr_mean

    # Store response into Mysql database
    response_model = Response()
    response_model.device_code = device_code
    response_model.uuid = uuid
    response_model.mode = mode
    response_model.status_basic = status_basic
    response_model.status_sliding = status_sliding
    response_model.hr_mean = mean_value
    response_model.hrv_pnn50 = parsed['HRV_pNN50']['0']
    response_model.hrv_rmssd = parsed['HRV_RMSSD']['0']
    response_model.response_body = data
    response_model.save()

    return create_json_response(status_code, status, data, message = message)


@csrf_exempt
def report_index(request):
    if validate_http_request_method(request, 'GET', True) == False :
        return create_json_response(400, 'error', message = 'Bad request! This API endpoint only handles GET request.')
    
    # The API needs two params to display the diagram and information about the experiment
    # device_code, uuid
    device_code = request.GET.get('device_code')
    uuid = request.GET.get('uuid')
    x_axis_start = int(request.GET.get('x-axis-start', "1"))
    x_axis_end = int(request.GET.get('x-axis-end', "1"))

    start = ''
    end = ''
    experiment_length = ''
    row_number = 1
    base_data_length = 21
    outlier_threshold = 3

    if not device_code or not uuid:
        return create_json_response(500, 'error', message = 'Bad request! You have to identify device code and uuid to render the page correctly.')

    responses = Response.objects.filter(device_code=device_code, uuid=uuid)
    # Calculate the HRV RMSSD value from the base data (first n mins, e.g. 5)
    hrv_rmssd_mean = list(responses[1:base_data_length].aggregate(Avg('hrv_rmssd')).values())[0]
    records = responses.count()
    if records:
        start = responses.first().created_at
        end = responses.last().created_at
        experiment_length = get_time_diff(int(start.strftime('%s')), int(end.strftime('%s')))
        rows = responses.values()
        detected_stress_x = []
        detected_stress_y = []
        # Preprocess the value
        
        for row in rows:
            current_row_number = row_number-1
            # Data smoothing, Remove outliers
            if float(rows[current_row_number]['hrv_rmssd']) > hrv_rmssd_mean * outlier_threshold:
                rows[current_row_number]['hrv_rmssd'] = hrv_rmssd_mean 

            # Add minute column
            rows[current_row_number]['minute'] = row_number

            # Form detected point
            if rows[current_row_number]['status_basic'] == 'warning':
                detected_stress_x.append(rows[current_row_number]['minute'])
                detected_stress_y.append(rows[current_row_number]['hrv_rmssd'])
            
            row_number+=1
        
        df = pd.DataFrame(rows)
        df['minute'] = df['minute'].astype(int)
        df['hrv_rmssd'] = df['hrv_rmssd'].astype(float)

        # fig, ax = plt.subplots()
        # df.plot(x='minute', y='hrv_rmssd').line()
        # filePath = "./demoapp/static/images/" + device_code + "/" + uuid + "/"
        # mkDir(filePath)
        # fig.saveFig(filePath + 'line_chart.png')
        generate_csv(rows, device_code, uuid, 'response')

    return render(request, "report.html", {
        'device_code': device_code,
        'uuid': uuid,
        'records': records,
        'start': start,
        'end': end,
        'experiment_length': experiment_length,
        'data': df['hrv_rmssd'].tolist()[x_axis_start:x_axis_end],
        'hr': df['hr_mean'].tolist()[x_axis_start:x_axis_end],
        'labels': df['minute'].tolist()[x_axis_start:x_axis_end],
        'detected_stress_x': detected_stress_x,
        'detected_stress_y': detected_stress_y
    })

# @csrf_exempt
# def ml_index(request):
#     status_code = 200
#     status = 'success'
    

#     uuid = request.GET.get('uuid')
#     device_code = request.GET.get('device_code')

#     # Read data from database
#     # Filter the data with device code and uuid
#     filtered_response = Response.objects.filter(device_code=device_code, uuid=uuid)

#     # Convert data to dataframe
#     df = pd.DataFrame(list(filtered_response.values()))

#     # Initialize empty dataframe with column names
#     dataframe_hrv = pd.DataFrame()

#     # Process data with sklearn ML algorithms
#     df = df.reset_index(drop=True)

#     # Transform response body data
#     for index, row in df['response_body'].iteritems():
#         data = json.loads(json.dumps(row))
#         tmp_df = pd.json_normalize(data)

#         dataframe_hrv = dataframe_hrv.append(tmp_df)

#     logger.info(dataframe_hrv.columns)

#     # Append stress column into the dataframe by heart rate
#     dataframe_hrv['stress'] = dataframe_hrv.apply(lambda row: stress_classifier(row), axis=1)
        
#     logger.info(dataframe_hrv.shape)
    
#     # 'HRV.HRV_ULF.0', 'HRV.HRV_VLF.0', are removed because all the values are None
#     selected_X_columns = ['HRV.HRV_S.0',
#        'HRV.HRV_AI.0', 'HRV.HRV_Ca.0', 'HRV.HRV_Cd.0', 'HRV.HRV_GI.0',
#        'HRV.HRV_HF.0', 'HRV.HRV_LF.0', 'HRV.HRV_PI.0', 'HRV.HRV_SI.0',
#        'HRV.HRV_C1a.0', 'HRV.HRV_C1d.0', 'HRV.HRV_C2a.0', 'HRV.HRV_C2d.0',
#        'HRV.HRV_CSI.0', 'HRV.HRV_CVI.0', 'HRV.HRV_HFn.0', 'HRV.HRV_HTI.0',
#        'HRV.HRV_LFn.0', 'HRV.HRV_PAS.0', 'HRV.HRV_PIP.0', 'HRV.HRV_PSS.0',
#        'HRV.HRV_SD1.0', 'HRV.HRV_SD2.0', 'HRV.HRV_VHF.0',
#        'HRV.HRV_ApEn.0', 'HRV.HRV_CVNN.0', 'HRV.HRV_CVSD.0',
#        'HRV.HRV_IALS.0', 'HRV.HRV_LFHF.0', 'HRV.HRV_LnHF.0', 'HRV.HRV_SD1a.0',
#        'HRV.HRV_SD1d.0', 'HRV.HRV_SD2a.0', 'HRV.HRV_SD2d.0', 'HRV.HRV_SDNN.0',
#        'HRV.HRV_SDSD.0', 'HRV.HRV_TINN.0', 'HRV.HRV_IQRNN.0',
#        'HRV.HRV_MCVNN.0', 'HRV.HRV_MadNN.0', 'HRV.HRV_RMSSD.0',
#        'HRV.HRV_SDNNa.0', 'HRV.HRV_SDNNd.0', 'HRV.HRV_pNN20.0',
#        'HRV.HRV_pNN50.0', 'HRV.HRV_MeanNN.0', 'HRV.HRV_SD1SD2.0',
#        'HRV.HRV_SampEn.0', 'HRV.HRV_MedianNN.0', 'HRV.HRV_CSI_Modified.0'
#     ]

#     for column_name in selected_X_columns:
#         logger.info(dataframe_hrv[column_name])
#         dataframe_hrv[column_name] = dataframe_hrv[column_name].apply(round_floats)

#     X = dataframe_hrv[selected_X_columns]
#     y = dataframe_hrv['stress']

#     # tpot_classifer = do_tpot(generations=10, population_size=20, X=X, y=y)

#     prediction = random_forest_classfier(X=X, y=y, test_size=0.2, random_state=0, debug=True)

#     logger.info(prediction)

#     return create_json_response(status_code, status, data, message = filtered_response.count())