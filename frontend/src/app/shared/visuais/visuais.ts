import { Component, computed, input } from '@angular/core';

import { intervaloVisual, rotuloRisco } from '../../core/plano-utils';
import { corDoPeso } from '../map/map-utils';

/**
 * Medidor de risco: 5 barrinhas crescentes, preenchidas até o peso clínico w, na cor do risco (a mesma do mapa).
 * O rótulo ("risco alto") fica no tooltip e para leitores de tela.
 */
@Component({
  selector: 'app-risco',
  template: `
    <span class="risco-medidor" role="img" [attr.aria-label]="rotulo()" [title]="rotulo()">
      @for (n of niveis; track n) {
        <i [style.background]="n <= nivel() ? cor() : null"></i>
      }
    </span>
  `,
})
export class RiscoComponent {
  readonly w = input.required<number>();
  protected readonly niveis = [1, 2, 3, 4, 5];
  protected readonly nivel = computed(() => Math.min(5, Math.max(1, Math.round(this.w()))));
  protected readonly cor = computed(() => corDoPeso(this.w()));
  protected readonly rotulo = computed(() => rotuloRisco(this.w()));
}

/**
 * Intervalo entre visitas: barra com os dias desde a última visita, marca no intervalo máximo (P) e rótulo curto
 * ("12/30 dias", "vence hoje" ou "+15 dias"). O texto completo fica no tooltip.
 */
@Component({
  selector: 'app-intervalo',
  template: `
    @let v = visual();
    <span class="intervalo" [attr.data-estado]="v.estado" [title]="v.completo" role="img" [attr.aria-label]="v.completo">
      <span class="trilho"><span class="cheio" [style.width.%]="v.pctCheio"></span>
        <span class="limite" [style.left.%]="v.pctLimite"></span></span>
      <span class="rotulo">{{ v.curto }}</span>
    </span>
  `,
})
export class IntervaloComponent {
  readonly dias = input.required<number>();
  readonly P = input.required<number>();
  protected readonly visual = computed(() => intervaloVisual(this.dias(), this.P()));
}
