import { DecimalPipe, PercentPipe } from '@angular/common';
import { Component, computed, input, signal } from '@angular/core';

export interface SerieComposicao {
  rotulo: string;
  cor: string;
  tinta: string; // cor do texto dentro do segmento (contraste com `cor`)
}

/** Séries da composição dos domicílios de uma microárea (paleta categórica validada: azul, laranja, verde-água). */
export const SERIES_COMPOSICAO: SerieComposicao[] = [
  { rotulo: 'visitados no dia', cor: '#2a78d6', tinta: '#ffffff' },
  { rotulo: 'atrasados sem visita', cor: '#eb6834', tinta: '#0b0b0b' },
  { rotulo: 'em dia, sem visita', cor: '#1baf7a', tinta: '#0b0b0b' },
];

export interface LinhaComposicao {
  rotulo: string;
  valores: number[] | null; // um valor por série; null = sem dado (ex.: microárea sem plano)
  alerta?: boolean;
}

interface Segmento {
  serie: number;
  valor: number;
  fracao: number;
  x: number;
  largura: number;
  ultimo: boolean;
}

const LINHA = 30;
const ESPESSURA = 18;
const ROTULO = 150; // largura da coluna de rótulos
const LARGURA = 560;
const AREA = LARGURA - ROTULO - 4; // largura de uma barra cheia (100%)
const VAO = 2; // espaço entre segmentos, na cor da superfície
const MIN_ROTULO = 34; // largura mínima para escrever o % dentro do segmento

/**
 * Barras horizontais empilhadas em 100% (uma por categoria): composição de um total em séries, com legenda,
 * % dentro do segmento quando cabe e tooltip por segmento com quantidade e %. Alerta = ícone + texto no rótulo.
 */
@Component({
  selector: 'app-composicao',
  imports: [DecimalPipe, PercentPipe],
  template: `
    <figure>
      <figcaption>{{ titulo() }}</figcaption>
      <ul class="legenda">
        @for (s of series(); track s.rotulo) {
          <li><span class="cor" [style.background]="s.cor"></span>{{ s.rotulo }}</li>
        }
      </ul>
      <svg [attr.viewBox]="'0 0 ' + largura + ' ' + altura()" role="img" [attr.aria-label]="titulo()">
        @for (l of geometria(); track l.rotulo; let i = $index) {
          <text class="rotulo" [attr.x]="x0 - 8" [attr.y]="i * linha + linha / 2" [class.alerta]="l.alerta">
            @if (l.alerta) { <tspan class="icone">⚠ </tspan> }{{ l.rotulo }}</text>
          @if (l.segmentos) {
            @for (s of l.segmentos; track s.serie) {
              <g class="segmento" tabindex="0" [class.ativo]="ativo()?.linha === i && ativo()?.serie === s.serie"
                 (pointerenter)="ativo.set({ linha: i, serie: s.serie })" (pointerleave)="ativo.set(null)"
                 (focus)="ativo.set({ linha: i, serie: s.serie })" (blur)="ativo.set(null)">
                <path [attr.d]="caminho(i, s)" [attr.fill]="series()[s.serie].cor" />
                @if (s.largura >= minRotulo) {
                  <text class="pct" [attr.x]="s.x + s.largura / 2" [attr.y]="i * linha + linha / 2"
                        [attr.fill]="series()[s.serie].tinta">{{ s.fracao | percent: '1.0-0' }}</text>
                }
              </g>
            }
          } @else {
            <text class="sem-dado" [attr.x]="x0 + 6" [attr.y]="i * linha + linha / 2">sem plano</text>
          }
        }
      </svg>
      @if (dica(); as d) {
        <div class="dica" [style.top.px]="d.topo">
          <b>{{ d.valor | number: '1.0-0' }} <small>({{ d.fracao | percent: '1.0-0' }})</small></b>
          <span>{{ d.serie }}</span>
          <small>{{ d.linha }}</small>
        </div>
      }
    </figure>
  `,
  styles: `
    :host {
      --critico: var(--vs-critico);
      --texto: var(--vs-texto);
      --texto-2: var(--vs-texto-2);
      display: block;
    }
    figure { position: relative; margin: 0; }
    figcaption { font-weight: 500; margin-bottom: var(--esp-2); color: var(--texto); }
    .legenda { display: flex; flex-wrap: wrap; gap: var(--esp-1) var(--esp-4); margin: 0 0 var(--esp-3); padding: 0; list-style: none;
      font-size: 12px; color: var(--texto-2); }
    .cor { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
    svg { width: 100%; max-width: 560px; height: auto; overflow: visible; font: 12px Roboto, sans-serif; }
    .rotulo { text-anchor: end; dominant-baseline: middle; fill: var(--texto); }
    .rotulo.alerta { fill: var(--critico); font-weight: 500; }
    .segmento { outline: none; cursor: default; }
    .segmento.ativo path, .segmento:focus-visible path { opacity: .85; }
    .pct { text-anchor: middle; dominant-baseline: middle; font-size: 11px; font-weight: 500; pointer-events: none; }
    .sem-dado { dominant-baseline: middle; fill: var(--texto-2); font-style: italic; }
    .dica {
      position: absolute; left: 160px; transform: translateY(-4px); z-index: 2; pointer-events: none;
      display: flex; flex-direction: column; gap: 1px; padding: 6px 8px; border-radius: 6px;
      background: #fff; box-shadow: 0 2px 8px rgba(0, 0, 0, .2); font-size: 12px; color: var(--texto-2);
      b { font-size: 14px; color: var(--texto); }
    }
  `,
})
export class ComposicaoComponent {
  readonly titulo = input.required<string>();
  readonly series = input.required<SerieComposicao[]>();
  readonly linhas = input.required<LinhaComposicao[]>();

  protected readonly linha = LINHA;
  protected readonly largura = LARGURA;
  protected readonly x0 = ROTULO;
  protected readonly minRotulo = MIN_ROTULO;
  protected readonly ativo = signal<{ linha: number; serie: number } | null>(null);

  protected readonly altura = computed(() => this.linhas().length * LINHA);

  protected readonly geometria = computed(() =>
    this.linhas().map((l) => ({ ...l, segmentos: l.valores ? this.segmentos(l.valores) : null })),
  );

  protected readonly dica = computed(() => {
    const a = this.ativo();
    if (!a) return null;
    const l = this.geometria()[a.linha];
    const s = l?.segmentos?.find((x) => x.serie === a.serie);
    if (!s) return null;
    return { topo: (a.linha + 1) * LINHA, valor: s.valor, fracao: s.fracao, serie: this.series()[s.serie].rotulo,
      linha: l.rotulo };
  });

  private segmentos(valores: number[]): Segmento[] {
    const total = valores.reduce((a, b) => a + Math.max(0, b), 0);
    if (total <= 0) return [];
    const visiveis = valores.map((v, serie) => ({ serie, valor: Math.max(0, v) })).filter((s) => s.valor > 0);
    let x = this.x0;
    return visiveis.map((s, k) => {
      const ultimo = k === visiveis.length - 1;
      const cheio = (s.valor / total) * AREA;
      const largura = Math.max(0, ultimo ? cheio : cheio - VAO);
      const seg = { ...s, fracao: s.valor / total, x, largura, ultimo };
      x += cheio;
      return seg;
    });
  }

  /** Segmento retangular; o último tem a ponta arredondada (4 px), como as barras simples. */
  protected caminho(i: number, s: Segmento): string {
    const y = i * LINHA + (LINHA - ESPESSURA) / 2;
    const { x, largura: w } = s;
    if (w <= 0) return '';
    if (!s.ultimo) return `M${x},${y} H${x + w} V${y + ESPESSURA} H${x} Z`;
    const r = Math.min(4, w / 2, ESPESSURA / 2);
    return `M${x},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + ESPESSURA - r} ` +
      `Q${x + w},${y + ESPESSURA} ${x + w - r},${y + ESPESSURA} H${x} Z`;
  }
}
