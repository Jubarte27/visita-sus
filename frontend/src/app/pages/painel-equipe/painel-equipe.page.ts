import { DatePipe, DecimalPipe } from '@angular/common';
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
import { RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { Metodo, Params } from '../../core/models';
import { ultimoPorMicroarea } from '../../core/plano-utils';
import { SelecaoService } from '../../core/selecao.service';
import { EquipeService } from '../../core/services/equipe.service';
import { PlanoService } from '../../core/services/plano.service';
import { JornadaBarComponent } from '../../shared/jornada/jornada-bar.component';

/** Painel da equipe (Apêndice F, tela 1): planejar o dia de todos os ACS e ver o resultado de cada um. */
@Component({
  selector: 'app-painel-equipe-page',
  imports: [
    DatePipe, DecimalPipe, FormsModule, RouterLink, JornadaBarComponent, MatButtonModule, MatButtonToggleModule,
    MatCardModule, MatExpansionModule, MatFormFieldModule, MatIconModule, MatInputModule, MatProgressBarModule,
    MatSnackBarModule,
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
  protected readonly params = { beta: 30, gamma: 2, sementes: 5, tempo: 5 };
  protected readonly planejando = signal<string | null>(null); // null ou o que está sendo planejado

  protected readonly equipe = rxResource({ params: () => this.id(), stream: ({ params }) => this.equipes.obter(params) });
  protected readonly planosDoDia = rxResource({
    params: () => ({ equipe: this.id(), data: this.selecao.data() }),
    stream: ({ params }) => this.planos.listar(params),
  });
  protected readonly ultimo = computed(() => ultimoPorMicroarea(this.planosDoDia.value() ?? []));

  protected planejarEquipe(): void {
    this.planejando.set('equipe');
    this.equipes.planejar(this.id(), this.selecao.data(), this.metodo(), this.paramsApi()).subscribe({
      next: (r) => this.concluir(`${r.planos.length} plano(s) gerado(s)`),
      error: (e) => this.falhar(e),
    });
  }

  protected planejarAgente(agente: number): void {
    this.planejando.set(`agente-${agente}`);
    this.planos.planejar(agente, this.selecao.data(), this.metodo(), this.paramsApi()).subscribe({
      next: () => this.concluir('plano gerado'),
      error: (e) => this.falhar(e),
    });
  }

  protected tempoEstimado(): string {
    return this.metodo() === 'guloso' ? 'menos de 1 s' : `até ~${this.params.sementes * this.params.tempo} s por ACS`;
  }

  private paramsApi(): Params {
    const base: Params = { beta: this.params.beta, gamma: this.params.gamma };
    if (this.metodo() === 'alns') {
      base.seeds = Array.from({ length: this.params.sementes }, (_, i) => i);
      base.time_limit_s = this.params.tempo;
    }
    return base;
  }

  private concluir(msg: string): void {
    this.planejando.set(null);
    this.planosDoDia.reload();
    this.snack.open(msg, 'ok', { duration: 3000 });
  }

  private falhar(e: HttpErrorResponse): void {
    this.planejando.set(null);
    const detalhe = typeof e.error === 'object' && e.error ? JSON.stringify(e.error.detail ?? e.error) : e.message;
    this.snack.open(`Erro ao planejar: ${detalhe}`, 'fechar');
  }
}
