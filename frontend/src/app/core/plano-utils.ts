import { MotivoNaoAtendida, MotivoVisita, Plano, PlanoResumo } from './models';

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

export interface Selo {
  rotulo: string;
  ok: boolean;
  detalhe: string;
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
  return [
    {
      rotulo: 'urgências primeiro',
      ok: urgenciasPrimeiro,
      detalhe: `${itens.filter((i) => i.urgente).length} urgência(s) no início do roteiro`,
    },
    { rotulo: `graves ≤ K`, ok: graves <= tetoEfetivo, detalhe: `${graves} grave(s), teto ${tetoEfetivo}` },
    { rotulo: 'jornada ≤ Tmax', ok: m.H <= m.jornada_max_min + 1e-6, detalhe: `retorno às ${m.retorno}` },
    { rotulo: 'janelas respeitadas', ok: janelas === 0, detalhe: janelas ? `${janelas} violação(ões)` : 'todas' },
    {
      rotulo: 'urgências atendidas',
      ok: urgentesFora === 0,
      detalhe: urgentesFora ? `${urgentesFora} sem visita` : `${m.urgentes_atendidas} atendida(s)`,
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
