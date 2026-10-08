import { Component, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatCardModule } from '@angular/material/card';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';

import { EquipeService } from '../../core/services/equipe.service';

/** Lista das equipes cadastradas, com as microáreas de cada uma. */
@Component({
  selector: 'app-inicio-page',
  imports: [MatCardModule, MatProgressBarModule, RouterLink],
  template: `
    <div class="pagina">
      <h1>Equipes</h1>
      @if (equipes.isLoading()) { <mat-progress-bar mode="indeterminate" /> }
      @if (equipes.error()) { <p class="erro">Não foi possível falar com o backend (http://localhost:8000).</p> }
      @for (e of equipes.value() ?? []; track e.id) {
        <mat-card appearance="outlined">
          <mat-card-header>
            <mat-card-title><a [routerLink]="['/equipes', e.id]">{{ e.nome }}</a></mat-card-title>
            <mat-card-subtitle>{{ e.ubs.nome }} · {{ e.microareas.length }} microárea(s)</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <ul>
              @for (m of e.microareas; track m.id) {
                <li><a [routerLink]="['/microareas', m.id]">{{ m.nome }}</a> · {{ m.agente?.nome }} ·
                  {{ m.n_domicilios }} domicílios</li>
              }
            </ul>
          </mat-card-content>
        </mat-card>
      } @empty {
        @if (equipes.hasValue()) {
          <p>Nenhuma equipe. Importe uma instância: <code>manage.py importar_instancia data/instances/bomjesus</code></p>
        }
      }
    </div>
  `,
  styles: `
    .pagina { max-width: 900px; margin: 0 auto; padding: 16px; }
    mat-card { margin-bottom: 12px; }
    .erro { color: var(--mat-sys-error); }
  `,
})
export class InicioPage {
  private readonly service = inject(EquipeService);
  protected readonly equipes = rxResource({ stream: () => this.service.listar() });
}
