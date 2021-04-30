from django.http import JsonResponse
from sklearn import metrics
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from tpot import TPOTClassifier
import numpy as np


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

def create_json_response(status_code = 200, status = 'success', data = {}, message = ''):
    body = {
        'statusCode': status_code,
        'status': status,
        'data': data,
        'message': message
    }
    return JsonResponse(body, status = status_code)

def convert_unit(x):
    return float(x) / 1000000

def round_floats(row, float_points = 2):
    return round(row, float_points)

def stress_classifier(row):
    is_stress = 1 if row['hr_mean'] > 95 else 0
    return is_stress

def do_tpot(generations=5, population_size=10,X='',y=''):
    X_train, X_test, y_train, y_test = train_test_split(X, y,
                                                        train_size=0.80, test_size=0.20)

    tpot = TPOTClassifier(generations=generations, population_size=population_size, verbosity=2, cv=3)
    tpot.fit(X_train, y_train)
    logger.info(tpot.score(X_test, y_test))
    return tpot

def random_forest_classfier(X, y, test_size = 0.2, random_state = 0, debug = False):
    X_train, X_test, y_train, y_test = train_test_split(X, y,
                                                    test_size=0.2, random_state=0)
    regressor = RandomForestRegressor(n_estimators=20, random_state=0)
    regressor.fit(X_train, y_train)
    y_pred = regressor.predict(X_test)

    logger.info("=============================")
    logger.info(debug)

    if debug == True:

        logger.info("=============================")

        logger.info('Mean Absolute Error:' + str(metrics.mean_absolute_error(y_test, y_pred)))
        logger.info('Mean Squared Error:' + str(metrics.mean_squared_error(y_test, y_pred)))
        logger.info('Root Mean Squared Error:'+ str(np.sqrt(metrics.mean_squared_error(y_test, y_pred))))

    logger.info("=============================")

    return y_pred