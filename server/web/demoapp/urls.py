from django.urls import path
from . import views

app_name = 'demoapp'

urlpatterns = [
	path('', views.index),
    path('api/v1/stress', views.stress_index, name="stress_index"),
    path('test/', views.test_index, name="test_index"),
]
