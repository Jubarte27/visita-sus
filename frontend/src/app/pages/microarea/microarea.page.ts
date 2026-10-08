import { DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { Component, computed, inject, input, numberAttribute } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatCardModule } from '@angular/material/card';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';

import { SelecaoService } from '../../core/selecao.service';
import { MicroareaService } from '../../core/services/microarea.service';
import { MapComponent } from '../../shared/map/map.component';
import { CORES_W, corDoPeso, nomeCondicao } from '../../shared/map/map-utils';

/** Mapa da microárea com os domicílios e seus atributos na data escolhida. */
@Component({
  selector: 'app-microarea-page',
  imports: [MapComponent, MatCardModule, MatProgressBarModule, DatePipe, DecimalPipe, PercentPipe, RouterLink],
  templateUrl: './microarea.page.html',
  styleUrl: './microarea.page.scss',
})
export class MicroareaPage {
  readonly id = input.required({ transform: numberAttribute });
  private readonly service = inject(MicroareaService);
  protected readonly selecao = inject(SelecaoService);

  protected readonly microarea = rxResource({ params: () => this.id(), stream: ({ params }) => this.service.obter(params) });
  protected readonly domicilios = rxResource({
    params: () => ({ id: this.id(), data: this.selecao.data() }),
    stream: ({ params }) => this.service.domicilios(params.id, params.data),
  });
  protected readonly malha = rxResource({ params: () => this.id(), stream: ({ params }) => this.service.malha(params) });

  protected readonly resumo = computed(() => {
    const fc = this.domicilios.value();
    if (!fc) return null;
    const ps = fc.features.map((f) => f.properties);
    const porCondicao = new Map<string, { n: number; w: number }>();
    for (const p of ps) {
      const c = porCondicao.get(p.condicao) ?? { n: 0, w: p.w };
      c.n += 1;
      porCondicao.set(p.condicao, c);
    }
    return {
      total: ps.length,
      pontos: new Set(ps.map((p) => p.node)).size,
      atrasados: ps.filter((p) => p.atrasado).length,
      urgentes: ps.filter((p) => p.urgente).length,
      graves: ps.filter((p) => p.grave).length,
      condicoes: [...porCondicao.entries()]
        .map(([condicao, c]) => ({ nome: nomeCondicao(condicao), n: c.n, cor: corDoPeso(c.w), w: c.w }))
        .sort((a, b) => b.w - a.w || b.n - a.n),
    };
  });

  protected readonly cores = Object.entries(CORES_W);
}
