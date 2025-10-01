from rest_framework import serializers
from .models import Image, Tag

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id","name"]

class ImageSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    class Meta:
        model = Image
        fields = ["id","title","description","image","created_at","likes_count","tags"]

