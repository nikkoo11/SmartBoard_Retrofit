import os
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import BoardRecord
from .serializers import BoardRecordSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok', 'service': 'SmartBoard Retrofit backend'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    total = BoardRecord.objects.count()
    latest = BoardRecord.objects.first()
    return Response({
        'system_status': 'Demo Mode',
        'camera_status': 'disconnected',
        'total_records': total,
        'latest_activity': BoardRecordSerializer(latest, context={'request': request}).data if latest else None,
        'note': 'Demo data until hardware is connected.',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def camera_status(request):
    return Response({'connected': False, 'status': 'disconnected', 'message': 'Camera not connected.'})


class BoardRecordViewSet(viewsets.ModelViewSet):
    queryset = BoardRecord.objects.all()
    serializer_class = BoardRecordSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'status', 'result_text']
    ordering_fields = ['created_at', 'status']

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_image(request):
    file = request.FILES.get('image')
    if not file:
        return Response({'error': 'No image provided.'}, status=status.HTTP_400_BAD_REQUEST)
    allowed = ['image/jpeg', 'image/png', 'image/jpg']
    if file.content_type not in allowed:
        return Response({'error': 'Unsupported file type.'}, status=status.HTTP_400_BAD_REQUEST)
    if file.size > 5 * 1024 * 1024:
        return Response({'error': 'File too large (max 5MB).'}, status=status.HTTP_400_BAD_REQUEST)
    record = BoardRecord.objects.create(image=file, title=request.data.get('title', 'Uploaded image'), status='pending')
    return Response(BoardRecordSerializer(record, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics(request):
    days = int(request.query_params.get('days', 7))
    since = timezone.now() - timedelta(days=days)
    qs = BoardRecord.objects.filter(created_at__gte=since)
    by_day = qs.extra({'day': "date(created_at)"}).values('day').annotate(count=Count('id')).order_by('day')
    return Response({
        'days': days,
        'total': qs.count(),
        'by_day': list(by_day),
        'note': 'Demo data based on stored records.',
    })
