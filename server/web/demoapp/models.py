from django.db import models
from django.db.models import JSONField

# Create your models here.

class Request(models.Model):
	device = models.CharField(max_length=50, default='')
	hr = models.IntegerField(default=0)
	ppg = models.FloatField(default=0.0)
	uuid = models.CharField(max_length=50, default='')
	time = models.CharField(max_length=50, default='')
	timedate = models.CharField(max_length=50, default='')
	created_at = models.DateTimeField(auto_now_add=True)


class Response(models.Model):
	device_code = models.CharField(max_length=50, default='')
	uuid = models.CharField(max_length=50, default='')
	mode = models.CharField(max_length=50, default='')
	mean = models.CharField(max_length=50, default='')
	hrv_pnn50 = models.CharField(max_length=50, default='')
	hrv_rmssd = models.CharField(max_length=50, default='')
	hr_mean = models.CharField(max_length=50, default='')
	status_basic = models.CharField(max_length=50, default='')
	status_sliding = models.CharField(max_length=50, default='')
	response_body = models.JSONField()
	created_at = models.DateTimeField(auto_now_add=True)

class EventLabel(models.Model):
	device_code = models.CharField(max_length=50, default='')
	uuid = models.CharField(max_length=50, default='')
	short_hand = models.CharField(max_length=50, default='')
	name = models.CharField(max_length=50, default='')
	value = models.CharField(max_length=50, default='')
	created_at = models.DateTimeField(auto_now_add=True)

class Uuid(models.Model):
	uuid = models.CharField(unique=True, max_length=50)
	created_at = models.DateTimeField(auto_now_add=True)