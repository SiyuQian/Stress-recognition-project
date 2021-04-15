from django.db import models
from django.db.models import JSONField

# Create your models here.

class Request(models.Model):
	request_body = models.JSONField()
	created_at = models.DateTimeField(auto_now_add=True)


class Response(models.Model):
	response_body = models.JSONField()
	created_at = models.DateTimeField(auto_now_add=True)

class Uuid(models.Model):
	uuid = models.CharField(unique=True, max_length=50)
	created_at = models.DateTimeField(auto_now_add=True)