from django.shortcuts import render
import os
import cv2
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.core.files.storage import FileSystemStorage
from rest_framework.views import APIView
from ultralytics import YOLO
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings

# Initialize the YOLO model
model = YOLO(r'../best.pt')

@method_decorator(csrf_exempt, name='dispatch')
class GenerateYOLOLabelView(APIView):

    def post(self, request):
        # Get image and type from request
        image_file = request.FILES.get('image')
        img_type = request.POST.get('img_type')

        if not image_file or img_type not in ['FFPL', 'CUST']:
            return JsonResponse({'error': 'Invalid input'}, status=400)

        # Save the uploaded file
        fs = FileSystemStorage()
        image_path = fs.save(image_file.name, image_file)
        image_path_full = os.path.join(fs.location, image_path)

        # Generate YOLO labeled image
        try:
            yolo_output_dir = os.path.join(settings.MEDIA_ROOT, 'yolo_output')

            if not os.path.exists(yolo_output_dir):
                os.makedirs(yolo_output_dir)

            output_txt_path = os.path.join(yolo_output_dir, f"{os.path.splitext(image_file.name)[0]}.txt")

            image_with_boxes = self.generate_yolo_labelled_img(image_path_full, output_txt_path)

            # Save or return the image with bounding boxes
            output_image_path = os.path.join(yolo_output_dir, f'output_{image_file.name}')
            cv2.imwrite(output_image_path, image_with_boxes)

            return JsonResponse({'output_image_path': output_image_path, 'output_txt_path': output_txt_path})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def generate_yolo_labelled_img(self, image_path, output_txt_path):
        image = cv2.imread(image_path)
        image_with_boxes = image.copy()
        result = model(image, conf=0.35, iou=0.3, save_txt=True, show_labels=False, show_conf=False, save=True)

        for r in result:
            r.save_txt(output_txt_path)

        # Read bounding box results
        with open(output_txt_path, 'r') as f:
            lines = f.readlines()

        boxes = []
        for line in lines:
            parts = line.split()
            class_index = int(parts[0])
            x, y, w, h = map(float, parts[1:])
            top_left = (int((x - w / 2) * image.shape[1]), int((y - h / 2) * image.shape[0]))
            bottom_right = (int((x + w / 2) * image.shape[1]), int((y + h / 2) * image.shape[0]))

            # Increase width by 2 pixels
            width_adjustment = 2
            top_left = (top_left[0] - width_adjustment, top_left[1])  # Move left
            bottom_right = (bottom_right[0] + width_adjustment, bottom_right[1])  # Move right

            boxes.append((class_index, top_left, bottom_right))

        boxes.sort(key=lambda box: (box[0], box[1][0]))

        # Draw bounding boxes and label numbers
        for i, (class_index, top_left, bottom_right) in enumerate(boxes):
            cv2.rectangle(image_with_boxes, top_left, bottom_right, (0, 0, 255), 1)
            cv2.putText(image_with_boxes, str(i + 1), (top_left[0] - 5, top_left[1] - 8),
                        cv2.FONT_HERSHEY_SCRIPT_COMPLEX, 1, (0, 0, 255), 2)

        return image_with_boxes

def home(request):
    return HttpResponse("Welcome to the FleetGuard API!")
