from django.core.management.base import BaseCommand

from engine import validate


class Command(BaseCommand):
    help = ("Validação experimental (P16): guloso, ALNS por semente e MILP em subinstâncias, sobre os arquivos das "
            "instâncias; grava data/resultados/validacao.csv. Aceita as opções de `python -m engine.validate`.")

    def add_arguments(self, parser):
        parser.add_argument("opcoes", nargs="*", help="repassadas a engine.validate (ex.: --sementes 10 --milp-n 10)")

    def handle(self, *args, **opts):
        validate.main(opts["opcoes"])
