import { DatePipe, DecimalPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, input, numberAttribute, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';

import { LinhaRelatorio, Metodo, Params } from '../../core/models';
import { ROTULO_SITUACAO, ultimoPorMicroarea } from '../../core/plano-utils';
import { SelecaoService } from '../../core/selecao.service';
import { EquipeService } from '../../core/services/equipe.service';
import { PlanoService } from '../../core/services/plano.service';
import { EstadoComponent } from '../../shared/estado/estado.component';
import { JornadaBarComponent } from '../../shared/jornada/jornada-bar.component';

/**
 * Painel da equipe (Apêndice F, tela 1): planejar o dia de todos os ACS e ver o resultado de cada um.
 * "Planejar dia" dispara uma requisição por ACS (o backend as roda em paralelo, num pool de processos), e cada
 * card mostra o próprio progresso e se atualiza quando o plano dele fica pronto.
 */
@Component({
  selector: 'app-painel-equipe-page',
  imports: [
    DatePipe, DecimalPipe, FormsModule, RouterLink, EstadoComponent, JornadaBarComponent, MatButtonModule,
    MatButtonToggleModule, MatCardModule, MatExpansionModule, MatFormFieldModule, MatIconModule, MatInputModule,
    MatProgressBarModule, MatSnackBarModule, MatTooltipModule,
  ],
  templateUrl: './painel-equipe.page.html',
  styleUrl: './painel-equipe.page.scss',
})
export class PainelEquipePage {
  readonly id = input.required({ transform: numberAttribute });
  private readonly equipes = inject(EquipeService);
  private readonly planos = inject(PlanoService);
  private readonly snack = inject(MatSnackBar);
  protected readonly selecao = inject(SelecaoService);

  protected readonly metodo = signal<Metodo>('alns');
  // padrões calibrados (decisão D7 do roteiro): β = 30, γ = 20
  protected readonly params = { beta: 30, gamma: 20, sementes: 5, tempo: 5 };
  /** Agentes com planejamento em andamento. */
  protected readonly pendentes = signal<ReadonlySet<number>>(new Set());
  protected readonly planejando = computed(() => this.pendentes().size > 0);
  protected readonly situacao = ROTULO_SITUACAO;

  protected readonly equipe = rxResource({ params: () => this.id(), stream: ({ params }) => this.equipes.obter(params) });
  protected readonly planosDoDia = rxResource({
    params: () => ({ equipe: this.id(), data: this.selecao.data() }),
    stream: ({ params }) => this.planos.listar(params),
  });
  /** Relatório da data: situação e atrasados sem visita de cada microárea. */
  protected readonly relatorio = rxResource({
    params: () => ({ id: this.id(), data: this.selecao.data() }),
    stream: ({ params }) => this.equipes.relatorio(params.id, params.data),
  });
  protected readonly ultimo = computed(() => ultimoPorMicroarea(this.planosDoDia.value() ?? []));
  protected readonly linhas = computed(
    () => new Map<number, LinhaRelatorio>((this.relatorio.value()?.linhas ?? []).map((l) => [l.microarea.id, l])),
  );
  protected readonly semPlanos = computed(
    () => this.planosDoDia.hasValue() && (this.planosDoDia.value() ?? []).length === 0 && !this.planejando(),
  );

  protected planejarEquipe(): void {
    const agentes = (this.equipe.value()?.microareas ?? []).flatMap((m) => (m.agente ? [m.agente.id] : []));
    this.planejarVarios(agentes);
  }

  protected planejarAgente(agente: number): void {
    this.planejarVarios([agente]);
  }

  protected pendente(agente: number | undefined): boolean {
    return agente !== undefined && this.pendentes().has(agente);
  }

  protected tempoEstimado(): string {
    return this.metodo() === 'guloso' ? 'menos de 1 s' : `até ~${this.params.sementes * this.params.tempo} s`;
  }

  private planejarVarios(agentes: number[]): void {
    if (!agentes.length) return;
    this.pendentes.set(new Set([...this.pendentes(), ...agentes]));
    let ok = 0;
    let falhas = 0;
    const terminar = (agente: number) => {
      const s = new Set(this.pendentes());
      s.delete(agente);
      this.pendentes.set(s);
      this.planosDoDia.reload();
      this.relatorio.reload();
      if (ok + falhas === agentes.length) {
        this.snack.open(falhas ? `${ok} plano(s) gerado(s), ${falhas} com erro` : `${ok} plano(s) gerado(s)`, 'ok',
          { duration: 3000 });
      }
    };
    for (const agente of agentes) {
      this.planos.planejar(agente, this.selecao.data(), this.metodo(), this.paramsApi()).subscribe({
        next: () => {
          ok += 1;
          terminar(agente);
        },
        error: (e: HttpErrorResponse) => {
          falhas += 1;
          terminar(agente);
          const detalhe = typeof e.error === 'object' && e.error ? JSON.stringify(e.error.detail ?? e.error) : e.message;
          this.snack.open(`Erro ao planejar: ${detalhe}`, 'fechar');
        },
      });
    }
  }

  private paramsApi(): Params {
    const base: Params = { beta: this.params.beta, gamma: this.params.gamma };
    if (this.metodo() === 'alns') {
      base.seeds = Array.from({ length: this.params.sementes }, (_, i) => i);
      base.time_limit_s = this.params.tempo;
    }
    return base;
  }
}
