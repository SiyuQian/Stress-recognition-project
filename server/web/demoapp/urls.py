from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'demoapp'

urlpatterns = [
	path('', views.index),
    path('api/v1/stress', views.stress_index, name="stress_index"),
    path('api/v1/uuid', views.uuid_index, name="uuid_index"),
    path('report', views.report_index, name="report_index"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
