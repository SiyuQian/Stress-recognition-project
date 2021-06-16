from django.http import JsonResponse
# from sklearn import metrics
# from sklearn.model_selection import train_test_split
# from sklearn.ensemble import RandomForestRegressor
# from tpot import TPOTClassifier
import numpy as np
import csv
import os
import neurokit2 as nk
from demoapp.models import Response, Job
from django.db.models import Avg


import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Utilites
def validate_http_request_method(request, method = 'GET', specific = False):
    isValid = True
    # Check is valid method
    # GET, POST, DELETE, PUT
    HTTP_METHODS = ['GET', 'POST', 'DELETE', 'PUT']
    if request.method not in HTTP_METHODS:
        isValid = False

    # if a specific HTTP method is required
    # then the request has to be same as the defined method
    if specific == True:
        isValid = False if request.method != method else True

    return isValid

def create_json_response(status_code, status, data = {}, message = ''):
    body = {
        'statusCode': status_code,
        'status': status,
        'data': data,
        'message': message
    }
    logger.info("=============== Creating json response body ============================")
    logger.info('Sending response with the body: ' + str(body))
    logger.info("========================================================================")
    return JsonResponse(body, status = status_code)

def get_base_line_size(frequency):
    return (10 * 60) / frequency

def normalize_z_score(x, mean, std):
    return (x - mean) / std

def normalize_min_max(x, min, max):
    return (x - min) / (max - min)

def round_floats(row, float_points = 2):
    return round(row, float_points)

def get_time_diff(start, end):
    return round((end - start) / 60, 1)

def mkDir(path):
    if not os.path.isdir(path):
        os.makedirs(path)

def get_normalized_ppg_data(dataframe):
    # ppd_std = dataframe['PPG'].astype(float).std(skipna = True)
    # ppg_mean = dataframe['PPG'].astype(float).mean(skipna = True)

    ppg_min = dataframe['PPG'].astype(float).min(skipna = True)
    ppg_max = dataframe['PPG'].astype(float).max(skipna = True)

    normalized_ppg_data = dataframe['PPG'].astype(float).apply(normalize_min_max, min = ppg_min, max = ppg_max)
    return normalized_ppg_data

def calculate_hrv(normalized_ppg_data, sample_rate):
    # Clear the noise
    ppg_clean = nk.ppg_clean(normalized_ppg_data, sampling_rate=sample_rate)

    # Peaks
    peaks = nk.ppg_findpeaks(ppg_clean, sampling_rate=sample_rate)

    hrv_indices = nk.hrv(peaks, sampling_rate=sample_rate, show=False)
    return hrv_indices

def detect_stress(filtered_response, base_data_length, parsed, hrv_threshold, hrv_rmssd_mean, hr_mean, base_hr_mean, hr_threshold, pnn50_threshold, pnn50_mean):
    stress_info = {
        'status': 'success',
        'status_basic': 'success',
        'status_sliding': 'success',
        'message': ''
    }
     # compare the mean value with recent request
    if filtered_response.count() > base_data_length :
        # Method: Comparing with Base Line
        # extract the recent mean
        if parsed['HRV_RMSSD']['0'] * hrv_threshold < hrv_rmssd_mean and hr_mean > base_hr_mean * hr_threshold and parsed['HRV_pNN50']['0'] * pnn50_threshold < pnn50_mean:
            stress_info['status'] = 'basic_warning'
            stress_info['status_basic'] = 'basic_warning'
            stress_info['message'] = 'HRV RMSSD has been changed significantly. You probably under stress.'

        sliding_window_size = base_data_length
        sliding_window_entry = filtered_response.count() - base_data_length

        hrv_rmssd_sliding_window_mean = list(filtered_response[sliding_window_entry:sliding_window_entry + sliding_window_size].aggregate(Avg('hrv_rmssd')).values())[0]
        hr_sliding_window_mean = list(filtered_response[sliding_window_entry:sliding_window_entry + sliding_window_size].aggregate(Avg('hr_mean')).values())[0]
        pnn50_sliding_window_mean = list(filtered_response[sliding_window_entry:sliding_window_entry + sliding_window_size].aggregate(Avg('hrv_pnn50')).values())[0]

        # Method: Sliding window
        if parsed['HRV_RMSSD']['0'] * hrv_threshold < hrv_rmssd_sliding_window_mean and hr_mean > hr_sliding_window_mean * hr_threshold and parsed['HRV_pNN50']['0'] * pnn50_threshold < pnn50_sliding_window_mean:
            stress_info['status'] = 'sliding_warning'
            stress_info['status_sliding'] = 'sliding_warning'
            stress_info['message'] = 'HRV RMSSD has been changed significantly. You probably under stress.'
    return stress_info

def store_response(device_code, uuid, mode, status_basic, status_sliding, hr_mean, hrv_pnn50, hrv_rmssd, response_body):
    response_model = Response()
    response_model.device_code = device_code
    response_model.uuid = uuid
    response_model.mode = mode
    response_model.status_basic = status_basic
    response_model.status_sliding = status_sliding
    response_model.hr_mean = hr_mean
    response_model.hrv_pnn50 = hrv_pnn50
    response_model.hrv_rmssd = hrv_rmssd
    response_model.response_body = response_body
    response_model.save()

def create_job(uuid, device_code, frequency, hr_threshold, hrv_threshold, baseline_size):
    if (Job.objects.filter(uuid=uuid, device=device_code).count() < 1) :
        logger.info('Creating job ...')
        job_model = Job()
        job_model.device = device_code
        job_model.uuid = uuid
        job_model.frequency = frequency
        job_model.hr_threshold = hr_threshold
        job_model.hrv_threshold = hrv_threshold
        job_model.baseline_size = baseline_size
        job_model.save()


def generate_csv(values, device_code, uuid, filename):
    header = values[0].keys()
    # @todo: remove the hard coded file path
    filePath = "./demoapp/static/datasets/" + device_code + "/" + uuid + "/"
    if not os.path.isdir(filePath):
        os.makedirs(filePath)

    with open(filePath + filename + ".csv", "w", newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, header)
        dict_writer.writeheader()
        dict_writer.writerows(values)

# def stress_classifier(row):
#     is_stress = True if row['hrv_rmssd'] > row['hrv_rmssd'] * 1.16 else False
#     return is_stress

# def stress_classifier(row):
#     is_stress = 1 if row['hr_mean'] > 95 else 0
#     return is_stress

# def do_tpot(generations=5, population_size=10,X='',y=''):
#     X_train, X_test, y_train, y_test = train_test_split(X, y,
#                                                         train_size=0.80, test_size=0.20)

#     tpot = TPOTClassifier(generations=generations, population_size=population_size, verbosity=2, cv=3)
#     tpot.fit(X_train, y_train)
#     logger.info(tpot.score(X_test, y_test))
#     return tpot

# def random_forest_classfier(X, y, test_size = 0.2, random_state = 0, debug = False):
#     X_train, X_test, y_train, y_test = train_test_split(X, y,
#                                                     test_size=0.2, random_state=0)
#     regressor = RandomForestRegressor(n_estimators=20, random_state=0)
#     regressor.fit(X_train, y_train)
#     y_pred = regressor.predict(X_test)

#     logger.info("=============================")
#     logger.info(debug)

#     if debug == True:

#         logger.info("=============================")

#         logger.info('Mean Absolute Error:' + str(metrics.mean_absolute_error(y_test, y_pred)))
#         logger.info('Mean Squared Error:' + str(metrics.mean_squared_error(y_test, y_pred)))
#         logger.info('Root Mean Squared Error:'+ str(np.sqrt(metrics.mean_squared_error(y_test, y_pred))))

#     logger.info("=============================")

#     return y_pred