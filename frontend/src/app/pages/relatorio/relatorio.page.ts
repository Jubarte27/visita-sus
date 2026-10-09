import { DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { Component, ElementRef, computed, inject, input, numberAttribute, signal, viewChild } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';

import { MotivoNaoAtendida } from '../../core/models';
import { ROTULO_MOTIVO_NAO_ATENDIDA, ROTULO_SITUACAO } from '../../core/plano-utils';
import { SelecaoService } from '../../core/selecao.service';
import { EquipeService } from '../../core/services/equipe.service';
import { Barra, BarrasComponent } from '../../shared/barras/barras.component';
import { ComposicaoComponent, LinhaComposicao, SERIES_COMPOSICAO } from '../../shared/composicao/composicao.component';
import { EstadoComponent } from '../../shared/estado/estado.component';

/** "Microárea 02 · Bom Jesus" → "Microárea 02" (cabe na coluna de rótulos dos gráficos). */
export function rotuloCurto(rotulo: string): string {
  return rotulo.split(' · ')[0];
}

/** Relatório da equipe (Apêndice F, tela 3): demanda não atendida e sobrecarga por microárea, para a gestão. */
@Component({
  selector: 'app-relatorio-page',
  imports: [
    DatePipe, DecimalPipe, PercentPipe, RouterLink, BarrasComponent, ComposicaoComponent, EstadoComponent, MatButtonModule,
    MatIconModule, MatProgressBarModule,
  ],
  templateUrl: './relatorio.page.html',
  styleUrl: './relatorio.page.scss',
  host: { '(window:beforeprint)': 'prepararImpressao()' },
})
export class RelatorioPage {
  readonly id = input.required({ transform: numberAttribute });
  private readonly equipes = inject(EquipeService);
  protected readonly selecao = inject(SelecaoService);

  protected readonly relatorio = rxResource({
    params: () => ({ id: this.id(), data: this.selecao.data() }),
    stream: ({ params }) => this.equipes.relatorio(params.id, params.data),
  });

  protected readonly situacao = ROTULO_SITUACAO;
  protected readonly series = SERIES_COMPOSICAO;
  /** Microáreas com a linha de detalhes aberta. */
  protected readonly abertas = signal<ReadonlySet<number>>(new Set());
  private readonly comoCalculamos = viewChild<ElementRef<HTMLDetailsElement>>('comoCalculamos');

  protected readonly composicao = computed<LinhaComposicao[]>(() =>
    (this.relatorio.value()?.linhas ?? []).map((l) => ({
      rotulo: rotuloCurto(l.microarea.rotulo),
      valores: l.sem_plano ? null : [l.planejadas ?? 0, l.atrasados_fora ?? 0, l.em_dia_sem_visita ?? 0],
      alerta: l.alerta_sobrecarga,
    })),
  );

  protected readonly excesso = computed<Barra[]>(() =>
    (this.relatorio.value()?.linhas ?? []).map((l) => ({
      rotulo: rotuloCurto(l.microarea.rotulo),
      valor: l.sem_plano ? null : (l.excesso_min ?? 0),
      alerta: l.alerta_sobrecarga,
      detalhe: l.sem_plano ? undefined : `retorno às ${l.retorno}`,
    })),
  );

  protected readonly limiarExcesso = computed(() => {
    const r = this.relatorio.value();
    return r ? { valor: r.limiares.excesso_min, rotulo: `limiar ${r.limiares.excesso_min} min` } : null;
  });

  protected readonly csv = computed(() => this.equipes.relatorioCsvUrl(this.id(), this.selecao.data()));

  protected alternar(microarea: number): void {
    const s = new Set(this.abertas());
    if (!s.delete(microarea)) s.add(microarea);
    this.abertas.set(s);
  }

  protected imprimir(): void {
    window.print();
  }

  /** No papel não há como expandir: as definições ("Como calculamos") saem abertas. */
  protected prepararImpressao(): void {
    const d = this.comoCalculamos()?.nativeElement;
    if (d) d.open = true;
  }

  protected motivos(m: Partial<Record<MotivoNaoAtendida, number>> | undefined): string {
    return Object.entries(m ?? {})
      .map(([k, n]) => `${ROTULO_MOTIVO_NAO_ATENDIDA[k as MotivoNaoAtendida]}: ${n}`)
      .join(' · ');
  }
}
