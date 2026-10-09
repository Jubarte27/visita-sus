import { Component, computed, input } from '@angular/core';

import { relogio } from '../../core/plano-utils';

/** Barra da jornada: tempo usado (H) contra a jornada nominal T e a máxima Tmax, com horários reais. */
@Component({
  selector: 'app-jornada-bar',
  template: `
    <div class="barra" [title]="'retorno à UBS às ' + fim()">
      <div class="usado" [class.excesso]="H() - T() >= 1" [style.width.%]="pct(H())"></div>
      <div class="marca" [style.left.%]="pct(T())" title="jornada nominal T"></div>
    </div>
    <div class="rotulos">
      <span>{{ inicio() }}</span>
      <span>retorno <b>{{ fim() }}</b> · T {{ relogio(T()) }} · Tmax {{ relogio(Tmax()) }}</span>
    </div>
  `,
  styles: `
    .barra { position: relative; height: 14px; border-radius: 7px; background: var(--mat-sys-surface-container-high); overflow: hidden; }
    .usado { height: 100%; background: var(--vs-serie); }
    .usado.excesso { background: linear-gradient(90deg, var(--vs-serie) 0, var(--vs-serie) var(--t, 85%),
      var(--vs-aviso) var(--t, 85%)); }
    .marca { position: absolute; top: 0; bottom: 0; width: 2px; background: var(--vs-texto); }
    .rotulos { display: flex; justify-content: space-between; font-size: 11px; margin-top: 2px;
      color: var(--mat-sys-on-surface-variant); }
    b { color: var(--mat-sys-on-surface); }
  `,
  host: { '[style.--t]': "pct(T()) / pct(H()) * 100 + '%'" },
})
export class JornadaBarComponent {
  readonly H = input.required<number>();
  readonly T = input.required<number>();
  readonly Tmax = input.required<number>();
  readonly horaInicio = input('08:00:00');

  protected readonly inicio = computed(() => this.relogio(0));
  protected readonly fim = computed(() => this.relogio(this.H()));

  protected pct(min: number): number {
    return Math.min(100, (100 * min) / this.Tmax());
  }

  protected relogio(min: number): string {
    return relogio(this.horaInicio(), min);
  }
}
