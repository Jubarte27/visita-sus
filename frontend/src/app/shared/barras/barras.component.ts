import { DecimalPipe } from '@angular/common';
import { Component, computed, input, signal } from '@angular/core';

export interface Barra {
  rotulo: string;
  valor: number | null; // null = sem dado (ex.: microárea sem plano)
  alerta?: boolean;
  detalhe?: string;
}

const LINHA = 30;
const ESPESSURA = 16;
const ROTULO = 150; // largura da coluna de rótulos
const VALOR = 64; // espaço para o valor depois da ponta
const LARGURA = 560;

/**
 * Barras horizontais de uma série (uma barra por categoria), com valor na ponta, linha de referência
 * opcional e tooltip por barra. Alerta = ícone + texto no rótulo (a cor da barra não muda).
 */
@Component({
  selector: 'app-barras',
  imports: [DecimalPipe],
  template: `
    <figure>
      <figcaption>{{ titulo() }}</figcaption>
      <svg [attr.viewBox]="'0 0 ' + largura + ' ' + altura()" role="img" [attr.aria-label]="titulo()">
        <line class="base" [attr.x1]="x0" [attr.x2]="x0" y1="0" [attr.y2]="altura() - 18" />
        @for (b of barras(); track b.rotulo; let i = $index) {
          <g class="linha" tabindex="0" (pointerenter)="ativa.set(i)" (pointerleave)="ativa.set(null)"
             (focus)="ativa.set(i)" (blur)="ativa.set(null)" [class.ativa]="ativa() === i">
            <rect class="alvo" x="0" [attr.y]="i * linha" [attr.width]="largura" [attr.height]="linha" />
            <text class="rotulo" [attr.x]="x0 - 8" [attr.y]="i * linha + linha / 2" [class.alerta]="b.alerta">
              @if (b.alerta) { <tspan class="icone">⚠ </tspan> }{{ b.rotulo }}</text>
            @if (b.valor !== null) {
              <path class="barra" [attr.d]="caminho(i, b.valor)" />
              <text class="valor" [attr.x]="x0 + escala(b.valor) + 6" [attr.y]="i * linha + linha / 2">
                {{ b.valor | number: '1.0-0' }}{{ unidade() }}</text>
            } @else {
              <text class="sem-dado" [attr.x]="x0 + 6" [attr.y]="i * linha + linha / 2">sem plano</text>
            }
          </g>
        }
        @if (referencia(); as r) {
          <line class="ref" [attr.x1]="x0 + escala(r.valor)" [attr.x2]="x0 + escala(r.valor)" y1="0"
                [attr.y2]="altura() - 18" />
          <text class="ref-rotulo" [attr.x]="x0 + escala(r.valor)" [attr.y]="altura() - 4">{{ r.rotulo }}</text>
        }
      </svg>
      @if (ativa() !== null) {
        @let b = barras()[ativa()!];
        <div class="dica" [style.top.px]="(ativa()! + 1) * linha">
          <b>{{ b.valor === null ? 'sem plano' : (b.valor | number: '1.0-1') + unidade() }}</b>
          <span>{{ b.rotulo }}</span>
          @if (b.detalhe) { <small>{{ b.detalhe }}</small> }
        </div>
      }
    </figure>
  `,
  styles: `
    :host {
      --serie: #2a78d6;
      --critico: #d03b3b;
      --texto: #0b0b0b;
      --texto-2: #52514e;
      --grade: #d8d7d3;
      display: block;
    }
    figure { position: relative; margin: 0; }
    figcaption { font-weight: 500; margin-bottom: 6px; color: var(--texto); }
    svg { width: 100%; max-width: 560px; height: auto; overflow: visible; font: 12px Roboto, sans-serif; }
    .alvo { fill: transparent; }
    .linha { outline: none; cursor: default; }
    .linha.ativa .alvo, .linha:focus-visible .alvo { fill: rgba(0, 0, 0, .04); }
    .linha.ativa .barra { opacity: .85; }
    .barra { fill: var(--serie); }
    .base { stroke: var(--grade); stroke-width: 1; }
    .rotulo { text-anchor: end; dominant-baseline: middle; fill: var(--texto); }
    .rotulo.alerta { fill: var(--critico); font-weight: 500; }
    .valor { dominant-baseline: middle; fill: var(--texto); }
    .sem-dado { dominant-baseline: middle; fill: var(--texto-2); font-style: italic; }
    .ref { stroke: var(--texto-2); stroke-width: 1; stroke-dasharray: 4 3; }
    .ref-rotulo { text-anchor: middle; fill: var(--texto-2); font-size: 11px; }
    .dica {
      position: absolute; left: 160px; transform: translateY(-4px); z-index: 2; pointer-events: none;
      display: flex; flex-direction: column; gap: 1px; padding: 6px 8px; border-radius: 6px;
      background: #fff; box-shadow: 0 2px 8px rgba(0, 0, 0, .2); font-size: 12px; color: var(--texto-2);
      b { font-size: 14px; color: var(--texto); }
    }
  `,
})
export class BarrasComponent {
  readonly titulo = input.required<string>();
  readonly barras = input.required<Barra[]>();
  readonly unidade = input(' min');
  readonly referencia = input<{ valor: number; rotulo: string } | null>(null);

  protected readonly linha = LINHA;
  protected readonly largura = LARGURA;
  protected readonly x0 = ROTULO;
  protected readonly ativa = signal<number | null>(null);

  protected readonly altura = computed(() => this.barras().length * LINHA + 22);
  private readonly maximo = computed(() =>
    Math.max(1, this.referencia()?.valor ?? 0, ...this.barras().map((b) => b.valor ?? 0)),
  );

  protected escala(v: number): number {
    return (Math.max(0, v) / this.maximo()) * (LARGURA - ROTULO - VALOR);
  }

  /** Barra quadrada na linha de base e com ponta arredondada (4 px) no valor. */
  protected caminho(i: number, v: number): string {
    const w = this.escala(v);
    const y = i * LINHA + (LINHA - ESPESSURA) / 2;
    const r = Math.min(4, w / 2, ESPESSURA / 2);
    const x = this.x0;
    if (w <= 0) return '';
    return `M${x},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + ESPESSURA - r} ` +
      `Q${x + w},${y + ESPESSURA} ${x + w - r},${y + ESPESSURA} H${x} Z`;
  }
}
