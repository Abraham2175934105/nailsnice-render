from rest_framework import viewsets
from .models import TipoServicio, Servicio, Agendamiento
from .serializers import TipoServicioSerializer, ServicioSerializer, AgendamientoSerializer

class TipoServicioViewSet(viewsets.ModelViewSet):
    queryset = TipoServicio.objects.all()
    serializer_class = TipoServicioSerializer

class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer

class AgendamientoViewSet(viewsets.ModelViewSet):
    queryset = Agendamiento.objects.all()
    serializer_class = AgendamientoSerializer