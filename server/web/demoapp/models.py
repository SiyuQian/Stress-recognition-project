from django.db import models
from django.db.models import JSONField

# Create your models here.

class Request(models.Model):
	request_body = models.JSONField()
	created_at = models.DateTimeField(auto_now_add=True)


class Response(models.Model):
	device_code = models.CharField(max_length=50, default='')
	uuid = models.CharField(max_length=50, default='')
	mode = models.CharField(max_length=50, default='')
	mean = models.CharField(max_length=50, default='')
	hrv_pnn50 = models.CharField(max_length=50, default='')
	hrv_rmssd = models.CharField(max_length=50, default='')
	hr_mean = models.CharField(max_length=50, default='')
	status = models.CharField(max_length=50, default='')
	response_body = models.JSONField()
	created_at = models.DateTimeField(auto_now_add=True)

class Uuid(models.Model):
	uuid = models.CharField(unique=True, max_length=50)
	created_at = models.DateTimeField(auto_now_add=True)