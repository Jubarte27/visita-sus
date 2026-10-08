from datetime import date

from django.db import connection
from django.db.utils import DatabaseError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from engine import export

from . import relatorio as relatorio_service
from . import services
from .models import Agente, Equipe, Microarea, Plano
from .serializers import (AgenteSerializer, CompararSerializer, EquipeSerializer, MicroareaSerializer,
                          PlanejarSerializer, PlanoCreateSerializer, PlanoResumoSerializer, PlanoSerializer)


def _instancia_ausente(microarea, erro):
    return Response({"detail": f"arquivos da instância {microarea.nome} indisponíveis em {microarea.path}: {erro}"},
                    status=status.HTTP_409_CONFLICT)


def _data(request) -> date:
    raw = request.query_params.get("data")
    if not raw:
        return date.today()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValidationError({"data": "use o formato AAAA-MM-DD"}) from None


@api_view(["GET"])
def health(request):
    """Saúde do serviço: confere a conexão com o banco com um SELECT 1."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db = cursor.fetchone() == (1,)
    except DatabaseError:
        db = False
    return Response({"status": "ok" if db else "erro", "db": db}, status=200 if db else 503)


class EquipeList(generics.ListAPIView):
    queryset = Equipe.objects.select_related("ubs").order_by("nome")
    serializer_class = EquipeSerializer


class EquipeDetail(generics.RetrieveAPIView):
    queryset = Equipe.objects.select_related("ubs")
    serializer_class = EquipeSerializer


@api_view(["POST"])
def equipe_planejar(request, pk):
    """Planeja o dia de todos os ACS da equipe ({data, metodo, params?}); devolve os planos resumidos."""
    equipe = get_object_or_404(Equipe, pk=pk)
    s = PlanejarSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    data, metodo = s.validated_data["data"], s.validated_data["metodo"]
    try:
        planos = services.planejar_equipe(equipe, data, metodo, s.params_obj())
    except OSError as e:
        return Response({"detail": f"arquivos de instância indisponíveis na equipe {equipe.nome}: {e}"},
                        status=status.HTTP_409_CONFLICT)
    return Response({"equipe": equipe.pk, "data": data.isoformat(), "metodo": metodo,
                     "planos": PlanoResumoSerializer(planos, many=True).data}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def equipe_relatorio(request, pk):
    """Relatório por microárea a partir do último plano de cada ACS na data (?data=, padrão hoje)."""
    equipe = get_object_or_404(Equipe.objects.select_related("ubs"), pk=pk)
    return Response(relatorio_service.relatorio(equipe, _data(request)))


class MicroareaDetail(generics.RetrieveAPIView):
    queryset = Microarea.objects.select_related("equipe__ubs", "agente")
    serializer_class = MicroareaSerializer


@api_view(["GET"])
def microarea_domicilios(request, pk):
    """Domicílios da microárea como FeatureCollection, com dias sem visita e penalidade na data (?data=)."""
    microarea = get_object_or_404(Microarea, pk=pk)
    data = _data(request)
    features = []
    for d in microarea.domicilios.all():
        dias = services.dias_sem_visita(d, data)
        features.append({
            "type": "Feature", "id": d.pk,
            "geometry": {"type": "Point", "coordinates": [d.lon, d.lat]},
            "properties": {
                "id": d.pk, "codigo": d.codigo, "condicao": d.condicao, "w": d.peso, "P": d.intervalo_max_dias,
                "duracao_min": d.duracao_min, "ultima_visita": d.ultima_visita.isoformat(), "dias_sem_visita": dias,
                "penalidade": services.penalidade(d, data), "atrasado": dias + 1 > d.intervalo_max_dias,
                "atraso_dias": max(0, dias - d.intervalo_max_dias), "urgente": d.urgente, "grave": d.grave,
                "tw_inicio": d.tw_inicio, "tw_fim": d.tw_fim, "n_moradores": d.n_moradores, "node": d.node,
            },
        })
    return Response({"type": "FeatureCollection", "data": data.isoformat(), "features": features})


@api_view(["GET"])
def microarea_malha(request, pk):
    microarea = get_object_or_404(Microarea, pk=pk)
    try:
        return Response(services.malha_geojson(microarea))
    except OSError as e:
        return _instancia_ausente(microarea, e)


class AgenteDetail(generics.RetrieveUpdateAPIView):
    queryset = Agente.objects.all()
    serializer_class = AgenteSerializer


class PlanoList(generics.ListCreateAPIView):
    """GET: planos (filtros ?agente=, ?microarea=, ?equipe=, ?data=). POST: planeja o dia de um ACS e devolve o plano."""
    serializer_class = PlanoResumoSerializer

    def get_queryset(self):
        qs = Plano.objects.select_related("agente")
        for param, field in [("agente", "agente_id"), ("microarea", "agente__microarea_id"),
                             ("equipe", "agente__microarea__equipe_id"), ("data", "data")]:
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})
        return qs

    def create(self, request, *args, **kwargs):
        s = PlanoCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        agente = s.validated_data["agente"]
        try:
            plano = services.planejar(agente, s.validated_data["data"], s.validated_data["metodo"], s.params_obj())
        except OSError as e:
            return _instancia_ausente(agente.microarea, e)
        return Response(PlanoSerializer(plano, context={"request": request}).data, status=status.HTTP_201_CREATED)


class PlanoDetail(generics.RetrieveDestroyAPIView):
    queryset = Plano.objects.select_related("agente__microarea__equipe__ubs")
    serializer_class = PlanoSerializer


@api_view(["POST"])
def plano_comparar(request, pk):
    """
    Guloso × ALNS × MILP na instância do plano ({tempo_milp?: s, n?: candidatas da subinstância, seed?}).
    Não grava nada; devolve métricas, gaps e a rota de cada método.
    """
    plano = get_object_or_404(Plano.objects.select_related("agente__microarea__equipe__ubs"), pk=pk)
    s = CompararSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    try:
        return Response(services.comparar(plano, **s.validated_data))
    except OSError as e:
        return _instancia_ausente(plano.agente.microarea, e)


def plano_csv(request, pk):
    plano = get_object_or_404(Plano.objects.select_related("agente__microarea__equipe__ubs"), pk=pk)
    body = export.to_csv(services.linhas_itinerario(plano))
    resp = HttpResponse(body.encode("utf-8-sig"), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{services.nome_arquivo(plano, "csv")}"'
    return resp


def plano_gpx(request, pk):
    plano = get_object_or_404(Plano.objects.select_related("agente__microarea__equipe__ubs"), pk=pk)
    name = f"{plano.agente.microarea.nome} · {plano.data} · {plano.metodo}"
    body = export.to_gpx(services.linhas_itinerario(plano), services.rota_linha(plano), name)
    resp = HttpResponse(body.encode("utf-8"), content_type="application/gpx+xml")
    resp["Content-Disposition"] = f'attachment; filename="{services.nome_arquivo(plano, "gpx")}"'
    return resp
