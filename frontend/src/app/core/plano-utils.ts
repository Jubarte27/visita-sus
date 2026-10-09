import { MotivoNaoAtendida, MotivoVisita, Plano, PlanoResumo, SituacaoMicroarea } from './models';

export const ROTULO_MOTIVO_VISITA: Record<MotivoVisita, string> = {
  urgencia: 'urgência',
  atraso: 'atraso',
  risco: 'risco',
  rotina: 'rotina',
};

export const ROTULO_MOTIVO_NAO_ATENDIDA: Record<MotivoNaoAtendida, string> = {
  inviavel: 'inviável',
  urgencia_excedente: 'urgência excedente',
  nao_coube: 'não coube',
  teto_graves: 'teto de graves',
  retirada_por_urgencia: 'retirada por urgência',
};

/** Situação da microárea no relatório: rótulo e ícone (a cor nunca vem sozinha). */
export const ROTULO_SITUACAO: Record<SituacaoMicroarea, { rotulo: string; icone: string }> = {
  ok: { rotulo: 'ok', icone: '✓' },
  atencao: { rotulo: 'atenção', icone: '!' },
  sobrecarga: { rotulo: 'sobrecarga', icone: '⚠' },
  sem_plano: { rotulo: 'sem plano', icone: '–' },
};

/** Peso clínico w (1–5) em palavras. */
export const ROTULO_RISCO: Record<number, string> = {
  1: 'risco baixo',
  2: 'risco moderado',
  3: 'risco alto',
  4: 'risco muito alto',
  5: 'risco máximo',
};

export function rotuloRisco(w: number): string {
  return ROTULO_RISCO[Math.min(5, Math.max(1, Math.round(w)))];
}

/**
 * Situação de um domicílio em relação ao intervalo máximo entre visitas, com o mesmo critério do backend:
 * atrasado quando amanhã já terá passado o intervalo (dias + 1 > P).
 */
export function situacaoVisita(dias: number, P: number): { texto: string; atrasado: boolean } {
  if (dias > P) return { texto: `atrasado ${dias - P} ${dias - P === 1 ? 'dia' : 'dias'}`, atrasado: true };
  if (dias === P) return { texto: 'vence hoje', atrasado: true };
  const faltam = P - dias;
  return { texto: `em dia (faltam ${faltam} ${faltam === 1 ? 'dia' : 'dias'})`, atrasado: false };
}

/** "última visita há 45 dias (máx. 30)". */
export function ultimaVisita(dias: number, P: number): string {
  const quando = dias === 0 ? 'hoje' : dias === 1 ? 'há 1 dia' : `há ${dias} dias`;
  return `última visita ${quando} (máx. ${P})`;
}

export type EstadoIntervalo = 'em_dia' | 'vence' | 'atrasado';

/**
 * Barra do intervalo entre visitas: trilho de 0 a 1,5×P, marca do intervalo máximo P em 2/3 e preenchimento
 * até os dias desde a última visita. `curto` é o rótulo ao lado da barra; `completo`, o texto do tooltip.
 */
export function intervaloVisual(dias: number, P: number) {
  const escala = Math.max(1, P * 1.5);
  const estado: EstadoIntervalo = dias > P ? 'atrasado' : dias === P ? 'vence' : 'em_dia';
  const curto = estado === 'atrasado' ? `+${dias - P} ${dias - P === 1 ? 'dia' : 'dias'}`
    : estado === 'vence' ? 'vence hoje' : `${dias}/${P} dias`;
  return {
    estado,
    pctCheio: (100 * Math.min(dias, escala)) / escala,
    pctLimite: (100 * P) / escala,
    curto,
    completo: `${ultimaVisita(dias, P)} · ${situacaoVisita(dias, P).texto}`,
  };
}

/** Violações do plano (evaluation.violations no engine) em linguagem simples. */
export const ROTULO_VIOLACAO: Record<string, string> = {
  janela: 'visita fora do horário em que o domicílio recebe',
  jornada: 'volta à UBS depois da jornada máxima',
  teto_graves: 'mais casos graves que o limite do dia',
  urgente_ausente: 'urgência que ficou fora do roteiro',
  urgencia_fora_de_ordem: 'urgência visitada depois de uma visita de rotina',
};

export interface Selo {
  rotulo: string;
  ok: boolean;
  detalhe: string;
  ajuda: string; // a regra, em uma frase
}

/** Conferência visual das regras do modelo (§6.4 da proposta) sobre um plano gravado. */
export function selosDoPlano(p: Plano): Selo[] {
  const m = p.metricas;
  const itens = p.itens;
  const primeiraNaoUrgente = itens.findIndex((i) => !i.urgente);
  const ultimaUrgente = itens.map((i) => i.urgente).lastIndexOf(true);
  const urgenciasPrimeiro = primeiraNaoUrgente === -1 || ultimaUrgente < primeiraNaoUrgente;
  const graves = itens.filter((i) => i.grave).length;
  const gravesUrgentes = itens.filter((i) => i.grave && i.urgente).length;
  const tetoEfetivo = Math.max(m.teto_graves, gravesUrgentes);
  const urgentesFora = p.nao_atendidas.filter((n) => n.urgente).length;
  const janelas = p.violacoes.filter((v) => v.tipo === 'janela').length;
  const nUrgentes = itens.filter((i) => i.urgente).length;
  return [
    {
      rotulo: 'urgências primeiro',
      ok: urgenciasPrimeiro,
      detalhe: nUrgentes ? `${nUrgentes} urgência(s) no início do roteiro` : 'nenhuma urgência no dia',
      ajuda: 'Toda urgência é visitada antes das visitas de rotina.',
    },
    {
      rotulo: 'graves no limite',
      ok: graves <= tetoEfetivo,
      detalhe: `${graves} caso(s) grave(s); limite ${tetoEfetivo}`,
      ajuda: `No máximo ${m.teto_graves} casos graves por dia; urgências graves são sempre visitadas.`,
    },
    {
      rotulo: 'volta no horário',
      ok: m.H <= m.jornada_max_min + 1e-6,
      detalhe: `retorno à UBS às ${m.retorno}`,
      ajuda: 'O ACS volta à UBS antes do fim da jornada máxima.',
    },
    {
      rotulo: 'horários respeitados',
      ok: janelas === 0,
      detalhe: janelas ? `${janelas} visita(s) fora do horário` : 'todas no horário',
      ajuda: 'Domicílios que só recebem num turno (manhã ou tarde) são visitados nele.',
    },
    {
      rotulo: 'urgências atendidas',
      ok: urgentesFora === 0,
      detalhe: urgentesFora ? `${urgentesFora} sem visita` : `${m.urgentes_atendidas} atendida(s)`,
      ajuda: 'Nenhuma urgência fica sem visita.',
    },
  ];
}

/** Último plano de cada microárea (a lista da API vem do mais novo para o mais antigo). */
export function ultimoPorMicroarea(planos: PlanoResumo[]): Map<number, PlanoResumo> {
  const out = new Map<number, PlanoResumo>();
  for (const p of planos) {
    const atual = out.get(p.microarea);
    if (!atual || p.criado_em > atual.criado_em) out.set(p.microarea, p);
  }
  return out;
}

/** "08:00:00" + minutos → "HH:MM", truncando os segundos como o backend (14:58:36 → 14:58). */
export function relogio(horaInicio: string, minutos: number): string {
  const [h, m] = horaInicio.split(':').map(Number);
  const total = Math.floor(h * 60 + m + minutos + 1e-9);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(Math.floor(total / 60) % 24)}:${pad(total % 60)}`;
}
