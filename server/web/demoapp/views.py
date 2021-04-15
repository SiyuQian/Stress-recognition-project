from django.shortcuts import render
from . import tasks
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from demoapp.models import Request, Response, Uuid
import neurokit2 as nk
import pandas as pd
import json

@csrf_exempt
def index(request):
    return render(request, "index.html")

@csrf_exempt
def test_index(request):
    body_unicode = request.body.decode('utf-8')
    context = { 'method': request.method, 'body': body_unicode }
    return render(request, 'test/index.html', context)

@csrf_exempt
def uuid_index(request):
    status_code = 200
    if (request.method != 'POST') :
        status_code = 400
        body = {
            'statusCode': status_code,
            'status': 'error',
            'response': 'Bad request! This API endpoint only handles POST request.',
        }

        return JsonResponse(body, status = status_code)
    body_unicode = request.body.decode('utf-8')

    # validate if the request body is in JSON format
    try:
        # { "uuid": "33d84b2a-9e39-11eb-a8b3-0242ac130003" }
        body = json.loads(body_unicode)
    except Exception as e:
        status_code = 400
        body = {
            'statusCode': status_code,
            'status': 'error',
            'response': 'Bad request! The request data have to be in a valid JSON format.',
        }
        return JsonResponse(body, status = status_code)

    uuid = Uuid.objects.filter(uuid=body['uuid'])
    if uuid.count() == 0 :
        uuid = Uuid(uuid=body['uuid'])
        uuid.save()

        body = {
            'statusCode': status_code,
            'status': 'success',
            'response': 'The UUID is vaild.'
        }
    else:
        body = {
            'statusCode': status_code,
            'status': 'error',
            'response': 'The UUID already existed.'
        }

    return JsonResponse(body, status = status_code)

@csrf_exempt
def stress_index(request):
    # success HTTP status code as default value
    status_code = 200
    # Validate the request
    if (request.method != 'POST') :
        status_code = 400
        body = {
            'statusCode': status_code,
            'status': 'error',
            'response': 'Bad request! This API endpoint only handles POST request.',
        }

        return JsonResponse(body, status = status_code)

    # Handle the request from the client-end
    body_unicode = request.body.decode('utf-8')

    # validate if the request body is in JSON format
    try:
        body = json.loads(body_unicode)
    except Exception as e:
        status_code = 400
        body = {
            'statusCode': status_code,
            'status': 'error',
            'response': 'Bad request! The request data have to be in a valid JSON format.',
        }

    # Store the request data into the Mysql database
    request = Request()
    request.request_body = body
    request.save()

    # Convert the json into a dataframe
    dataframe = pd.DataFrame.from_dict(body)

    # Clear the noise
    ppg_clean = nk.ppg_clean(dataframe['PPG'].div(1000000).to_numpy(), sampling_rate=50)

    # Peaks
    peaks = nk.ppg_findpeaks(ppg_clean, sampling_rate=50)

    # Compute HRV indices
    hrv_indices = nk.hrv(peaks, sampling_rate=50, show=False)
    result = hrv_indices.to_json()
    parsed = json.loads(result)
    # context = {'response' : json.dumps(parsed), 'post': body}
    body = {
        'statusCode': status_code,
        'status': 'success',
        'response': parsed
    }

    response = Response()
    response.response_body = body
    response.save()

    # store the response body to the database

    return JsonResponse(body, status = status_code)
