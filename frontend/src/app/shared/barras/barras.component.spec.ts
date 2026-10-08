import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';

import { BarrasComponent } from './barras.component';

describe('BarrasComponent', () => {
  it('desenha uma barra por categoria, valor na ponta, alerta com ícone e "sem plano"', async () => {
    const f = TestBed.createComponent(BarrasComponent);
    f.componentRef.setInput('titulo', 'Excesso');
    f.componentRef.setInput('barras', [
      { rotulo: 'a', valor: 10 },
      { rotulo: 'b', valor: 40, alerta: true },
      { rotulo: 'c', valor: null },
    ]);
    f.componentRef.setInput('referencia', { valor: 30, rotulo: 'limiar 30 min' });
    await f.whenStable();
    const el: HTMLElement = f.nativeElement;
    expect(el.querySelectorAll('path.barra')).toHaveLength(2);
    expect([...el.querySelectorAll('text.valor')].map((t) => t.textContent?.trim())).toEqual(['10 min', '40 min']);
    expect(el.querySelector('text.rotulo.alerta')?.textContent).toContain('⚠');
    expect(el.querySelector('text.sem-dado')?.textContent).toContain('sem plano');
    expect(el.querySelector('text.ref-rotulo')?.textContent).toContain('limiar 30 min');
    // a maior barra (40) ocupa toda a escala; a de 10, um quarto
    const largura = (d: string) => Number(/H([\d.]+)/.exec(d)![1]);
    const [p10, p40] = [...el.querySelectorAll('path.barra')].map((p) => largura(p.getAttribute('d')!));
    expect((p10 - 150) / (p40 - 150)).toBeCloseTo(0.25, 1);
  });
});
