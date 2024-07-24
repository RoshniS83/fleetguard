from django.urls import path
from .views import GenerateYOLOLabelView, home

urlpatterns = [
    path('generate-yolo-label/', GenerateYOLOLabelView.as_view(), name='generate_yolo_label'),
    # path('home/', home, name='home'),  # Add this line for the home view
]