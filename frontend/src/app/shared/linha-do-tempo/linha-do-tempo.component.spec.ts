import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';

import { ItemRoteiro } from '../../core/models';
import { LinhaDoTempoComponent, blocosDoDia, minutosDesde } from './linha-do-tempo.component';

function item(ordem: number, chegada: string, inicio: string, fim: string, w = 2): ItemRoteiro {
  return {
    ordem, domicilio: ordem, codigo: ordem, lat: 0, lon: 0, condicao: 'idoso', motivo: 'rotina', w, urgente: false,
    grave: false, dias_sem_visita: 1, P: 30, chegada, inicio, fim, espera_min: 0, caminhada_min: 5, duracao_min: 15,
  };
}

describe('linha do tempo', () => {
  it('minutos desde o início da jornada', () => {
    expect(minutosDesde('08:00:00', '09:15')).toBe(75);
    expect(minutosDesde('07:30:00', '07:30')).toBe(0);
  });

  it('caminhada, espera, visita e volta à UBS, em ordem', () => {
    const blocos = blocosDoDia([item(1, '08:05', '08:05', '08:20'), item(2, '08:25', '08:40', '08:55')], '08:00:00', 65);
    expect(blocos.map((b) => [b.tipo, b.inicio, b.fim])).toEqual([
      ['caminhada', 0, 5], ['visita', 5, 20], ['caminhada', 20, 25], ['espera', 25, 40], ['visita', 40, 55],
      ['caminhada', 55, 65],
    ]);
    expect(blocos[1].descricao).toContain('1ª visita');
  });

  it('desenha um bloco por trecho, com a marca de T e a faixa de hora extra', async () => {
    const f = TestBed.createComponent(LinhaDoTempoComponent);
    f.componentRef.setInput('itens', [item(1, '08:05', '08:05', '08:50')]);
    f.componentRef.setInput('H', 60);
    f.componentRef.setInput('T', 50);
    f.componentRef.setInput('Tmax', 100);
    await f.whenStable();
    const el: HTMLElement = f.nativeElement;
    expect(el.querySelectorAll('.bloco[data-tipo="visita"]')).toHaveLength(1);
    expect(el.querySelector('.extra')).not.toBeNull();
    expect(el.querySelector('.legenda')?.textContent).toContain('hora extra até 09:00');
    expect([...el.querySelectorAll('.eixo span')].map((s) => s.textContent?.trim())).toEqual(['08h', '09h']);
  });
});
