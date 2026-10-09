import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';

import { ComposicaoComponent } from './composicao.component';

const SERIES = [
  { rotulo: 'visitados', cor: '#2a78d6', tinta: '#ffffff' },
  { rotulo: 'atrasados sem visita', cor: '#eb6834', tinta: '#0b0b0b' },
  { rotulo: 'em dia', cor: '#1baf7a', tinta: '#0b0b0b' },
];

describe('ComposicaoComponent', () => {
  it('empilha as séries em 100%, com legenda, % no segmento, alerta e "sem plano"', async () => {
    const f = TestBed.createComponent(ComposicaoComponent);
    f.componentRef.setInput('titulo', 'Domicílios');
    f.componentRef.setInput('series', SERIES);
    f.componentRef.setInput('linhas', [
      { rotulo: 'a', valores: [25, 25, 50] },
      { rotulo: 'b', valores: [10, 0, 0], alerta: true },
      { rotulo: 'c', valores: null },
    ]);
    await f.whenStable();
    const el: HTMLElement = f.nativeElement;
    expect([...el.querySelectorAll('.legenda li')].map((li) => li.textContent?.trim())).toEqual(
      SERIES.map((s) => s.rotulo),
    );
    // a: três segmentos; b: só o de valor > 0; c: sem dado
    expect(el.querySelectorAll('g.segmento')).toHaveLength(4);
    expect([...el.querySelectorAll('text.pct')].map((t) => t.textContent?.trim())).toEqual(['25%', '25%', '50%', '100%']);
    expect(el.querySelector('text.rotulo.alerta')?.textContent).toContain('⚠');
    expect(el.querySelector('text.sem-dado')?.textContent).toContain('sem plano');
    // larguras proporcionais (o vão de 2 px entre segmentos sai dos segmentos internos)
    const larguras = [...el.querySelectorAll('g.segmento path')].slice(0, 3).map((p) => {
      const [, x0, x1] = /M([\d.]+),[\d.]+ H([\d.]+)/.exec(p.getAttribute('d')!)!.map(Number);
      return x1 - x0;
    });
    expect((larguras[0] + 2) / (larguras[2] + 4)).toBeCloseTo(0.5, 1);
  });

  it('mostra quantidade e % no tooltip do segmento', async () => {
    const f = TestBed.createComponent(ComposicaoComponent);
    f.componentRef.setInput('titulo', 'Domicílios');
    f.componentRef.setInput('series', SERIES);
    f.componentRef.setInput('linhas', [{ rotulo: 'a', valores: [30, 10, 60] }]);
    await f.whenStable();
    const el: HTMLElement = f.nativeElement;
    el.querySelectorAll('g.segmento')[1].dispatchEvent(new Event('pointerenter'));
    await f.whenStable();
    const dica = el.querySelector('.dica')!;
    expect(dica.textContent).toContain('10');
    expect(dica.textContent).toContain('10%');
    expect(dica.textContent).toContain('atrasados sem visita');
  });
});
