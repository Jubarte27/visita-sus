import { Component, effect, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatToolbarModule } from '@angular/material/toolbar';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { SelecaoService } from './core/selecao.service';
import { EquipeService } from './core/services/equipe.service';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly selecao = inject(SelecaoService);
  private readonly router = inject(Router);
  private readonly equipeService = inject(EquipeService);
  protected readonly equipes = rxResource({ stream: () => this.equipeService.listar() });

  constructor() {
    // a URL /equipes/:id manda na equipe selecionada
    this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe((e) => {
      const m = /^\/equipes\/(\d+)/.exec(e.urlAfterRedirects);
      if (m) this.selecao.escolherEquipe(Number(m[1]));
    });
    // sem escolha anterior, usa a primeira equipe
    effect(() => {
      const lista = this.equipes.value();
      if (lista?.length && !lista.some((e) => e.id === this.selecao.equipeId())) {
        this.selecao.escolherEquipe(lista[0].id);
      }
    });
  }

  protected escolherEquipe(id: number): void {
    this.selecao.escolherEquipe(id);
    this.router.navigate(['/equipes', id]);
  }

  protected escolherData(valor: string): void {
    if (valor) this.selecao.data.set(valor);
  }
}
