from django.shortcuts import render
from . import tasks
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from demoapp.models import Request, Response, Uuid
from django.db.models import Avg
from demoapp.utils import validate_http_request_method, create_json_response, convert_unit, round_floats, stress_classifier, do_tpot, random_forest_classfier
import neurokit2 as nk
import pandas as pd
import json
import logging

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
    status_code = 200
    mode = 'hrv'
    diff = 0
    status = 'success'
    message = ''
    dataframe = None
    hr_threshold = 3
    data = {}

    if validate_http_request_method(request, 'POST', True) == False:
        return create_json_response(400, 'error', message = 'Bad request! This API endpoint only handles POST request.')

    try:
        # Handle the request from the client-end
        body_unicode = request.body.decode('utf-8')

        # Convert the json into a dataframe
        body = json.loads(body_unicode)

        # Store the request into Mysql
        request_model = Request()
        request_model.request_body = body
        request_model.save()

        # Convert the json into a dataframe for further processing
        dataframe = pd.DataFrame.from_dict(body)
    except Exception as e:
        return create_json_response(500, 'error', data = { 'raw_request_body': request.data }, message = str(e))

    # @todo: validate the mode value, the mode parameter should be optional
    mode = request.GET.get('mode')

    # Get the first value of the device column (as the device code value will never change from a same device)
    device_code = dataframe['Device'].iloc[0]

    # Get the first value of the uuid column (as the device code value will never change from a same experiment)
    uuid = dataframe['uuid'].iloc[0]

    # Calculate the average hear rate based on HR column
    hr_mean = round(dataframe['HR'].astype(float).mean(axis=0), 2)

    if mode == 'hr' :
        filtered_response = Response.objects.filter(device_code=device_code, uuid=uuid)

        # compare the mean value with recent request
        if filtered_response.count() > 0 :
            # extract the recent mean
            diff = hr_mean - list(filtered_response.aggregate(Avg('mean')).values())[0]

        # if the changes is bigger than the pre-defined threshold
        if diff >= hr_threshold  :
            status = 'warning'
            message = 'HR has been changed siginificantly, you probably in a stress.'


        data = {
            'mode': mode,
            'device': device_code,
            'uuid': uuid,
            'HR_MEAN': hr_mean
        }
    elif mode == 'hrv':
        # logger.info('==================')
        # logger.info(dataframe['PPG'])
        # logger.info(type['PPG'])
        # logger.info(dataframe['PPG'].astype(float).div(1000000).to_numpy())
        # logger.info(type(dataframe['PPG'].astype(float).div(1000000)))
        # logger.info('==================')

        # Clear the noise
        ppg_clean = nk.ppg_clean(dataframe['PPG'].apply(convert_unit), sampling_rate=50)

        # Peaks
        peaks = nk.ppg_findpeaks(ppg_clean, sampling_rate=50)

        # Compute HRV indices
        hrv_indices = nk.hrv(peaks, sampling_rate=50, show=False)
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

    mean_value = hr_mean if mode == 'hr' and hr_mean != None else parsed['HRV_MeanNN']['0']

    # Store response into Mysql database
    response_model = Response()
    response_model.device_code = device_code
    response_model.uuid = uuid
    response_model.mode = mode
    response_model.mean = mean_value
    response_model.response_body = data
    response_model.save()

    return create_json_response(status_code, status, data, message = message)

@csrf_exempt
def ml_index(request):
    status_code = 200
    status = 'success'
    

    uuid = request.GET.get('uuid')
    device_code = request.GET.get('device_code')

    # Read data from database
    # Filter the data with device code and uuid
    filtered_response = Response.objects.filter(device_code=device_code, uuid=uuid)

    # Convert data to dataframe
    df = pd.DataFrame(list(filtered_response.values()))

    # Initialize empty dataframe with column names
    dataframe_hrv = pd.DataFrame()

    # Process data with sklearn ML algorithms
    df = df.reset_index(drop=True)

    # Transform response body data
    for index, row in df['response_body'].iteritems():
        data = json.loads(json.dumps(row))
        tmp_df = pd.json_normalize(data)

        dataframe_hrv = dataframe_hrv.append(tmp_df)

    logger.info(dataframe_hrv.columns)

    # Append stress column into the dataframe by heart rate
    dataframe_hrv['stress'] = dataframe_hrv.apply(lambda row: stress_classifier(row), axis=1)
        
    logger.info(dataframe_hrv.shape)
    
    # 'HRV.HRV_ULF.0', 'HRV.HRV_VLF.0', are removed because all the values are None
    selected_X_columns = ['HRV.HRV_S.0',
       'HRV.HRV_AI.0', 'HRV.HRV_Ca.0', 'HRV.HRV_Cd.0', 'HRV.HRV_GI.0',
       'HRV.HRV_HF.0', 'HRV.HRV_LF.0', 'HRV.HRV_PI.0', 'HRV.HRV_SI.0',
       'HRV.HRV_C1a.0', 'HRV.HRV_C1d.0', 'HRV.HRV_C2a.0', 'HRV.HRV_C2d.0',
       'HRV.HRV_CSI.0', 'HRV.HRV_CVI.0', 'HRV.HRV_HFn.0', 'HRV.HRV_HTI.0',
       'HRV.HRV_LFn.0', 'HRV.HRV_PAS.0', 'HRV.HRV_PIP.0', 'HRV.HRV_PSS.0',
       'HRV.HRV_SD1.0', 'HRV.HRV_SD2.0', 'HRV.HRV_VHF.0',
       'HRV.HRV_ApEn.0', 'HRV.HRV_CVNN.0', 'HRV.HRV_CVSD.0',
       'HRV.HRV_IALS.0', 'HRV.HRV_LFHF.0', 'HRV.HRV_LnHF.0', 'HRV.HRV_SD1a.0',
       'HRV.HRV_SD1d.0', 'HRV.HRV_SD2a.0', 'HRV.HRV_SD2d.0', 'HRV.HRV_SDNN.0',
       'HRV.HRV_SDSD.0', 'HRV.HRV_TINN.0', 'HRV.HRV_IQRNN.0',
       'HRV.HRV_MCVNN.0', 'HRV.HRV_MadNN.0', 'HRV.HRV_RMSSD.0',
       'HRV.HRV_SDNNa.0', 'HRV.HRV_SDNNd.0', 'HRV.HRV_pNN20.0',
       'HRV.HRV_pNN50.0', 'HRV.HRV_MeanNN.0', 'HRV.HRV_SD1SD2.0',
       'HRV.HRV_SampEn.0', 'HRV.HRV_MedianNN.0', 'HRV.HRV_CSI_Modified.0'
    ]

    for column_name in selected_X_columns:
        logger.info(dataframe_hrv[column_name])
        dataframe_hrv[column_name] = dataframe_hrv[column_name].apply(round_floats)

    X = dataframe_hrv[selected_X_columns]
    y = dataframe_hrv['stress']

    # tpot_classifer = do_tpot(generations=10, population_size=20, X=X, y=y)

    prediction = random_forest_classfier(X=X, y=y, test_size=0.2, random_state=0, debug=True)

    logger.info(prediction)

    return create_json_response(status_code, status, data, message = filtered_response.count())