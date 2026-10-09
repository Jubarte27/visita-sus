import { DatePipe, PercentPipe } from '@angular/common';
import { Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';

import { Equipe, LinhaRelatorio } from '../../core/models';
import { ROTULO_SITUACAO } from '../../core/plano-utils';
import { SelecaoService } from '../../core/selecao.service';
import { EquipeService } from '../../core/services/equipe.service';
import { SERIES_COMPOSICAO } from '../../shared/composicao/composicao.component';
import { EstadoComponent } from '../../shared/estado/estado.component';

/** Card de uma equipe na tela inicial: situação do dia em números e uma linha por microárea, com minibarra. */
@Component({
  selector: 'app-equipe-card',
  imports: [DatePipe, PercentPipe, MatButtonModule, MatCardModule, MatIconModule, MatTooltipModule, RouterLink],
  template: `
    @let e = equipe();
    @let r = relatorio.value();
    <mat-card appearance="outlined">
      <mat-card-header>
        <mat-card-title>{{ e.nome }}</mat-card-title>
        <mat-card-subtitle>{{ e.ubs.nome }} · {{ e.microareas.length }} ACS · {{ total() }} domicílios</mat-card-subtitle>
      </mat-card-header>
      <mat-card-content>
        @if (relatorio.isLoading()) {
          <p class="sub">carregando a situação do dia…</p>
        } @else if (r && r.total.com_plano === 0) {
          <p class="sem-plano"><mat-icon aria-hidden="true">event_busy</mat-icon>
            Sem plano para {{ data() | date: 'dd/MM' }}</p>
        } @else if (r) {
          <div class="kpis" [matTooltip]="r.resumo">
            <div [class.critico]="r.total.alertas > 0">
              <b>@if (r.total.alertas > 0) { <span class="ic">⚠</span> } @else { <span class="ic ok">✓</span> }{{ r.total.alertas }}<small>/{{ r.total.microareas }}</small></b>
              <span>em sobrecarga</span>
            </div>
            <div><b>{{ r.total.planejadas }}</b><span>visitas no dia</span></div>
            <div><b>{{ r.total.cobertura_atrasados === null ? '—' : (r.total.cobertura_atrasados | percent: '1.0-0') }}</b>
              <span>dos atrasados visitados</span></div>
          </div>
        }
        <ul class="microareas">
          @for (m of e.microareas; track m.id) {
            @let l = linha(m.id);
            <li>
              @if (l) {
                <span class="situacao" [attr.data-s]="l.situacao" [matTooltip]="situacao[l.situacao].rotulo + ': ' + l.resumo_situacao"
                  [attr.aria-label]="situacao[l.situacao].rotulo"><span class="ic">{{ situacao[l.situacao].icone }}</span></span>
              }
              <a [routerLink]="['/microareas', m.id]" class="nome">{{ curto(m.rotulo) }}<small>{{ m.agente?.nome }}</small></a>
              @if (l && !l.sem_plano) {
                <span class="mini-barra" role="img" [attr.aria-label]="descricaoBarra(l)" [matTooltip]="descricaoBarra(l)">
                  @for (seg of segmentos(l); track $index) {
                    <i [style.flex-grow]="seg.valor" [style.background]="seg.cor"></i>
                  }
                </span>
              }
            </li>
          }
        </ul>
        @if (r && r.total.com_plano > 0) {
          <p class="legenda">@for (s of series; track s.rotulo) { <span><i [style.background]="s.cor"></i>{{ s.rotulo }}</span> }</p>
        }
      </mat-card-content>
      <mat-card-actions>
        <a mat-flat-button [routerLink]="['/equipes', e.id]">
          <mat-icon>{{ r && r.total.com_plano === 0 ? 'route' : 'dashboard' }}</mat-icon>
          {{ r && r.total.com_plano === 0 ? 'Planejar o dia' : 'Abrir painel' }}</a>
        <a mat-button [routerLink]="['/equipes', e.id, 'relatorio']"><mat-icon>insights</mat-icon> Relatório</a>
      </mat-card-actions>
    </mat-card>
  `,
  styles: `
    mat-card { height: 100%; }
    mat-card-content { padding-top: var(--esp-3); }
    .sub { color: var(--mat-sys-on-surface-variant); font-size: 13px; }
    .sem-plano { display: flex; align-items: center; gap: var(--esp-2); margin: 0 0 var(--esp-3);
      color: var(--mat-sys-on-surface-variant); }
    .kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--esp-2); margin-bottom: var(--esp-4); }
    .kpis > div { display: flex; flex-direction: column; gap: 2px; padding: var(--esp-3); border-radius: 10px;
      background: var(--mat-sys-surface-container); }
    .kpis > div.critico { background: var(--vs-critico-fundo); }
    .kpis b { font-size: 26px; font-weight: 500; line-height: 1.1; }
    .kpis small { font-size: 14px; font-weight: 400; color: var(--mat-sys-on-surface-variant); }
    .kpis span { font-size: 11px; line-height: 1.3; color: var(--mat-sys-on-surface-variant); }
    .kpis .ic { font-size: 20px; margin-right: 4px; color: var(--vs-critico); }
    .kpis .ic.ok { color: var(--vs-bom); }
    .microareas { list-style: none; margin: 0; padding: 0; }
    .microareas li { display: grid; grid-template-columns: 28px 1fr 110px; align-items: center; gap: var(--esp-2);
      padding: var(--esp-2) 0; border-top: 1px solid var(--mat-sys-outline-variant); }
    .situacao { padding: 1px 6px; justify-content: center; }
    .nome { display: flex; flex-direction: column; line-height: 1.25; font-size: 13px; }
    .nome small { font-weight: 400; font-size: 11px; color: var(--mat-sys-on-surface-variant); }
    .mini-barra { display: flex; gap: 2px; height: 10px; }
    .mini-barra i { min-width: 2px; border-radius: 2px; }
    .legenda { display: flex; flex-wrap: wrap; gap: 2px var(--esp-3); margin: var(--esp-2) 0 0; font-size: 11px;
      color: var(--mat-sys-on-surface-variant); }
    .legenda i { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; }
    mat-card-actions { gap: var(--esp-2); padding: var(--esp-3) var(--esp-4) var(--esp-4); }
  `,
})
export class EquipeCardComponent {
  readonly equipe = input.required<Equipe>();
  readonly data = input.required<string>();
  private readonly service = inject(EquipeService);
  protected readonly situacao = ROTULO_SITUACAO;
  protected readonly series = SERIES_COMPOSICAO;

  protected readonly relatorio = rxResource({
    params: () => ({ id: this.equipe().id, data: this.data() }),
    stream: ({ params }) => this.service.relatorio(params.id, params.data),
  });

  private readonly porMicroarea = computed(
    () => new Map<number, LinhaRelatorio>((this.relatorio.value()?.linhas ?? []).map((l) => [l.microarea.id, l])),
  );

  protected linha(microarea: number): LinhaRelatorio | undefined {
    return this.porMicroarea().get(microarea);
  }

  protected total(): number {
    return this.equipe().microareas.reduce((s, m) => s + m.n_domicilios, 0);
  }

  protected curto(rotulo: string): string {
    return rotulo.split(' · ')[0];
  }

  protected segmentos(l: LinhaRelatorio) {
    const valores = [l.planejadas ?? 0, l.atrasados_fora ?? 0, l.em_dia_sem_visita ?? 0];
    return valores.map((valor, k) => ({ valor, cor: SERIES_COMPOSICAO[k].cor })).filter((s) => s.valor > 0);
  }

  protected descricaoBarra(l: LinhaRelatorio): string {
    return `${l.planejadas} visitados · ${l.atrasados_fora} atrasados sem visita · ${l.em_dia_sem_visita} em dia sem visita`;
  }
}

/** Tela inicial: as equipes cadastradas, cada uma com a situação do dia escolhido. */
@Component({
  selector: 'app-inicio-page',
  imports: [DatePipe, EquipeCardComponent, EstadoComponent, MatButtonModule, MatIconModule, MatProgressBarModule],
  template: `
    <div class="pagina">
      <header>
        <h1>Equipes</h1>
        <p class="sub">Situação de {{ selecao.data() | date: 'dd/MM/yyyy' }} · troque a data na barra superior</p>
      </header>
      @if (equipes.isLoading()) { <mat-progress-bar mode="indeterminate" /> }
      @if (equipes.error()) {
        <app-estado tipo="erro" icone="cloud_off" titulo="Não foi possível falar com o backend"
          texto="Confira se o servidor está no ar: na pasta backend, rode .venv/bin/python manage.py runserver (API em http://localhost:8000).">
          <button mat-stroked-button (click)="equipes.reload()"><mat-icon>refresh</mat-icon> Tentar de novo</button>
        </app-estado>
      }
      <div class="cards">
        @for (e of equipes.value() ?? []; track e.id) {
          <app-equipe-card [equipe]="e" [data]="selecao.data()" />
        }
      </div>
      @if (equipes.hasValue() && !equipes.value().length) {
        <app-estado icone="group_add" titulo="Nenhuma equipe cadastrada"
          texto="Importe uma instância do gerador: na pasta backend, rode .venv/bin/python manage.py importar_instancia data/instances/bomjesus" />
      }
    </div>
  `,
  styles: `
    .pagina { max-width: 1200px; margin: 0 auto; padding: var(--esp-5) var(--esp-6); }
    header h1 { margin: 0; }
    .sub { color: var(--mat-sys-on-surface-variant); margin: var(--esp-1) 0 var(--esp-5); }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: var(--esp-5); }
    @media (max-width: 600px) {
      .pagina { padding: var(--esp-4); }
      .cards { grid-template-columns: 1fr; }
    }
  `,
})
export class InicioPage {
  private readonly service = inject(EquipeService);
  protected readonly selecao = inject(SelecaoService);
  protected readonly equipes = rxResource({ stream: () => this.service.listar() });
}
