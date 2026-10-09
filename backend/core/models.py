"""
Modelos do visita-sus: território (UBS, equipe, microárea, ACS, domicílios) e planos diários.

Os atributos clínicos dos domicílios seguem o engine: peso (w), intervalo_max_dias (P), duracao_min (s),
ultima_visita (d é calculado para a data do plano, decisão D8) e janela em minutos desde o início da
jornada. Grafo e matriz de tempos ficam em arquivo, na pasta da instância (`Microarea.instancia_dir`).
"""

from datetime import time
from pathlib import Path

from django.conf import settings
from django.db import models


class Ubs(models.Model):
    nome = models.CharField(max_length=200)
    lat = models.FloatField()
    lon = models.FloatField()

    class Meta:
        verbose_name = "UBS"
        verbose_name_plural = "UBS"
        constraints = [models.UniqueConstraint(fields=["lat", "lon"], name="ubs_coordenada_unica")]

    def __str__(self):
        return self.nome


class Equipe(models.Model):
    nome = models.CharField(max_length=200)
    ubs = models.ForeignKey(Ubs, on_delete=models.CASCADE, related_name="equipes")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["ubs", "nome"], name="equipe_nome_unico_por_ubs")]

    def __str__(self):
        return self.nome


class Microarea(models.Model):
    equipe = models.ForeignKey(Equipe, on_delete=models.CASCADE, related_name="microareas")
    nome = models.CharField(max_length=200, unique=True, help_text="nome da instância do gerador")
    setores = models.JSONField(default=list, help_text="códigos dos setores censitários")
    bairros = models.JSONField(default=list)
    poligono = models.JSONField(null=True, blank=True, help_text="GeoJSON (lon, lat) da união dos setores")
    area_km2 = models.FloatField(null=True, blank=True)
    moradores_censo = models.IntegerField(null=True, blank=True)
    domicilios_censo = models.IntegerField(null=True, blank=True)
    instancia_dir = models.CharField(max_length=500, help_text="pasta da instância (relativa a INSTANCES_DIR)")
    ubs_node = models.BigIntegerField(help_text="nó da malha a pé onde fica a UBS")
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "microárea"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def path(self) -> Path:
        return Path(settings.INSTANCES_DIR) / self.instancia_dir

    @property
    def numero(self) -> int:
        """Número da microárea na equipe (o id do gerador numa instância de equipe; 1 numa instância de um ACS)."""
        return int((self.meta or {}).get("microarea", {}).get("id") or 1)

    @property
    def rotulo(self) -> str:
        """Nome de exibição: "Microárea 02 · Bom Jesus" (o `nome` é a chave da importação)."""
        from .nomes import rotulo_microarea
        return rotulo_microarea(self.numero, self.bairros or [])


class Agente(models.Model):
    microarea = models.OneToOneField(Microarea, on_delete=models.CASCADE, related_name="agente")
    nome = models.CharField(max_length=200)
    hora_inicio = models.TimeField(default=time(8, 0))
    jornada_min = models.FloatField(default=360, help_text="jornada nominal T (min)")
    jornada_max_min = models.FloatField(default=420, help_text="jornada máxima Tmax (min)")
    velocidade_m_min = models.FloatField(default=75, help_text="velocidade de caminhada (m/min)")
    teto_graves = models.PositiveIntegerField(default=3, help_text="teto K de casos graves por dia")

    class Meta:
        verbose_name = "agente (ACS)"
        verbose_name_plural = "agentes (ACS)"

    def __str__(self):
        return self.nome


class Domicilio(models.Model):
    microarea = models.ForeignKey(Microarea, on_delete=models.CASCADE, related_name="domicilios")
    codigo = models.IntegerField(help_text="linha em instance.gpkg (id do domicílio na instância)")
    node = models.BigIntegerField(help_text="nó da malha a pé em frente à edificação")
    lat = models.FloatField()
    lon = models.FloatField()
    edificacao = models.IntegerField(null=True, blank=True)
    n_moradores = models.PositiveIntegerField(default=1)
    condicao = models.CharField(max_length=50)
    peso = models.FloatField(help_text="peso clínico w")
    intervalo_max_dias = models.PositiveIntegerField(help_text="intervalo máximo entre visitas P (dias)")
    duracao_min = models.FloatField(help_text="duração da visita s (min)")
    ultima_visita = models.DateField()
    tw_inicio = models.FloatField(default=0, help_text="início da janela (min desde o início da jornada)")
    tw_fim = models.FloatField(default=420, help_text="fim da janela (min desde o início da jornada)")
    urgente = models.BooleanField(default=False)
    grave = models.BooleanField(default=False)

    class Meta:
        verbose_name = "domicílio"
        ordering = ["microarea", "codigo"]
        constraints = [models.UniqueConstraint(fields=["microarea", "codigo"], name="domicilio_codigo_unico")]

    def __str__(self):
        return f"{self.microarea} · {self.codigo}"


class Plano(models.Model):
    class Metodo(models.TextChoices):
        GULOSO = "guloso", "guloso"
        ALNS = "alns", "ALNS"
        MILP = "milp", "MILP"

    class Status(models.TextChoices):
        VIAVEL = "viavel", "viável"
        COM_VIOLACOES = "com_violacoes", "com violações"

    agente = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name="planos")
    data = models.DateField()
    metodo = models.CharField(max_length=10, choices=Metodo.choices)
    params = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=Status.choices)
    violacoes = models.JSONField(default=list, blank=True)
    hora_inicio = models.TimeField(help_text="início da jornada usado no plano")
    objetivo = models.FloatField()
    caminhada_min = models.FloatField()
    penalidade_residual = models.FloatField()
    excesso_min = models.FloatField()
    retorno_min = models.FloatField(help_text="H: retorno à UBS (min desde o início da jornada)")
    n_candidatas = models.PositiveIntegerField(default=0)
    n_fora_candidatas = models.PositiveIntegerField(default=0, help_text="viáveis que ficaram fora das candidatas")
    runtime_s = models.FloatField(default=0)
    seed = models.IntegerField(null=True, blank=True)
    seeds_stats = models.JSONField(null=True, blank=True)
    gap = models.FloatField(null=True, blank=True)
    rota_geojson = models.JSONField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        indexes = [models.Index(fields=["agente", "data"])]

    def __str__(self):
        return f"{self.agente} · {self.data} · {self.metodo}"


class ItemRoteiro(models.Model):
    class Motivo(models.TextChoices):
        URGENCIA = "urgencia", "urgência"
        ATRASO = "atraso", "atraso"
        RISCO = "risco", "risco"
        ROTINA = "rotina", "rotina"

    plano = models.ForeignKey(Plano, on_delete=models.CASCADE, related_name="itens")
    ordem = models.PositiveIntegerField()
    domicilio = models.ForeignKey(Domicilio, on_delete=models.PROTECT, related_name="itens_roteiro")
    chegada_min = models.FloatField()
    inicio_min = models.FloatField()
    fim_min = models.FloatField()
    caminhada_min = models.FloatField(help_text="caminhada desde a parada anterior")
    motivo = models.CharField(max_length=10, choices=Motivo.choices)

    class Meta:
        verbose_name = "item do roteiro"
        verbose_name_plural = "itens do roteiro"
        ordering = ["plano", "ordem"]
        constraints = [models.UniqueConstraint(fields=["plano", "ordem"], name="item_ordem_unica")]


class NaoAtendida(models.Model):
    class Motivo(models.TextChoices):
        INVIAVEL = "inviavel", "inviável"
        URGENCIA_EXCEDENTE = "urgencia_excedente", "urgência excedente"
        NAO_COUBE = "nao_coube", "não coube"
        TETO_GRAVES = "teto_graves", "teto de graves"
        RETIRADA_POR_URGENCIA = "retirada_por_urgencia", "retirada por urgência"

    plano = models.ForeignKey(Plano, on_delete=models.CASCADE, related_name="nao_atendidas")
    domicilio = models.ForeignKey(Domicilio, on_delete=models.PROTECT, related_name="nao_atendimentos")
    motivo = models.CharField(max_length=30, choices=Motivo.choices)
    penalidade = models.FloatField()
    dias_sem_visita = models.PositiveIntegerField()
    atraso_dias = models.PositiveIntegerField(help_text="dias além do intervalo máximo: max(0, d − P)")

    class Meta:
        verbose_name = "visita não atendida"
        verbose_name_plural = "visitas não atendidas"
        constraints = [models.UniqueConstraint(fields=["plano", "domicilio"], name="nao_atendida_unica")]
