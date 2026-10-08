import type { Feature, Point } from 'geojson';

import { DomicilioProps } from '../../core/models';

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

function janela(p: DomicilioProps): string {
  return p.tw_inicio === 0 && p.tw_fim >= 420 ? '—' : `${p.tw_inicio}–${p.tw_fim} min`;
}

function escapar(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}

/** Popup de um ponto de acesso: uma linha por domicílio, os de maior penalidade primeiro. */
export function popupDoPonto(g: PontoDeAcesso): string {
  const linhas = [...g.domicilios]
    .sort((a, b) => b.penalidade - a.penalidade)
    .map(
      (p) => `<tr>
        <td>${p.codigo}</td><td>${escapar(nomeCondicao(p.condicao))}</td><td>${p.w}</td>
        <td>${p.dias_sem_visita}/${p.P}${p.atrasado ? ' <b style="color:#c62828">atrasado</b>' : ''}</td>
        <td>${p.duracao_min}</td><td>${janela(p)}</td>
        <td>${p.urgente ? '<b style="color:#c62828">sim</b>' : ''}</td><td>${p.grave ? 'sim' : ''}</td>
        <td>${p.penalidade.toFixed(2)}</td></tr>`,
    )
    .join('');
  const titulo = `${g.domicilios.length} domicílio(s) neste ponto`;
  return `<b>${titulo}</b><table class="domicilios">
    <tr><th>cód.</th><th>condição</th><th>w</th><th>dias/P</th><th>min</th><th>janela</th><th>urg.</th>
    <th>grave</th><th>pen.</th></tr>${linhas}</table>`;
}
