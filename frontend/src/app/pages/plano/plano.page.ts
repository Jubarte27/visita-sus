import { DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { Component, computed, inject, input, numberAttribute, signal, viewChild } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';

import { Comparacao, MetodoComparado } from '../../core/models';
import { ROTULO_MOTIVO_NAO_ATENDIDA, ROTULO_MOTIVO_VISITA, selosDoPlano } from '../../core/plano-utils';
import { MicroareaService } from '../../core/services/microarea.service';
import { PlanoService } from '../../core/services/plano.service';
import { JornadaBarComponent } from '../../shared/jornada/jornada-bar.component';
import { MapComponent } from '../../shared/map/map.component';
import { corDoPeso, nomeCondicao } from '../../shared/map/map-utils';

/** Plano do ACS (Apêndice F, tela 2): rota no mapa, itinerário, não atendidas e conferência das regras. */
@Component({
  selector: 'app-plano-page',
  imports: [
    DatePipe, DecimalPipe, PercentPipe, RouterLink, MapComponent, JornadaBarComponent, MatButtonModule, MatIconModule,
    MatProgressBarModule, MatTabsModule, MatTooltipModule, FormsModule, MatFormFieldModule, MatInputModule,
  ],
  templateUrl: './plano.page.html',
  styleUrl: './plano.page.scss',
})
export class PlanoPage {
  readonly id = input.required({ transform: numberAttribute });
  private readonly planos = inject(PlanoService);
  private readonly microareas = inject(MicroareaService);
  private readonly mapa = viewChild(MapComponent);

  protected readonly plano = rxResource({ params: () => this.id(), stream: ({ params }) => this.planos.obter(params) });
  private readonly microareaId = computed(() => this.plano.value()?.microarea);
  protected readonly microarea = rxResource({
    params: () => this.microareaId(),
    stream: ({ params }) => this.microareas.obter(params),
  });
  protected readonly domicilios = rxResource({
    params: () => {
      const p = this.plano.value();
      return p ? { id: p.microarea, data: p.data } : undefined;
    },
    stream: ({ params }) => this.microareas.domicilios(params.id, params.data),
  });
  protected readonly malha = rxResource({
    params: () => this.microareaId(),
    stream: ({ params }) => this.microareas.malha(params),
  });

  protected readonly selos = computed(() => {
    const p = this.plano.value();
    return p ? selosDoPlano(p) : [];
  });
  protected readonly foraPorMotivo = computed(() => {
    const cont = new Map<string, number>();
    for (const n of this.plano.value()?.nao_atendidas ?? []) {
      const r = ROTULO_MOTIVO_NAO_ATENDIDA[n.motivo];
      cont.set(r, (cont.get(r) ?? 0) + 1);
    }
    return [...cont.entries()];
  });

  protected readonly motivoVisita = ROTULO_MOTIVO_VISITA;
  protected readonly motivoFora = ROTULO_MOTIVO_NAO_ATENDIDA;
  protected readonly cor = corDoPeso;
  protected readonly condicao = nomeCondicao;

  protected readonly comparacao = signal<Comparacao | null>(null);
  protected readonly comparando = signal(false);
  protected readonly erroComparacao = signal<string | null>(null);
  protected readonly rotaComparada = signal<MetodoComparado | null>(null);
  protected subN: number | null = null;
  protected tempoMilp = 20;

  protected comparar(): void {
    this.comparando.set(true);
    this.erroComparacao.set(null);
    this.rotaComparada.set(null);
    this.planos.comparar(this.id(), { tempo_milp: this.tempoMilp, n: this.subN || null }).subscribe({
      next: (c) => {
        this.comparacao.set(c);
        this.comparando.set(false);
      },
      error: (e) => {
        this.erroComparacao.set(e?.error?.detail ?? e.message);
        this.comparando.set(false);
      },
    });
  }

  protected mostrarRota(m: MetodoComparado): void {
    this.rotaComparada.set(this.rotaComparada() === m ? null : m);
  }

  protected csv(): string {
    return this.planos.csvUrl(this.id());
  }

  protected gpx(): string {
    return this.planos.gpxUrl(this.id());
  }

  protected abrir(chave: string): void {
    this.mapa()?.abrir(chave);
  }
}
