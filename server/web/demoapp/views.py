from django.shortcuts import render
from . import tasks
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from demoapp.models import Request, Response, Uuid, EventLabel
from django.db import transaction
from django.db.models import Avg, Count
from demoapp.utils import validate_http_request_method, create_json_response, get_base_line_size, get_normalized_ppg_data, round_floats, get_time_diff, generate_csv, calculate_hrv, detect_stress, store_response
import neurokit2 as nk
import pandas as pd
import json
import logging
import csv
import numpy as np
import matplotlib.pyplot as plt

# Get an instance of a logger
logger = logging.getLogger(__name__)

class Constant(object):
    HTTP_SUCCESS_STATUS_CODE        = 200
    SAMPLE_RATE                     = 50
    HRV_MODE                        = 'hrv'
    HR_MODE                         = 'hr'
    FREQUENCY                       = 12
    BASELINE_SIZE                   = 21
    HR_THRESHOLD                    = 1.05
    HRV_THRESHOLD                   = 1.09
    STATUS_SUCCESS                  = 'success'
    DATA                            = {}

@csrf_exempt
def index(request):
    return render(request, "index.html")

@csrf_exempt
def uuid_index(request):
    status_code = Constant.HTTP_SUCCESS_STATUS_CODE
    status = Constant.STATUS_SUCCESS
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
    status_code         = Constant.HTTP_SUCCESS_STATUS_CODE
    sample_rate         = Constant.SAMPLE_RATE
    mode                = Constant.HRV_MODE
    diff                = 0
    message             = ''
    dataframe           = None
    hr_threshold        = Constant.HR_THRESHOLD
    base_data_length    = get_base_line_size(Constant.FREQUENCY)
    hrv_threshold       = Constant.HRV_THRESHOLD
    status              = Constant.STATUS_SUCCESS
    status_basic        = Constant.STATUS_SUCCESS
    status_sliding      = Constant.STATUS_SUCCESS
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
        normalized_ppg_data = get_normalized_ppg_data(dataframe)

        # Compute HRV indices
        try:
            hrv_indices = calculate_hrv(normalized_ppg_data, sample_rate)
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

        # Convert HRV output into json format
        result = hrv_indices.to_json()
        parsed = json.loads(result)

        stress_info = detect_stress(filtered_response, base_data_length, parsed, hrv_threshold, hrv_rmssd_mean, hr_mean, base_hr_mean, hr_threshold)
        status = stress_info['status']
        status_basic = stress_info['status_basic']
        status_sliding = stress_info['status_sliding']
        message = stress_info['message']

        data = {
            'mode': mode,
            'device': device_code,
            'uuid': uuid,
            'hr_mean': hr_mean,
            'HRV': parsed
        }

    # add message into the data dict
    data['message'] = message

    # Store response into Mysql database
    store_response(device_code, uuid, mode, status_basic, status_sliding, hr_mean, parsed['HRV_pNN50']['0'], parsed['HRV_RMSSD']['0'], data)
    return create_json_response(status_code, status, data, message = message)

@csrf_exempt
def process(request):
    # success HTTP status code as default value
    status_code         = Constant.HTTP_SUCCESS_STATUS_CODE
    sample_rate         = Constant.SAMPLE_RATE
    mode                = Constant.HRV_MODE
    message             = ''
    dataframe           = None
    hr_threshold        = Constant.HR_THRESHOLD
    base_data_length    = get_base_line_size(Constant.FREQUENCY)
    hrv_threshold       = Constant.HRV_THRESHOLD
    status              = Constant.STATUS_SUCCESS
    status_basic        = Constant.STATUS_SUCCESS
    status_sliding      = Constant.STATUS_SUCCESS
    data                = {}
    secondStorage       = 0
    isSend              = False

    if validate_http_request_method(request, 'POST', True) == False :
        return create_json_response(400, 'error', message = 'Bad request! This API endpoint only handles POST request.')

    # device_code = request.POST.get('device_code')
    
    uuid = request.POST.get('uuid')
    frequency = int(request.POST.get('frequency'))

    uuid_model = Uuid(uuid = uuid)
    uuid_model.save()

    ppg_raw_file = request.FILES['ppg_raw']

    decoded_file = ppg_raw_file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    dataframe = pd.DataFrame()

    for row in reader:
        device_code = row['Device']
        dataframe = dataframe.append(row, ignore_index=True)
 
        # Get the second of the time
        second = int(row['Time'].split(':')[2])
        
        if second is not secondStorage:
            secondStorage = second
            isSend = False

        # Per frequency to process HRV
        if (second + 1) % frequency == 0 and not isSend:
            request_model = Request()
            request_model.device = dataframe['Device'].iloc[0]
            request_model.hr = round(dataframe['HR'].astype(int).mean(axis=0), 2)
            request_model.time = 0
            request_model.timedate = 0
            request_model.uuid = uuid
            request_model.ppg = round(dataframe['PPG'].astype(float).mean(axis=0), 2)
            request_model.save()

            normalized_ppg_data = get_normalized_ppg_data(dataframe)
            filtered_response = Response.objects.filter(device_code=device_code, uuid=uuid)

            # Calculate the average hear rate based on HR column
            hr_mean = round(dataframe['HR'].astype(float).mean(axis=0), 2)

            # Compute HRV indices
            try:
                hrv_indices = calculate_hrv(normalized_ppg_data, sample_rate)
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

            # Convert HRV output into json format
            result = hrv_indices.to_json()
            parsed = json.loads(result)
            
            data = {
                'mode': mode,
                'device': device_code,
                'uuid': uuid,
                'hr_mean': hr_mean,
                'HRV': parsed
            }

            # add message into the data dict
            data['message'] = message
            
            if filtered_response.count() > 0:
                # Calculate the HRV RMSSD value from the base data (first n mins, e.g. 5)
                hrv_rmssd_mean = list(filtered_response[1:base_data_length].aggregate(Avg('hrv_rmssd')).values())[0]
                base_hr_mean = list(filtered_response[1:base_data_length].aggregate(Avg('mean')).values())[0]

                stress_info = detect_stress(
                    filtered_response,
                    base_data_length,
                    parsed,
                    hrv_threshold,
                    hrv_rmssd_mean,
                    hr_mean,
                    base_hr_mean,
                    hr_threshold
                )
                status = stress_info['status']
                status_basic = stress_info['status_basic']
                status_sliding = stress_info['status_sliding']
                message = stress_info['message']

            # Store response into Mysql database
            store_response(device_code, uuid, mode, status_basic, status_sliding, hr_mean, parsed['HRV_pNN50']['0'], parsed['HRV_RMSSD']['0'], data)
            # Reset dataframe
            dataframe = pd.DataFrame()
            isSend = True

    return redirect('/report?device_code=' + device_code + '&' + 'uuid=' + uuid)

@csrf_exempt
def tests_index(request):
    distinct_requests = Request.objects.all().values('device', 'uuid').annotate(dcount=Count('uuid'))

    return render(request, 'list.html', {
        'requests': distinct_requests
    })


@csrf_exempt
def report_index(request):
    if validate_http_request_method(request, 'GET', True) == False :
        return create_json_response(400, 'error', message = 'Bad request! This API endpoint only handles GET request.')
    
    # The API needs two params to display the diagram and information about the experiment
    # device_code, uuid
    device_code = request.GET.get('device_code')
    uuid = request.GET.get('uuid')
    x_axis_start = int(request.GET.get('x-axis-start', '0'))
    x_axis_end = int(request.GET.get('x-axis-end', "1"))

    start = ''
    end = ''
    experiment_length = ''
    row_number = 1
    base_data_length = 21
    outlier_threshold = 3
    x_axis_labels = []

    if not device_code or not uuid:
        return create_json_response(500, 'error', message = 'Bad request! You have to identify device code and uuid to render the page correctly.')

    responses = Response.objects.filter(device_code=device_code, uuid=uuid)
    requests = Request.objects.filter(device=device_code, uuid=uuid)
    requests_df = pd.DataFrame(requests.values())

    # Calculate the HRV RMSSD value from the base data (first n mins, e.g. 5)
    hrv_rmssd_mean = list(responses[1:base_data_length].aggregate(Avg('hrv_rmssd')).values())[0]
    records = responses.count()

    if not records:
        return render(request, 'error.html', {})

    if records:
        if x_axis_end == 1:
            x_axis_end = records

        start = responses.first().created_at
        end = responses.last().created_at
        # experiment_length = get_time_diff(int(start.strftime('%s')), int(end.strftime('%s')))
        rows = responses.values()
        detected_stress_x_basic = []
        detected_stress_y_basic = []
        detected_stress_x_sliding = []
        detected_stress_y_sliding = []
        event_labels_short_hand = []
        event_labels_value = []

        # Preprocess the value
        
        for row in rows:
            current_row_number = row_number-1
            # Data smoothing, Remove outliers
            if float(rows[current_row_number]['hrv_rmssd']) > hrv_rmssd_mean * outlier_threshold:
                rows[current_row_number]['hrv_rmssd'] = hrv_rmssd_mean 

            # Add row number column
            rows[current_row_number]['row_number'] = row_number

            # Create detected points
            if rows[current_row_number]['status_basic'] == 'warning' or rows[current_row_number]['status_basic'] == 'basic_warning':
                detected_stress_x_basic.append(rows[current_row_number]['row_number'])
                detected_stress_y_basic.append(rows[current_row_number]['hrv_rmssd'])
            
            # Create detected points generated by sliding window algorithm
            if rows[current_row_number]['status_sliding'] == 'sliding_warning':
                detected_stress_x_sliding.append(rows[current_row_number]['row_number'])
                detected_stress_y_sliding.append(rows[current_row_number]['hrv_rmssd'])
            
            row_number+=1
        
        df = pd.DataFrame(rows)
        df['row_number'] = df['row_number'].astype(int)
        df['hrv_rmssd'] = df['hrv_rmssd'].astype(float)

        # fig, ax = plt.subplots()
        # df.plot(x='row_number', y='hrv_rmssd').line()
        # filePath = "./demoapp/static/images/" + device_code + "/" + uuid + "/"
        # mkDir(filePath)
        # fig.saveFig(filePath + 'line_chart.png')
        generate_csv(rows, device_code, uuid, 'response')

    event_labels = EventLabel.objects.filter(device_code=device_code, uuid=uuid)
    if event_labels.count() > 0:
        for label in event_labels:
            event_labels_short_hand.append(label.short_hand)
            event_labels_value.append(int(label.value))

    x_axis_labels = df['row_number'].tolist()[x_axis_start:x_axis_end]
    x_axis_labels.insert(0, 0)

    return render(request, "report.html", {
        'device_code': device_code,
        'uuid': uuid,
        'records': records,
        'start': start,
        'end': end,
        'ppg_data': requests_df['ppg'].tolist()[x_axis_start:x_axis_end],
        'data': df['hrv_rmssd'].tolist()[x_axis_start:x_axis_end],
        'hr': df['hr_mean'].tolist()[x_axis_start:x_axis_end],
        'labels': x_axis_labels,
        'detected_stress_x_basic': detected_stress_x_basic,
        'detected_stress_y_basic': detected_stress_y_basic,
        'detected_stress_x_sliding': detected_stress_x_sliding,
        'detected_stress_y_sliding': detected_stress_y_sliding,
        'stress_labels': event_labels.values('short_hand', 'name').order_by('short_hand').distinct(),
        'event_labels_short_hand': event_labels_short_hand,
        'event_labels_value' : event_labels_value
    })

@csrf_exempt
def report_add_label_index(request):
    if validate_http_request_method(request, 'POST', True) == False :
        return create_json_response(400, 'error', message = 'Bad request! This API endpoint only handles POST request.')

    device_code = request.POST.get('device_code')
    uuid = request.POST.get('uuid')
    event_short_hand = request.POST.get('label_short_hand')
    event_label_name = request.POST.get('event_label_name')
    event_label_value = request.POST.get('event_label_value')

    if not event_label_name or not event_label_value or not event_short_hand:
        return create_json_response(500, 'error', message = 'Bad request! You have to identify device code and uuid to render the page correctly.')

    try:
        event_label_model = EventLabel()
        event_label_model.uuid = uuid
        event_label_model.device_code = device_code
        event_label_model.name = event_label_name
        event_label_model.short_hand = event_short_hand
        event_label_model.value = event_label_value
        event_label_model.save()
    except Exception as e:
        logger.info(e)

    return redirect('/report?device_code=' + device_code + '&' + 'uuid=' + uuid)

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