from django.http import JsonResponse

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
