from dataclasses import fields

from rest_framework import serializers

from engine.instance import Params

from . import services
from .models import Agente, Equipe, Microarea, Plano

# limites por requisição: o planejamento roda de forma síncrona
LIMITES = {"iterations": 100_000, "time_limit_s": 30.0, "n_candidatas": 500}
MAX_SEMENTES = 10


class AgenteSerializer(serializers.ModelSerializer):
    microarea = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Agente
        fields = ["id", "nome", "microarea", "hora_inicio", "jornada_min", "jornada_max_min", "velocidade_m_min",
                  "teto_graves"]

    def validate(self, attrs):
        T = attrs.get("jornada_min", getattr(self.instance, "jornada_min", None))
        Tmax = attrs.get("jornada_max_min", getattr(self.instance, "jornada_max_min", None))
        if T is not None and Tmax is not None and T > Tmax:
            raise serializers.ValidationError("jornada_min não pode ser maior que jornada_max_min")
        if attrs.get("velocidade_m_min", 1) <= 0:
            raise serializers.ValidationError({"velocidade_m_min": "deve ser positiva"})
        return attrs


class MicroareaSerializer(serializers.ModelSerializer):
    equipe = serializers.SerializerMethodField()
    ubs = serializers.SerializerMethodField()
    agente = serializers.SerializerMethodField()
    n_domicilios = serializers.IntegerField(source="domicilios.count", read_only=True)

    class Meta:
        model = Microarea
        fields = ["id", "nome", "equipe", "ubs", "agente", "setores", "bairros", "area_km2", "moradores_censo",
                  "domicilios_censo", "n_domicilios", "poligono"]

    def get_equipe(self, m):
        return {"id": m.equipe_id, "nome": m.equipe.nome}

    def get_ubs(self, m):
        u = m.equipe.ubs
        return {"id": u.pk, "nome": u.nome, "lat": u.lat, "lon": u.lon}

    def get_agente(self, m):
        a = getattr(m, "agente", None)
        return {"id": a.pk, "nome": a.nome} if a else None


class ParamsSerializer(serializers.Serializer):
    """Parâmetros opcionais do otimizador (campos de engine.instance.Params)."""
    beta = serializers.FloatField(required=False, min_value=0)
    gamma = serializers.FloatField(required=False, min_value=0)
    n_candidatas = serializers.IntegerField(required=False, min_value=0, max_value=LIMITES["n_candidatas"])
    iterations = serializers.IntegerField(required=False, min_value=0, max_value=LIMITES["iterations"])
    time_limit_s = serializers.FloatField(required=False, min_value=0, max_value=LIMITES["time_limit_s"])
    seeds = serializers.ListField(child=serializers.IntegerField(), required=False, min_length=1,
                                  max_length=MAX_SEMENTES)
    destroy_min = serializers.FloatField(required=False, min_value=0, max_value=1)
    destroy_max = serializers.FloatField(required=False, min_value=0, max_value=1)
    t_start = serializers.FloatField(required=False, min_value=0)
    cooling = serializers.FloatField(required=False, min_value=0, max_value=1)

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("params deve ser um objeto")
        unknown = set(data) - {f.name for f in fields(Params)}
        if unknown:
            raise serializers.ValidationError(f"parâmetros desconhecidos: {', '.join(sorted(unknown))}")
        return super().to_internal_value(data)

    def validate(self, attrs):
        if attrs.get("destroy_min", 0) > attrs.get("destroy_max", 1):
            raise serializers.ValidationError("destroy_min não pode ser maior que destroy_max")
        return attrs


class EquipeSerializer(serializers.ModelSerializer):
    ubs = serializers.SerializerMethodField()
    microareas = serializers.SerializerMethodField()

    class Meta:
        model = Equipe
        fields = ["id", "nome", "ubs", "microareas"]

    def get_ubs(self, e):
        return {"id": e.ubs_id, "nome": e.ubs.nome, "lat": e.ubs.lat, "lon": e.ubs.lon}

    def get_microareas(self, e):
        out = []
        for m in e.microareas.select_related("agente").order_by("nome"):
            a = getattr(m, "agente", None)
            out.append({"id": m.pk, "nome": m.nome, "area_km2": m.area_km2, "n_domicilios": m.domicilios.count(),
                        "agente": AgenteSerializer(a).data if a else None})
        return out


class PlanejarSerializer(serializers.Serializer):
    data = serializers.DateField()
    metodo = serializers.ChoiceField(choices=sorted(services.METODOS), default="alns")
    params = ParamsSerializer(required=False, default=dict)

    def params_obj(self) -> Params:
        return Params(**self.validated_data.get("params", {}))


class PlanoCreateSerializer(PlanejarSerializer):
    agente = serializers.PrimaryKeyRelatedField(queryset=Agente.objects.select_related("microarea__equipe__ubs"))


class CompararSerializer(serializers.Serializer):
    tempo_milp = serializers.FloatField(required=False, default=20.0, min_value=1, max_value=120)
    n = serializers.IntegerField(required=False, allow_null=True, default=None, min_value=2, max_value=60)
    seed = serializers.IntegerField(required=False, default=0)


class PlanoResumoSerializer(serializers.ModelSerializer):
    """Linha de listagem: o plano sem itens nem rota."""
    agente = serializers.SerializerMethodField()
    microarea = serializers.IntegerField(source="agente.microarea_id")
    visitas = serializers.IntegerField(source="itens.count")
    nao_atendidas = serializers.IntegerField(source="nao_atendidas.count")
    retorno = serializers.SerializerMethodField()

    class Meta:
        model = Plano
        fields = ["id", "agente", "microarea", "data", "metodo", "status", "objetivo", "caminhada_min",
                  "penalidade_residual", "excesso_min", "retorno_min", "retorno", "visitas", "nao_atendidas",
                  "n_candidatas", "runtime_s", "criado_em"]

    def get_agente(self, p):
        return {"id": p.agente_id, "nome": p.agente.nome}

    def get_retorno(self, p):
        return services.relogio(p, p.retorno_min)


class PlanoSerializer(serializers.ModelSerializer):
    """Plano completo no formato do Apêndice E de docs/passos-implementacao.md."""
    agente = serializers.SerializerMethodField()
    microarea = serializers.IntegerField(source="agente.microarea_id")
    metricas = serializers.SerializerMethodField()
    ubs = serializers.SerializerMethodField()
    itens = serializers.SerializerMethodField()
    nao_atendidas = serializers.SerializerMethodField()
    rota = serializers.JSONField(source="rota_geojson")
    links = serializers.SerializerMethodField()

    class Meta:
        model = Plano
        fields = ["id", "agente", "microarea", "data", "metodo", "params", "status", "violacoes", "hora_inicio",
                  "metricas", "ubs", "itens", "nao_atendidas", "rota", "links", "criado_em"]

    def get_agente(self, p):
        return {"id": p.agente_id, "nome": p.agente.nome}

    def get_ubs(self, p):
        u = p.agente.microarea.equipe.ubs
        return {"id": u.pk, "nome": u.nome, "lat": u.lat, "lon": u.lon}

    def get_metricas(self, p):
        itens = list(p.itens.select_related("domicilio"))
        acs = p.params.get("acs", {})
        return {
            "objetivo": p.objetivo, "caminhada_min": p.caminhada_min, "penalidade_residual": p.penalidade_residual,
            "penalidade_residual_min": p.params.get("beta", Params().beta) * p.penalidade_residual,
            "excesso_min": p.excesso_min, "H": p.retorno_min, "retorno": services.relogio(p, p.retorno_min),
            "jornada_min": acs.get("T"), "jornada_max_min": acs.get("Tmax"), "teto_graves": acs.get("K"),
            "visitas": len(itens), "candidatas": p.n_candidatas, "fora_das_candidatas": p.n_fora_candidatas,
            "urgentes_atendidas": sum(i.domicilio.urgente for i in itens),
            "graves": sum(i.domicilio.grave for i in itens),
            "nao_atendidas": p.nao_atendidas.count(),
            "runtime_s": p.runtime_s, "seed": p.seed, "seeds_stats": p.seeds_stats, "gap": p.gap,
        }

    def get_itens(self, p):
        out = []
        for i in p.itens.select_related("domicilio"):
            d = i.domicilio
            out.append({
                "ordem": i.ordem, "domicilio": d.pk, "codigo": d.codigo, "lat": d.lat, "lon": d.lon,
                "condicao": d.condicao, "motivo": i.motivo, "w": d.peso, "urgente": d.urgente, "grave": d.grave,
                "dias_sem_visita": services.dias_sem_visita(d, p.data), "P": d.intervalo_max_dias,
                "chegada": services.relogio(p, i.chegada_min), "inicio": services.relogio(p, i.inicio_min),
                "fim": services.relogio(p, i.fim_min), "espera_min": i.inicio_min - i.chegada_min,
                "caminhada_min": i.caminhada_min, "duracao_min": d.duracao_min,
            })
        return out

    def get_nao_atendidas(self, p):
        out = []
        for n in p.nao_atendidas.select_related("domicilio").order_by("-penalidade"):
            d = n.domicilio
            out.append({
                "domicilio": d.pk, "codigo": d.codigo, "lat": d.lat, "lon": d.lon, "condicao": d.condicao,
                "motivo": n.motivo, "w": d.peso, "urgente": d.urgente, "grave": d.grave, "penalidade": n.penalidade,
                "dias_sem_visita": n.dias_sem_visita, "atraso_dias": n.atraso_dias,
            })
        return out

    def get_links(self, p):
        request = self.context.get("request")

        def url(suffix):
            path = f"/api/planos/{p.pk}/{suffix}"
            return request.build_absolute_uri(path) if request else path

        return {"csv": url("itinerario.csv"), "gpx": url("itinerario.gpx")}
