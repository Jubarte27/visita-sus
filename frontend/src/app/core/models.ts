// Tipos da API do backend (docs/passos-implementacao.md, Apêndice E).
import type { FeatureCollection, LineString, MultiPolygon, Point, Polygon } from 'geojson';

export type Metodo = 'guloso' | 'alns' | 'milp';
export type MotivoVisita = 'urgencia' | 'atraso' | 'risco' | 'rotina';
export type MotivoNaoAtendida =
  | 'inviavel'
  | 'urgencia_excedente'
  | 'nao_coube'
  | 'teto_graves'
  | 'retirada_por_urgencia';

export interface Ref {
  id: number;
  nome: string;
}

export interface Ubs extends Ref {
  lat: number;
  lon: number;
}

export interface Agente extends Ref {
  microarea: number;
  hora_inicio: string; // "08:00:00"
  jornada_min: number;
  jornada_max_min: number;
  velocidade_m_min: number;
  teto_graves: number;
}

export interface MicroareaResumo extends Ref {
  rotulo: string; // "Microárea 02 · Bom Jesus" (o `nome` é o da instância)
  area_km2: number | null;
  n_domicilios: number;
  agente: Agente | null;
}

export interface Equipe extends Ref {
  ubs: Ubs;
  microareas: MicroareaResumo[];
}

export interface Microarea extends Ref {
  rotulo: string;
  equipe: Ref;
  ubs: Ubs;
  agente: Ref | null;
  setores: string[];
  bairros: string[];
  area_km2: number | null;
  moradores_censo: number | null;
  domicilios_censo: number | null;
  n_domicilios: number;
  poligono: Polygon | MultiPolygon | null;
}

export interface DomicilioProps {
  id: number;
  codigo: number;
  condicao: string;
  w: number;
  P: number;
  duracao_min: number;
  ultima_visita: string;
  dias_sem_visita: number;
  penalidade: number;
  atrasado: boolean;
  atraso_dias: number;
  urgente: boolean;
  grave: boolean;
  tw_inicio: number;
  tw_fim: number;
  n_moradores: number;
  node: number;
}

export type Domicilios = FeatureCollection<Point, DomicilioProps> & { data: string };
export type Malha = FeatureCollection<LineString, { length_m: number; highway: string }>;

export interface Params {
  beta?: number;
  gamma?: number;
  n_candidatas?: number;
  iterations?: number;
  time_limit_s?: number;
  seeds?: number[];
  destroy_min?: number;
  destroy_max?: number;
  t_start?: number;
  cooling?: number;
}

export interface SeedsStats {
  sementes: number[];
  objetivos: number[];
  media: number;
  desvio: number;
  melhor: number;
  pior: number;
  tempos_s: number[];
}

export interface Metricas {
  objetivo: number;
  caminhada_min: number;
  penalidade_residual: number;
  penalidade_residual_min: number;
  excesso_min: number;
  H: number;
  retorno: string;
  jornada_min: number;
  jornada_max_min: number;
  teto_graves: number;
  visitas: number;
  candidatas: number;
  fora_das_candidatas: number;
  urgentes_atendidas: number;
  graves: number;
  nao_atendidas: number;
  runtime_s: number;
  seed: number | null;
  seeds_stats: SeedsStats | null;
  gap: number | null;
}

export interface ItemRoteiro {
  ordem: number;
  domicilio: number;
  codigo: number;
  lat: number;
  lon: number;
  condicao: string;
  motivo: MotivoVisita;
  w: number;
  urgente: boolean;
  grave: boolean;
  dias_sem_visita: number;
  P: number;
  chegada: string;
  inicio: string;
  fim: string;
  espera_min: number;
  caminhada_min: number;
  duracao_min: number;
}

export interface NaoAtendida {
  domicilio: number;
  codigo: number;
  lat: number;
  lon: number;
  condicao: string;
  motivo: MotivoNaoAtendida;
  w: number;
  urgente: boolean;
  grave: boolean;
  penalidade: number;
  dias_sem_visita: number;
  atraso_dias: number;
  P: number;
}

export interface Violacao {
  tipo: string;
  domicilio: number | null;
  quanto: number;
}

export interface Plano {
  id: number;
  agente: Ref;
  microarea: number;
  data: string;
  metodo: Metodo;
  params: Params & { acs?: { T: number; Tmax: number; K: number; velocidade_m_min: number } };
  status: 'viavel' | 'com_violacoes';
  violacoes: Violacao[];
  hora_inicio: string;
  metricas: Metricas;
  ubs: Ubs;
  itens: ItemRoteiro[];
  nao_atendidas: NaoAtendida[];
  rota: LineString | null;
  links: { csv: string; gpx: string };
  criado_em: string;
}

export interface PlanoResumo {
  id: number;
  agente: Ref;
  microarea: number;
  data: string;
  metodo: Metodo;
  status: 'viavel' | 'com_violacoes';
  objetivo: number;
  caminhada_min: number;
  penalidade_residual: number;
  excesso_min: number;
  retorno_min: number;
  retorno: string;
  visitas: number;
  nao_atendidas: number;
  n_candidatas: number;
  runtime_s: number;
  criado_em: string;
}

export interface MetodoComparado {
  metodo: Metodo;
  objetivo: number;
  caminhada_min: number;
  penalidade_residual: number;
  excesso_min: number;
  retorno: string;
  visitas: number;
  viavel: boolean;
  runtime_s: number;
  gap_para_milp: number;
  gap_solver: number | null;
  seeds_stats: SeedsStats | null;
  ordem: number[];
  rota: LineString | null;
}

export interface Comparacao {
  plano: number;
  candidatas: number;
  subinstancia: number | null;
  seed: number;
  tempo_milp: number;
  metodos: MetodoComparado[];
}

export interface PlanejarEquipeResposta {
  equipe: number;
  data: string;
  metodo: Metodo;
  planos: PlanoResumo[];
}

export type SituacaoMicroarea = 'ok' | 'atencao' | 'sobrecarga' | 'sem_plano';

export interface LinhaRelatorio {
  microarea: Ref & { rotulo: string };
  agente: Ref | null;
  plano: { id: number; metodo: Metodo; status: string } | null;
  sem_plano: boolean;
  domicilios: number;
  atrasados: number;
  prioritarios: number; // urgentes ou atrasados
  candidatas?: number;
  planejadas?: number;
  nao_atendidas?: number;
  nao_atendidas_por_motivo?: Partial<Record<MotivoNaoAtendida, number>>;
  fora_das_candidatas?: number;
  atrasados_fora?: number;
  atrasados_visitados?: number;
  em_dia_sem_visita?: number;
  cobertura_atrasados?: number | null; // fração dos atrasados visitados no dia
  urgentes_fora?: number;
  prioritarios_fora?: number;
  dias_atraso_fora?: number; // Σ max(0, d − P) dos atrasados sem visita
  penalidade_residual?: number;
  penalidade_residual_min?: number;
  caminhada_min?: number;
  jornada_usada_min?: number;
  jornada_min?: number;
  jornada_max_min?: number;
  excesso_min?: number;
  retorno?: string;
  alerta_sobrecarga: boolean;
  motivos_alerta: string[];
  situacao: SituacaoMicroarea;
  resumo_situacao: string;
}

export interface TotalRelatorio {
  microareas: number;
  com_plano: number;
  sem_plano: number;
  alertas: number;
  domicilios: number;
  atrasados: number;
  prioritarios: number;
  candidatas: number;
  planejadas: number;
  nao_atendidas: number;
  nao_atendidas_por_motivo: Partial<Record<MotivoNaoAtendida, number>>;
  fora_das_candidatas: number;
  atrasados_fora: number;
  atrasados_visitados: number;
  em_dia_sem_visita: number;
  urgentes_fora: number;
  prioritarios_fora: number;
  dias_atraso_fora: number;
  penalidade_residual_min: number;
  caminhada_min: number;
  jornada_usada_min: number;
  excesso_min: number;
  acs_com_hora_extra: number;
  excesso_max_min: number;
  caminhada_media_min: number | null;
  cobertura_atrasados: number | null;
}

export interface Relatorio {
  equipe: Ref;
  ubs: Ubs;
  data: string;
  limiares: { excesso_min: number; fracao_atrasados_fora: number };
  resumo: string;
  linhas: LinhaRelatorio[];
  total: TotalRelatorio;
}
