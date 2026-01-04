from rest_framework import generics

from api.permissions import IsAdminUserOrReadOnly
from api.serializers import TrailConditionSerializer
from trail_status.models.condition import TrailCondition
from trail_status.models.source import DataSource


class ListView(generics.ListCreateAPIView):
    queryset = TrailCondition.objects.all().order_by("-updated_at")
    serializer_class = TrailConditionSerializer
    permission_classes = [IsAdminUserOrReadOnly]


class DetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TrailCondition.objects.all()
    serializer_class = TrailConditionSerializer
    permission_classes = [IsAdminUserOrReadOnly]
