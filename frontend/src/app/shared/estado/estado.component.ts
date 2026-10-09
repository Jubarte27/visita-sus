import { Component, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

/**
 * Estado vazio ou de erro: ícone, título, explicação e, no conteúdo projetado, a ação que resolve
 * (ex.: "Nenhum plano para 08/10" + botão "Planejar agora").
 */
@Component({
  selector: 'app-estado',
  imports: [MatIconModule],
  template: `
    <div class="estado" [attr.data-tipo]="tipo()" [attr.role]="tipo() === 'erro' ? 'alert' : null">
      <mat-icon aria-hidden="true">{{ icone() }}</mat-icon>
      <div class="texto">
        <b>{{ titulo() }}</b>
        @if (texto()) { <p>{{ texto() }}</p> }
        <div class="acoes"><ng-content /></div>
      </div>
    </div>
  `,
  styles: `
    .estado {
      display: flex; gap: var(--esp-3); align-items: flex-start; margin: var(--esp-5) 0; padding: var(--esp-4) var(--esp-5);
      border-radius: 12px;
      background: var(--mat-sys-surface-container); max-width: 760px;
    }
    .estado[data-tipo='erro'] { background: var(--vs-critico-fundo); mat-icon { color: var(--vs-critico); } }
    mat-icon { flex: none; color: var(--mat-sys-primary); }
    b { font-weight: 500; }
    p { margin: var(--esp-1) 0 0; color: var(--mat-sys-on-surface-variant); font-size: 13px; line-height: 1.5; }
    .acoes { display: flex; flex-wrap: wrap; gap: var(--esp-2); margin-top: var(--esp-3); }
    .acoes:empty { display: none; }
  `,
})
export class EstadoComponent {
  readonly titulo = input.required<string>();
  readonly texto = input('');
  readonly icone = input('info');
  readonly tipo = input<'vazio' | 'erro'>('vazio');
}
