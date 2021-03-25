from django.shortcuts import render, redirect
from . import tasks
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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
def stress_index(request):
    # success HTTP status code as default value
    status_code = 200;
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

    # @todo: implement actual logic to detect the stress by process the requests from the client end constantly

    # data = pd.read_csv("https://raw.githubusercontent.com/SiyuQian/django-docker/master/712AF22B_Mar11_14-07-59.csv");
    # Generate 15 seconds of PPG signal (recorded at 250 samples / second)
    # 130
    # ppg = nk.ppg_simulate(duration=15, sampling_rate=250, heart_rate=70)
    # signals, info = nk.ppg_process(data['PPG'], sampling_rate=50)

    # Clear the noise
    # ppg_clean = nk.ppg_clean(signals)

    # Peaks
    # peaks = nk.ppg_findpeaks(data['PPG'].div(1000000).to_numpy(), sampling_rate=100)

    # Compute HRV indices
    # hrv_indices = nk.hrv(peaks, sampling_rate=100, show=True)
    # result = hrv_indices.to_json()
    # parsed = json.loads(result)
    # context = {'response' : json.dumps(parsed), 'post': body}
    body = {
        'statusCode': status_code,
        'status': 'success',
        'response': body
    }
    return JsonResponse(body, status = status_code)
