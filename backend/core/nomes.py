"""
Nomes de exibição para os dados sintéticos: ACS com nomes fictícios, microáreas numeradas e equipes pelo bairro.

Os nomes são determinísticos (derivados do nome da instância), então reimportar a mesma instância dá os mesmos
nomes. `Microarea.nome` e `Equipe.nome` continuam sendo as chaves da importação.
"""

import hashlib

NOMES = ["Ana", "Bruno", "Carla", "Daniel", "Eliane", "Fábio", "Gabriela", "Henrique", "Isabel", "João", "Karina",
         "Lucas", "Mariana", "Nelson", "Olívia", "Paulo", "Queila", "Rafael", "Sandra", "Tiago", "Úrsula", "Vinícius",
         "Wanda", "Yasmin", "Zeca", "Beatriz", "Cláudio", "Denise", "Everton", "Fernanda"]
SOBRENOMES = ["Silva", "Souza", "Oliveira", "Santos", "Pereira", "Lima", "Carvalho", "Ferreira", "Rodrigues", "Almeida",
              "Costa", "Gomes", "Martins", "Araújo", "Ribeiro", "Barbosa", "Rocha", "Dias", "Moreira", "Cardoso",
              "Teixeira", "Correia", "Mendes", "Nunes", "Machado", "Freitas", "Vieira", "Monteiro", "Pinto", "Ramos"]


def nome_ficticio(chave: str, usados: set[str] | None = None) -> str:
    """Nome e sobrenome fictícios derivados de `chave`, diferente dos já `usados` (que recebe o novo nome)."""
    usados = usados if usados is not None else set()
    h = int(hashlib.sha256(chave.encode()).hexdigest(), 16)
    for k in range(len(NOMES) * len(SOBRENOMES)):
        nome = f"{NOMES[(h + k) % len(NOMES)]} {SOBRENOMES[(h // len(NOMES) + 7 * k) % len(SOBRENOMES)]}"
        if nome not in usados:
            usados.add(nome)
            return nome
    raise ValueError("nomes fictícios esgotados")


def nome_equipe(bairro: str, n_acs: int) -> str:
    """Nome padrão da equipe: "eSF <bairro>", e "(N ACS)" numa instância de equipe."""
    return f"eSF {bairro}" + (f" ({n_acs} ACS)" if n_acs > 1 else "")


def rotulo_microarea(numero: int, bairros: list[str]) -> str:
    """ "Microárea 02 · Bom Jesus" (o bairro principal, se houver)."""
    return f"Microárea {numero:02d}" + (f" · {bairros[0]}" if bairros else "")
