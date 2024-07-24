from django.urls import path
from .views import GenerateExcelView

urlpatterns = [
    path('excelsheet/', GenerateExcelView.as_view(), name='generate_excelsheet'),
]