from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("equipes/", views.EquipeList.as_view(), name="equipe-list"),
    path("equipes/<int:pk>/", views.EquipeDetail.as_view(), name="equipe-detail"),
    path("equipes/<int:pk>/planejar/", views.equipe_planejar, name="equipe-planejar"),
    path("equipes/<int:pk>/relatorio/", views.equipe_relatorio, name="equipe-relatorio"),
    path("microareas/<int:pk>/", views.MicroareaDetail.as_view(), name="microarea-detail"),
    path("microareas/<int:pk>/domicilios/", views.microarea_domicilios, name="microarea-domicilios"),
    path("microareas/<int:pk>/malha/", views.microarea_malha, name="microarea-malha"),
    path("agentes/<int:pk>/", views.AgenteDetail.as_view(), name="agente-detail"),
    path("planos/", views.PlanoList.as_view(), name="plano-list"),
    path("planos/<int:pk>/", views.PlanoDetail.as_view(), name="plano-detail"),
    path("planos/<int:pk>/comparar/", views.plano_comparar, name="plano-comparar"),
    path("planos/<int:pk>/itinerario.csv", views.plano_csv, name="plano-csv"),
    path("planos/<int:pk>/itinerario.gpx", views.plano_gpx, name="plano-gpx"),
]
