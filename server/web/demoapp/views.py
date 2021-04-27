from django.shortcuts import render
from . import tasks
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from demoapp.models import Request, Response, Uuid
from django.db.models import Avg
from demoapp.utils import validate_http_request_method, create_json_response, convert_unit
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
