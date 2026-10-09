import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';

import { IntervaloComponent, RiscoComponent } from './visuais';

describe('indicadores visuais', () => {
  it('medidor de risco preenche w barrinhas na cor do risco, com rótulo acessível', async () => {
    const f = TestBed.createComponent(RiscoComponent);
    f.componentRef.setInput('w', 3);
    await f.whenStable();
    const el: HTMLElement = f.nativeElement;
    const barras = [...el.querySelectorAll('i')];
    expect(barras).toHaveLength(5);
    expect(barras.filter((b) => b.style.background).length).toBe(3);
    expect(el.querySelector('.risco-medidor')?.getAttribute('aria-label')).toBe('risco alto');
  });

  it('intervalo marca o estado e mostra o rótulo curto', async () => {
    const f = TestBed.createComponent(IntervaloComponent);
    f.componentRef.setInput('dias', 45);
    f.componentRef.setInput('P', 30);
    await f.whenStable();
    const el: HTMLElement = f.nativeElement;
    expect(el.querySelector('.intervalo')?.getAttribute('data-estado')).toBe('atrasado');
    expect(el.querySelector('.rotulo')?.textContent?.trim()).toBe('+15 dias');
    expect((el.querySelector('.cheio') as HTMLElement).style.width).toBe('100%');
  });
});
