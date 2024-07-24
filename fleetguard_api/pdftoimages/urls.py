from django.urls import path
from .views import PDFToJPEGView, GetConvert

urlpatterns = [
    path('getconverted/', GetConvert.as_view(), name='getconverted image'),
    path('convert/', PDFToJPEGView.as_view(), name='post convert')
]
