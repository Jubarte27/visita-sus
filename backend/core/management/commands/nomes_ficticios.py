"""
Aplica os nomes de exibição (core.nomes) às equipes e aos ACS já importados com os nomes antigos:
  - ACS chamados "ACS <instância>" passam a ter um nome fictício;
  - equipes chamadas "eSF <instância de equipe>" passam a "eSF <bairro> (N ACS)", o mesmo nome que a importação
    usa hoje (então reimportar a instância continua achando a equipe).

    .venv/bin/python manage.py nomes_ficticios [--dry-run]
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Agente, Equipe
from core.nomes import nome_equipe, nome_ficticio


class Command(BaseCommand):
    help = "Troca os nomes antigos de ACS e equipes (nomes de instância) por nomes de exibição."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="só mostra o que mudaria")

    @transaction.atomic
    def handle(self, *args, dry_run=False, **opts):
        mudancas = []
        for equipe in Equipe.objects.prefetch_related("microareas__agente"):
            microareas = sorted(equipe.microareas.all(), key=lambda m: m.nome)
            instancias = {m.meta.get("nome") or m.nome.rsplit("_", 1)[0] for m in microareas if m.meta.get("equipe")}
            if len(instancias) == 1 and equipe.nome == f"eSF {next(iter(instancias))}":
                bairros = microareas[0].meta.get("microarea", {}).get("bairros") or microareas[0].bairros or []
                novo = nome_equipe(bairros[0] if bairros else next(iter(instancias)), len(microareas))
                mudancas.append((equipe, "nome", equipe.nome, novo))

            usados = {a.nome for m in microareas if (a := getattr(m, "agente", None)) and not a.nome.startswith("ACS ")}
            for m in microareas:
                a = getattr(m, "agente", None)
                if a and a.nome.startswith("ACS "):
                    mudancas.append((a, "nome", a.nome, nome_ficticio(m.nome, usados)))

        for obj, campo, antes, depois in mudancas:
            self.stdout.write(f"{type(obj).__name__.lower()}: {antes} → {depois}")
            if not dry_run:
                setattr(obj, campo, depois)
                obj.save(update_fields=[campo])
        if not mudancas:
            self.stdout.write("nada a mudar")
        elif dry_run:
            transaction.set_rollback(True)
            self.stdout.write("(dry-run: nada gravado)")
