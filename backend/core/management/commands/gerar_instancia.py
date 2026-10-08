from datetime import date

from django.core.management.base import BaseCommand, CommandError

from core.importer import ImportacaoError, importar_instancia
from engine import generator


class Command(BaseCommand):
    help = ("Gera uma instância sintética ao redor de uma UBS (OpenStreetMap + Censo 2022; precisa de rede e de "
            "./fetch.sh) e importa para o banco.")

    def add_arguments(self, parser):
        parser.add_argument("--ubs", required=True, help="lat,lon da UBS (use --ubs=-30.04,-51.15)")
        parser.add_argument("--name", required=True, help="nome da instância (pasta em data/instances)")
        parser.add_argument("--populacao", type=int, default=750, help="população de cada microárea")
        parser.add_argument("--acs", type=int, default=1, help="nº de ACS: equipe com N microáreas contíguas")
        parser.add_argument("--seed", type=int, default=0)
        parser.add_argument("--urgencia", type=float, default=0.02)
        parser.add_argument("--atraso", type=float, default=1.5)
        parser.add_argument("--candidatas", type=int, default=40)
        parser.add_argument("--data-base", type=date.fromisoformat, default=None)
        parser.add_argument("--equipe")
        parser.add_argument("--agente")
        parser.add_argument("--ubs-nome")

    def handle(self, *args, **opts):
        try:
            lat, lon = (float(x) for x in opts["ubs"].split(","))
        except ValueError:
            raise CommandError("--ubs deve ser lat,lon (ex.: --ubs=-30.0431944,-51.1563369)") from None
        self.stdout.write(f"gerando {opts['name']} (consulta o OpenStreetMap; pode levar alguns minutos)…")
        out, _ = generator.generate((lat, lon), opts["name"], opts["populacao"], opts["seed"], opts["urgencia"],
                                    opts["atraso"], opts["candidatas"], data_base=opts["data_base"], n_acs=opts["acs"])
        try:
            microareas = importar_instancia(out, equipe=opts["equipe"], agente=opts["agente"], ubs_nome=opts["ubs_nome"])
        except ImportacaoError as e:
            raise CommandError(str(e)) from None
        for m in microareas:
            self.stdout.write(self.style.SUCCESS(
                f"microárea {m.nome} (id {m.pk}) · equipe {m.equipe} · {m.domicilios.count()} domicílios"))
