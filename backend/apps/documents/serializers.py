from rest_framework import serializers
from .models import BoardRecord


class BoardRecordSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BoardRecord
        fields = ['id', 'title', 'image', 'image_url', 'status', 'result_text', 'confidence', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'result_text', 'confidence', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
