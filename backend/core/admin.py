from django.contrib import admin

from .models import Agente, Domicilio, Equipe, ItemRoteiro, Microarea, NaoAtendida, Plano, Ubs


@admin.register(Ubs)
class UbsAdmin(admin.ModelAdmin):
    list_display = ["nome", "lat", "lon"]
    search_fields = ["nome"]


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ["nome", "ubs"]
    list_filter = ["ubs"]
    search_fields = ["nome"]


class AgenteInline(admin.StackedInline):
    model = Agente
    extra = 0


@admin.register(Microarea)
class MicroareaAdmin(admin.ModelAdmin):
    list_display = ["nome", "equipe", "area_km2", "moradores_censo", "domicilios_censo", "n_domicilios"]
    list_filter = ["equipe"]
    search_fields = ["nome"]
    readonly_fields = ["setores", "bairros", "poligono", "meta", "ubs_node", "instancia_dir"]
    inlines = [AgenteInline]

    @admin.display(description="domicílios")
    def n_domicilios(self, obj):
        return obj.domicilios.count()


@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ["nome", "microarea", "hora_inicio", "jornada_min", "jornada_max_min", "teto_graves"]
    list_filter = ["microarea__equipe"]
    search_fields = ["nome"]


@admin.register(Domicilio)
class DomicilioAdmin(admin.ModelAdmin):
    list_display = ["codigo", "microarea", "condicao", "peso", "intervalo_max_dias", "ultima_visita", "urgente", "grave"]
    list_filter = ["microarea", "condicao", "urgente", "grave"]
    search_fields = ["codigo"]
    list_per_page = 50


class ItemRoteiroInline(admin.TabularInline):
    model = ItemRoteiro
    extra = 0
    can_delete = False
    readonly_fields = ["ordem", "domicilio", "chegada_min", "inicio_min", "fim_min", "caminhada_min", "motivo"]


class NaoAtendidaInline(admin.TabularInline):
    model = NaoAtendida
    extra = 0
    can_delete = False
    readonly_fields = ["domicilio", "motivo", "penalidade", "dias_sem_visita", "atraso_dias"]


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ["agente", "data", "metodo", "status", "objetivo", "caminhada_min", "excesso_min", "criado_em"]
    list_filter = ["metodo", "status", "agente__microarea__equipe", "data"]
    readonly_fields = [f.name for f in Plano._meta.fields]
    inlines = [ItemRoteiroInline, NaoAtendidaInline]
