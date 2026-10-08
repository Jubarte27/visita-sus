"""
Contrato do engine: estruturas compartilhadas por guloso, ALNS, MILP e backend.

Uma Instance é o problema de 1 ACS em 1 dia: a UBS (índice 0) e as visitas candidatas já
pré-processadas (índices 1..n-1). Visitas descartadas no pré-processamento (inviáveis, urgências
excedentes) não entram na Instance; são reportadas à parte. Toda urgente da Instance é obrigatória.

Tempos em minutos desde o início da jornada; distâncias já convertidas em minutos de caminhada.
"""

from dataclasses import asdict, dataclass, field

import numpy as np

# motivo de cada visita feita (Stop.reason)
MOTIVOS_VISITA = ("urgencia", "atraso", "risco", "rotina")
# motivo de cada visita não feita (Solution.unvisited)
MOTIVOS_NAO_ATENDIDA = ("inviavel", "urgencia_excedente", "nao_coube", "teto_graves", "retirada_por_urgencia")
W_RISCO = 3  # peso clínico a partir do qual uma visita não urgente e não atrasada é "risco"


@dataclass
class Visit:
    id: int                      # id do Domicilio no banco (ou linha do gpkg); a UBS usa -1
    node: int                    # nó da malha a pé
    s: float                     # duração da visita (min)
    w: float                     # peso clínico
    P: int                       # intervalo máximo entre visitas (dias)
    d: int                       # dias desde a última visita (calculado no pré-processamento)
    tw: tuple[float, float]      # janela de início [a, b] em min desde o início da jornada
    urgent: bool = False
    grave: bool = False

    @property
    def penalty(self) -> float:
        """Penalidade de deixar a visita para depois: w·(d+1)/P (§6.4). Zero para a UBS."""
        return self.w * (self.d + 1) / self.P if self.P > 0 else 0.0

    @property
    def overdue(self) -> bool:
        """Amanhã já terá passado o intervalo máximo (mesmo critério de `atrasado` do gerador)."""
        return self.P > 0 and self.d + 1 > self.P


@dataclass
class Instance:
    visits: list[Visit]          # visits[0] é a UBS
    t: np.ndarray                # t[i, j]: tempo a pé de i até j (min), indexado como visits
    T: float = 360.0             # jornada nominal (min)
    Tmax: float = 420.0          # jornada máxima tolerada (min)
    K: int = 3                   # teto de casos graves por dia

    def __post_init__(self):
        self.t = np.asarray(self.t, dtype=float)
        n = len(self.visits)
        if n == 0:
            raise ValueError("instância sem UBS")
        if self.t.shape != (n, n):
            raise ValueError(f"matriz t {self.t.shape} não corresponde a {n} visitas")
        if self.T > self.Tmax:
            raise ValueError("jornada nominal T maior que Tmax")

    @property
    def n(self) -> int:
        return len(self.visits)

    @property
    def candidates(self) -> range:
        """Índices das visitas candidatas (todas menos a UBS)."""
        return range(1, self.n)

    @property
    def urgent(self) -> list[int]:
        return [i for i in self.candidates if self.visits[i].urgent]


@dataclass
class Params:
    # padrões calibrados no P16 (docs/resultados.md): β/γ pela política "hora extra é exceção"
    # (menor γ com excesso médio ≤ 10 min para β = 30); ALNS por Taguchi L9 + confirmação
    beta: float = 30.0           # min por unidade de penalidade
    gamma: float = 20.0          # min por min de excesso de jornada
    n_candidatas: int = 40       # candidatas do dia além das urgentes
    iterations: int = 1000
    time_limit_s: float = 5.0
    seeds: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    destroy_min: float = 0.20    # fração mínima removida pela destruição da ALNS
    destroy_max: float = 0.50
    t_start: float = 200.0       # temperatura inicial do Simulated Annealing
    cooling: float = 0.999


@dataclass
class Stop:
    visit: int                   # índice em Instance.visits
    arrival: float               # chegada (min desde o início da jornada)
    start: float                 # início do atendimento (após esperar a janela abrir)
    end: float                   # fim do atendimento
    walk_from_prev: float        # caminhada desde a parada anterior (min)
    reason: str = ""             # um de MOTIVOS_VISITA


@dataclass
class Violation:
    kind: str                    # janela | jornada | teto_graves | urgente_ausente | urgencia_fora_de_ordem
    visit: int | None = None     # índice da visita envolvida, quando houver
    amount: float = 0.0          # quanto passou do limite (min ou nº de casos)


@dataclass
class Solution:
    route: list[int]                  # índices em visits; começa e termina em 0
    stops: list[Stop]
    unvisited: list[tuple[int, str]]  # (índice, motivo) das candidatas fora da rota
    walk: float
    residual_penalty: float
    overtime: float
    objective: float
    H: float                          # retorno à UBS (min desde o início da jornada)
    method: str                       # guloso | alns | milp
    seed: int | None = None
    runtime_s: float = 0.0
    seeds_stats: dict | None = None   # estatísticas do objetivo entre sementes (ALNS)
    gap: float | None = None          # só MILP
    violations: list[Violation] = field(default_factory=list)

    @property
    def feasible(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict:
        return {**asdict(self), "feasible": self.feasible}
