from datetime import date

from django.core.management.base import BaseCommand, CommandError

from core.importer import ImportacaoError, importar_instancia


class Command(BaseCommand):
    help = "Importa uma instância do gerador (pasta com meta.json, instance.gpkg e graph.graphml) para o banco."

    def add_arguments(self, parser):
        parser.add_argument("pasta", help="pasta da instância (ex.: data/instances/bomjesus)")
        parser.add_argument("--equipe", help="nome da equipe (padrão: eSF <bairro>, ou eSF <instância> numa equipe); "
                                             "instâncias da mesma UBS e mesmo nome de equipe ficam juntas")
        parser.add_argument("--agente", help="nome do ACS (padrão: ACS <instância>); numa equipe, prefixo + nº da microárea")
        parser.add_argument("--ubs-nome", help="nome da UBS (padrão: UBS <bairro>)")
        parser.add_argument("--data-base", type=date.fromisoformat,
                            help="data até a qual os dias desde a última visita são contados (padrão: a do meta.json)")

    def handle(self, *args, **opts):
        try:
            microareas = importar_instancia(opts["pasta"], equipe=opts["equipe"], agente=opts["agente"],
                                            data_base=opts["data_base"], ubs_nome=opts["ubs_nome"])
        except (ImportacaoError, FileNotFoundError) as e:
            raise CommandError(str(e)) from None
        for m in microareas:
            self.stdout.write(self.style.SUCCESS(
                f"microárea {m.nome} (id {m.pk}) · equipe {m.equipe} · UBS {m.equipe.ubs} · agente {m.agente} · "
                f"{m.domicilios.count()} domicílios"))
