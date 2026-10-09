import type { Feature, Point } from 'geojson';

import { DomicilioProps } from '../../core/models';
import { intervaloVisual, relogio, rotuloRisco } from '../../core/plano-utils';

/** Peso clínico w → cor (mesma paleta do mapa.html do gerador: verde → vinho). */
export const CORES_W: Record<number, string> = {
  1: '#4daf4a',
  2: '#ffcc00',
  3: '#ff7f00',
  4: '#e41a1c',
  5: '#7b0000',
};

export function corDoPeso(w: number): string {
  const k = Math.min(5, Math.max(1, Math.round(w)));
  return CORES_W[k];
}

export const NOMES_CONDICAO: Record<string, string> = {
  nenhuma: 'nenhuma',
  hipertensao_diabetes: 'hipertensão/diabetes',
  idoso: 'idoso',
  crianca_menor_2: 'criança < 2 anos',
  gestante: 'gestante',
  acamado: 'acamado',
  tuberculose: 'tuberculose',
};

export function nomeCondicao(c: string): string {
  return NOMES_CONDICAO[c] ?? c;
}

export interface PontoDeAcesso {
  node: number;
  lat: number;
  lon: number;
  domicilios: DomicilioProps[];
  wMax: number;
  urgente: boolean;
  atrasados: number;
}

/** Agrupa os domicílios pelo ponto de acesso na malha (prédios e casas no mesmo ponto da rua). */
export function agruparPorPonto(features: Feature<Point, DomicilioProps>[]): PontoDeAcesso[] {
  const grupos = new Map<number, PontoDeAcesso>();
  for (const f of features) {
    const p = f.properties;
    const [lon, lat] = f.geometry.coordinates;
    let g = grupos.get(p.node);
    if (!g) {
      g = { node: p.node, lat, lon, domicilios: [], wMax: 0, urgente: false, atrasados: 0 };
      grupos.set(p.node, g);
    }
    g.domicilios.push(p);
    g.wMax = Math.max(g.wMax, p.w);
    g.urgente ||= p.urgente;
    g.atrasados += p.atrasado ? 1 : 0;
  }
  return [...grupos.values()];
}

export function raioDoPonto(n: number): number {
  return 4 + Math.min(n, 10) ** 0.7;
}

/** Janela de atendimento em horário real: "manhã (08:00–11:00)", "tarde (11:00–14:00)" ou "qualquer horário". */
export function janelaHorario(twInicio: number, twFim: number, horaInicio = '08:00:00'): string {
  if (twInicio === 0 && twFim >= 420) return 'qualquer horário';
  const periodo = twInicio === 0 ? 'manhã' : 'tarde';
  return `${periodo} (${relogio(horaInicio, twInicio)}–${relogio(horaInicio, twFim)})`;
}

const MAX_CARTOES = 8;

function escapar(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}

/** Medidor de risco em HTML (mesma marcação do componente app-risco), para os popups do Leaflet. */
export function htmlRisco(w: number): string {
  const nivel = Math.min(5, Math.max(1, Math.round(w)));
  const cor = corDoPeso(w);
  const barras = [1, 2, 3, 4, 5].map((n) => `<i${n <= nivel ? ` style="background:${cor}"` : ''}></i>`).join('');
  return `<span class="risco-medidor" role="img" aria-label="${rotuloRisco(w)}" title="${rotuloRisco(w)}">${barras}</span>`;
}

/** Barra do intervalo entre visitas em HTML (mesma marcação do componente app-intervalo). */
export function htmlIntervalo(dias: number, P: number): string {
  const v = intervaloVisual(dias, P);
  return `<span class="intervalo" data-estado="${v.estado}" title="${v.completo}" role="img" aria-label="${v.completo}">` +
    `<span class="trilho"><span class="cheio" style="width:${v.pctCheio.toFixed(1)}%"></span>` +
    `<span class="limite" style="left:${v.pctLimite.toFixed(1)}%"></span></span><span class="rotulo">${v.curto}</span></span>`;
}

function icone(nome: string, titulo: string): string {
  return `<span class="material-icons" aria-label="${titulo}" title="${titulo}">${nome}</span>`;
}

/** Cartão de um domicílio no popup: condição, risco, urgente/grave, intervalo, duração, horário e moradores. */
function cartao(p: DomicilioProps, horaInicio: string): string {
  const chips = (p.urgente ? '<span class="chip-mini urgente">urgente</span>' : '') +
    (p.grave ? '<span class="chip-mini">grave</span>' : '');
  return `<div class="dom-card">
    <div class="t"><b>${escapar(nomeCondicao(p.condicao))}</b>${htmlRisco(p.w)}${chips}<span class="cod">#${p.codigo}</span></div>
    <div>${htmlIntervalo(p.dias_sem_visita, p.P)}</div>
    <div class="m">${icone('timer', 'duração da visita')}${p.duracao_min} min
      ${icone('schedule', 'quando recebe')}${janelaHorario(p.tw_inicio, p.tw_fim, horaInicio)}
      ${icone('group', 'moradores')}${p.n_moradores}</div>
  </div>`;
}

/** Popup de um ponto de acesso: um cartão por domicílio, os mais prioritários primeiro. */
export function popupDoPonto(g: PontoDeAcesso, horaInicio = '08:00:00'): string {
  const ordenados = [...g.domicilios].sort((a, b) => b.penalidade - a.penalidade);
  const cartoes = ordenados.slice(0, MAX_CARTOES).map((p) => cartao(p, horaInicio)).join('');
  const resto = ordenados.length - MAX_CARTOES;
  const titulo = `${g.domicilios.length} domicílio(s) neste ponto` + (g.atrasados ? ` · ${g.atrasados} atrasado(s)` : '');
  return `<div class="popup-ponto"><div class="titulo">${titulo}</div>${cartoes}` +
    (resto > 0 ? `<div class="m">+ ${resto} domicílio(s) de menor prioridade</div>` : '') + '</div>';
}

export interface Seta {
  lat: number;
  lon: number;
  angulo: number; // graus na tela, sentido horário a partir do leste (para CSS rotate)
}

/**
 * Pontos ao longo da rota (LineString em lon/lat), a cada `passoM` metros, com a direção do trecho: setas que
 * mostram o sentido do percurso. Usa uma projeção local (equiretangular), suficiente na escala de uma microárea.
 */
export function setasDaRota(coords: number[][], passoM: number): Seta[] {
  const out: Seta[] = [];
  let acumulado = 0;
  let proxima = passoM / 2;
  for (let i = 1; i < coords.length; i++) {
    const [x0, y0] = coords[i - 1];
    const [x1, y1] = coords[i];
    const dx = (x1 - x0) * 111320 * Math.cos((y0 * Math.PI) / 180);
    const dy = (y1 - y0) * 110540;
    const d = Math.hypot(dx, dy);
    while (d > 0 && acumulado + d >= proxima) {
      const f = (proxima - acumulado) / d;
      out.push({ lon: x0 + (x1 - x0) * f, lat: y0 + (y1 - y0) * f, angulo: (Math.atan2(-dy, dx) * 180) / Math.PI });
      proxima += passoM;
    }
    acumulado += d;
  }
  return out;
}

/** Comprimento aproximado (m) de uma linha em lon/lat. */
export function comprimentoM(coords: number[][]): number {
  let total = 0;
  for (let i = 1; i < coords.length; i++) {
    const [x0, y0] = coords[i - 1];
    const [x1, y1] = coords[i];
    total += Math.hypot((x1 - x0) * 111320 * Math.cos((y0 * Math.PI) / 180), (y1 - y0) * 110540);
  }
  return total;
}
