from rest_framework.generics import ListAPIView, RetrieveAPIView
from .models import Image
from .serializers import ImageSerializer
from .filters import ImageFilter

class ImageListAPI(ListAPIView):
    serializer_class = ImageSerializer
    filterset_class = ImageFilter

    def get_queryset(self):
        return Image.objects.filter(is_public=True).prefetch_related("tags")

class ImageDetailAPI(RetrieveAPIView):
    serializer_class = ImageSerializer
    queryset = Image.objects.filter(is_public=True).prefetch_related("tags")

