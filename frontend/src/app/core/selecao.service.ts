import { Injectable, signal } from '@angular/core';

/** Equipe e data escolhidas na barra superior, compartilhadas pelas telas. */
@Injectable({ providedIn: 'root' })
export class SelecaoService {
  readonly equipeId = signal<number | null>(lerNumero('visita-sus.equipe'));
  readonly data = signal<string>(hoje());

  escolherEquipe(id: number | null): void {
    this.equipeId.set(id);
    try {
      if (id === null) localStorage.removeItem('visita-sus.equipe');
      else localStorage.setItem('visita-sus.equipe', String(id));
    } catch {
      // armazenamento indisponível: a escolha vale só nesta aba
    }
  }
}

export function hoje(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function lerNumero(chave: string): number | null {
  try {
    const v = localStorage.getItem(chave);
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}
