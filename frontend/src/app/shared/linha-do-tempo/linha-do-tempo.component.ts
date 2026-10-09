import { Component, computed, input, output, signal } from '@angular/core';

import { ItemRoteiro } from '../../core/models';
import { relogio, rotuloRisco } from '../../core/plano-utils';
import { corDoPeso, nomeCondicao } from '../map/map-utils';

export type TipoBloco = 'visita' | 'caminhada' | 'espera';

export interface Bloco {
  tipo: TipoBloco;
  inicio: number; // min desde o início da jornada
  fim: number;
  ordem?: number;
  cor?: string;
  descricao: string;
}

/** "HH:MM" → minutos desde `horaInicio` ("HH:MM:SS"), no mesmo dia. */
export function minutosDesde(horaInicio: string, hhmm: string): number {
  const [h0, m0] = horaInicio.split(':').map(Number);
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m - (h0 * 60 + m0);
}

/** Blocos do dia: caminhada até cada parada, espera (janela ainda fechada), visita e caminhada de volta. */
export function blocosDoDia(itens: ItemRoteiro[], horaInicio: string, H: number): Bloco[] {
  const blocos: Bloco[] = [];
  let relogioAtual = 0;
  for (const i of itens) {
    const chegada = minutosDesde(horaInicio, i.chegada);
    const inicio = minutosDesde(horaInicio, i.inicio);
    const fim = minutosDesde(horaInicio, i.fim);
    if (chegada > relogioAtual) {
      blocos.push({ tipo: 'caminhada', inicio: relogioAtual, fim: chegada,
        descricao: `caminhada até a ${i.ordem}ª visita · ${i.caminhada_min.toFixed(0)} min` });
    }
    if (inicio > chegada) {
      blocos.push({ tipo: 'espera', inicio: chegada, fim: inicio,
        descricao: `espera até ${i.inicio} (o domicílio só recebe a partir desse horário)` });
    }
    blocos.push({ tipo: 'visita', inicio, fim, ordem: i.ordem, cor: corDoPeso(i.w),
      descricao: `${i.ordem}ª visita · ${nomeCondicao(i.condicao)} · ${rotuloRisco(i.w)} · ${i.inicio}–${i.fim}` });
    relogioAtual = Math.max(relogioAtual, fim);
  }
  if (H > relogioAtual) {
    blocos.push({ tipo: 'caminhada', inicio: relogioAtual, fim: H,
      descricao: `volta à UBS · ${(H - relogioAtual).toFixed(0)} min` });
  }
  return blocos;
}

/**
 * Linha do tempo do dia do ACS: da saída da UBS ao retorno, com cada visita (cor = risco, como no mapa),
 * caminhadas e esperas, a marca da jornada nominal T e a faixa de hora extra. Emite `destacar` com a ordem da
 * visita sob o ponteiro, para a página destacar a parada no mapa.
 */
@Component({
  selector: 'app-linha-do-tempo',
  template: `
    <div class="trilho" role="img" [attr.aria-label]="resumo()">
      @if (H() - T() >= 1) {
        <div class="extra" [style.left.%]="pct(T())" [style.width.%]="pct(H()) - pct(T())" title="hora extra"></div>
      }
      @for (b of blocos(); track $index) {
        <div class="bloco" [attr.data-tipo]="b.tipo" [style.left.%]="pct(b.inicio)"
             [style.width.%]="pct(b.fim) - pct(b.inicio)" [style.background]="b.cor ?? null"
             (pointerenter)="entrar($index)" (pointerleave)="sair()" (focus)="entrar($index)" (blur)="sair()"
             [attr.tabindex]="b.tipo === 'visita' ? 0 : null" [attr.aria-label]="b.descricao">
          @if (b.tipo === 'visita' && pct(b.fim) - pct(b.inicio) >= 3.5) { <span>{{ b.ordem }}</span> }
        </div>
      }
      <div class="marca" [style.left.%]="pct(T())" title="fim da jornada nominal"></div>
    </div>
    <div class="eixo">
      @for (h of horas(); track h.min) {
        <span [style.left.%]="pct(h.min)">{{ h.rotulo }}</span>
      }
    </div>
    @if (ativo(); as a) {
      <div class="dica" [style.left.%]="posicaoDica(a)">{{ a.descricao }}</div>
    }
    <div class="legenda">
      <span><i class="v"></i>visita (cor = risco)</span>
      <span><i class="c"></i>caminhada</span>
      <span><i class="e"></i>espera</span>
      <span><i class="t"></i>fim da jornada {{ hora(T()) }}</span>
      @if (H() - T() >= 1) { <span><i class="x"></i>hora extra até {{ hora(H()) }}</span> }
    </div>
  `,
  styles: `
    :host { display: block; position: relative; margin: 0; }
    .trilho { position: relative; height: 26px; border-radius: 6px; background: var(--mat-sys-surface-container); }
    .extra { position: absolute; top: 0; bottom: 0; background: var(--vs-aviso-fundo); }
    .bloco { position: absolute; top: 3px; bottom: 3px; box-sizing: border-box; outline: none; }
    .bloco[data-tipo='visita'] {
      border-radius: 3px; border: 1px solid rgba(0, 0, 0, .35);
      display: flex; align-items: center; justify-content: center;
      font: 600 10px Roboto, sans-serif; color: var(--vs-texto);
      &:hover, &:focus-visible { box-shadow: 0 0 0 2px var(--vs-texto); z-index: 1; }
    }
    .bloco[data-tipo='caminhada'] {
      top: 11px; bottom: 11px;
      background: repeating-linear-gradient(90deg, var(--vs-texto-2) 0 3px, transparent 3px 6px);
    }
    .bloco[data-tipo='espera'] { top: 9px; bottom: 9px; border: 1px dashed var(--vs-texto-2); }
    .marca { position: absolute; top: -3px; bottom: -3px; width: 2px; background: var(--vs-texto); }
    .eixo { position: relative; height: 18px; font-size: 10px; color: var(--vs-texto-2);
      span { position: absolute; transform: translateX(-50%); top: 1px; white-space: nowrap; } }
    .dica {
      position: absolute; top: -30px; transform: translateX(-50%); z-index: 3; pointer-events: none;
      max-width: 300px; padding: 4px 8px; border-radius: 6px; white-space: nowrap;
      background: #fff; box-shadow: 0 2px 8px rgba(0, 0, 0, .2); font-size: 12px; color: var(--vs-texto);
    }
    .legenda { display: flex; flex-wrap: wrap; gap: var(--esp-1) var(--esp-4); margin-top: var(--esp-2); font-size: 11px;
      color: var(--vs-texto-2); }
    .legenda i { display: inline-block; width: 14px; height: 8px; margin-right: 4px; vertical-align: 0; }
    .legenda .v { background: linear-gradient(90deg, #4daf4a, #ffcc00, #ff7f00, #e41a1c); border-radius: 2px; }
    .legenda .c { height: 2px; vertical-align: 3px;
      background: repeating-linear-gradient(90deg, var(--vs-texto-2) 0 3px, transparent 3px 6px); }
    .legenda .e { height: 6px; border: 1px dashed var(--vs-texto-2); box-sizing: border-box; }
    .legenda .t { width: 2px; height: 10px; background: var(--vs-texto); vertical-align: -1px; }
    .legenda .x { background: var(--vs-aviso-fundo); border: 1px solid var(--vs-aviso); box-sizing: border-box; }
  `,
})
export class LinhaDoTempoComponent {
  readonly itens = input.required<ItemRoteiro[]>();
  readonly H = input.required<number>();
  readonly T = input.required<number>();
  readonly Tmax = input.required<number>();
  readonly horaInicio = input('08:00:00');
  /** Ordem da visita sob o ponteiro (null ao sair). */
  readonly destacar = output<number | null>();

  protected readonly blocos = computed(() => blocosDoDia(this.itens(), this.horaInicio(), this.H()));
  private readonly escala = computed(() => Math.max(this.Tmax(), this.H(), 1));
  protected readonly ativoIdx = signal<number | null>(null);
  protected readonly ativo = computed(() => {
    const i = this.ativoIdx();
    return i === null ? null : this.blocos()[i];
  });

  protected readonly horas = computed(() => {
    const [h0, m0] = this.horaInicio().split(':').map(Number);
    const inicio = h0 * 60 + m0;
    const out = [];
    for (let t = Math.ceil(inicio / 60) * 60; t - inicio <= this.escala(); t += 60) {
      out.push({ min: t - inicio, rotulo: `${String(Math.floor(t / 60) % 24).padStart(2, '0')}h` });
    }
    return out;
  });

  protected readonly resumo = computed(
    () => `linha do tempo: ${this.itens().length} visitas, retorno às ${this.hora(this.H())}`,
  );

  protected pct(min: number): number {
    return (100 * Math.max(0, min)) / this.escala();
  }

  /** Centro do bloco, sem deixar a dica sair pelas bordas. */
  protected posicaoDica(b: Bloco): number {
    return Math.min(78, Math.max(22, this.pct((b.inicio + b.fim) / 2)));
  }

  protected hora(min: number): string {
    return relogio(this.horaInicio(), min);
  }

  protected entrar(i: number): void {
    this.ativoIdx.set(i);
    const b = this.blocos()[i];
    this.destacar.emit(b.tipo === 'visita' ? (b.ordem ?? null) : null);
  }

  protected sair(): void {
    this.ativoIdx.set(null);
    this.destacar.emit(null);
  }
}
