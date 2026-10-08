import { DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { Component, computed, inject, input, numberAttribute } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';

import { MotivoNaoAtendida } from '../../core/models';
import { ROTULO_MOTIVO_NAO_ATENDIDA } from '../../core/plano-utils';
import { SelecaoService } from '../../core/selecao.service';
import { EquipeService } from '../../core/services/equipe.service';
import { Barra, BarrasComponent } from '../../shared/barras/barras.component';

/** Relatório da equipe (Apêndice F, tela 3): demanda não atendida e sobrecarga por microárea, para a gestão. */
@Component({
  selector: 'app-relatorio-page',
  imports: [
    DatePipe, DecimalPipe, PercentPipe, RouterLink, BarrasComponent, MatButtonModule, MatIconModule,
    MatProgressBarModule,
  ],
  templateUrl: './relatorio.page.html',
  styleUrl: './relatorio.page.scss',
})
export class RelatorioPage {
  readonly id = input.required({ transform: numberAttribute });
  private readonly equipes = inject(EquipeService);
  protected readonly selecao = inject(SelecaoService);

  protected readonly relatorio = rxResource({
    params: () => ({ id: this.id(), data: this.selecao.data() }),
    stream: ({ params }) => this.equipes.relatorio(params.id, params.data),
  });

  protected readonly penalidade = computed<Barra[]>(() =>
    (this.relatorio.value()?.linhas ?? []).map((l) => ({
      rotulo: l.microarea.nome,
      valor: l.sem_plano ? null : (l.penalidade_residual_min ?? 0),
      alerta: l.alerta_sobrecarga,
      detalhe: l.sem_plano ? undefined : `${l.nao_atendidas} candidata(s) não atendida(s)`,
    })),
  );

  protected readonly excesso = computed<Barra[]>(() =>
    (this.relatorio.value()?.linhas ?? []).map((l) => ({
      rotulo: l.microarea.nome,
      valor: l.sem_plano ? null : (l.excesso_min ?? 0),
      alerta: l.alerta_sobrecarga,
      detalhe: l.sem_plano ? undefined : `retorno às ${l.retorno}`,
    })),
  );

  protected readonly limiarExcesso = computed(() => {
    const r = this.relatorio.value();
    return r ? { valor: r.limiares.excesso_min, rotulo: `limiar ${r.limiares.excesso_min} min` } : null;
  });

  protected motivos(m: Partial<Record<MotivoNaoAtendida, number>> | undefined): string {
    return Object.entries(m ?? {})
      .map(([k, n]) => `${ROTULO_MOTIVO_NAO_ATENDIDA[k as MotivoNaoAtendida]}: ${n}`)
      .join(' · ');
  }
}
