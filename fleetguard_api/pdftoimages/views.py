import os

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.core.files.storage import default_storage
from pdf2image import convert_from_path
from django.conf import settings
from django.http import JsonResponse
from django.core.files.base import ContentFile
from io import BytesIO
import logging
logger=logging.getLogger(__name__)

class PDFToJPEGView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_description="Upload a PDF and convert it to JPEG",
        responses={
            200: openapi.Response(
                description="Successful operation",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'jpeg_images': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)
                        )
                    }
                )
            ),
            400: "Invalid input"
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'file': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY,
                                       description='The PDF file to convert')
            },
            required=['file']
        )
    )
    def post(self, request, *args, **kwargs):
        logger.info(f"Request FILES:{request.FILES}")
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        logger.info(f"Received file: {file.name}")
        file_path = default_storage.save(file.name, file)
        full_file_path = os.path.join(default_storage.location, file_path)
        # Get the base name of the PDF file without the extension
        base_name = os.path.splitext(file.name)[0]

        poppler_path = r"../poppler-24.02.0/Library/bin"
        output_folder = os.path.join(settings.MEDIA_ROOT, 'converted_images')

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        try:
            # Convert PDF to JPEG
            pages = convert_from_path(pdf_path=full_file_path, poppler_path=poppler_path)
            jpeg_urls = []
            for i, page in enumerate(pages):
                img_name = f"{base_name}-{i + 1}.jpeg"
                # img_path = os.path.join(output_folder, img_name)
                # page.save(img_path, "JPEG")

                # Save the image to the media directory and generate its URL
                # with open(img_path, 'rb') as img_file:
                #     saved_img = default_storage.save(f'converted_images/{img_name}', ContentFile(img_file.read()))
                #     jpeg_url = default_storage.url(saved_img)
                #     jpeg_urls.append(jpeg_url)

                #Save the image directly to the default storage
                img_byte_arr = BytesIO()
                page.save(img_byte_arr, format='JPEG')
                img_byte_arr = img_byte_arr.getvalue()
                saved_img = default_storage.save(f'converted_images/{img_name}',ContentFile(img_byte_arr))
                jpeg_url = default_storage.url(saved_img)
                jpeg_urls.append(jpeg_url)

            return JsonResponse({'jpeg_images': jpeg_urls})

        finally:
            # Clean up the uploaded file
            if os.path.exists(full_file_path):
                os.remove(full_file_path)

class GetConvert(APIView):
    def get(self, request, *args, **kwargs):
        output_folder = os.path.join(settings.MEDIA_ROOT, 'converted_images')
        if not os.path.exists(output_folder):
            return Response({'error': 'No converted images found'}, status=status.HTTP_404_NOT_FOUND)

        image_files = os.listdir(output_folder)
        jpeg_urls = [default_storage.url(os.path.join('converted_images', img)) for img in image_files if
                     img.endswith('.jpeg')]

        return JsonResponse({'jpeg_images': jpeg_urls})

