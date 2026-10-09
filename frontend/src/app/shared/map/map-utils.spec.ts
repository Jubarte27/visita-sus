import type { Feature, Point } from 'geojson';
import { describe, expect, it } from 'vitest';

import { DomicilioProps } from '../../core/models';
import {
  agruparPorPonto, comprimentoM, corDoPeso, janelaHorario, nomeCondicao, popupDoPonto, raioDoPonto, setasDaRota,
} from './map-utils';

function dom(codigo: number, node: number, extra: Partial<DomicilioProps> = {}): Feature<Point, DomicilioProps> {
  return {
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [-51.15 + node * 1e-4, -30.04] },
    properties: {
      id: codigo, codigo, condicao: 'idoso', w: 2, P: 30, duracao_min: 15, ultima_visita: '2026-09-01',
      dias_sem_visita: 10, penalidade: 0.7, atrasado: false, atraso_dias: 0, urgente: false, grave: false,
      tw_inicio: 0, tw_fim: 420, n_moradores: 2, node, ...extra,
    },
  };
}

describe('map-utils', () => {
  it('cor pelo peso clínico, com limites', () => {
    expect(corDoPeso(1)).toBe('#4daf4a');
    expect(corDoPeso(5)).toBe('#7b0000');
    expect(corDoPeso(9)).toBe('#7b0000');
    expect(corDoPeso(0)).toBe('#4daf4a');
  });

  it('agrupa domicílios do mesmo ponto de acesso', () => {
    const grupos = agruparPorPonto([
      dom(1, 10),
      dom(2, 10, { w: 4, urgente: true, atrasado: true }),
      dom(3, 11),
    ]);
    expect(grupos).toHaveLength(2);
    const g = grupos.find((x) => x.node === 10)!;
    expect(g.domicilios.map((d) => d.codigo)).toEqual([1, 2]);
    expect(g.wMax).toBe(4);
    expect(g.urgente).toBe(true);
    expect(g.atrasados).toBe(1);
  });

  it('raio cresce com o nº de domicílios até 10', () => {
    expect(raioDoPonto(1)).toBe(5);
    expect(raioDoPonto(20)).toBe(raioDoPonto(10));
    expect(raioDoPonto(5)).toBeGreaterThan(raioDoPonto(2));
  });

  it('popup em cartões, mais prioritários primeiro, com texto escapado e horário real', () => {
    const [g] = agruparPorPonto([
      dom(1, 10, { penalidade: 0.2 }),
      dom(2, 10, { penalidade: 3.1, condicao: '<b>x</b>', tw_inicio: 180, tw_fim: 360, w: 3, dias_sem_visita: 45,
        atrasado: true, urgente: true }),
    ]);
    const html = popupDoPonto(g, '08:00:00');
    expect(html.indexOf('#2<')).toBeLessThan(html.indexOf('#1<'));
    expect(html).toContain('&lt;b&gt;x&lt;/b&gt;');
    expect(html).toContain('tarde (11:00–14:00)');
    expect(html).toContain('aria-label="risco alto"');
    expect(html).toContain('+15 dias');
    expect(html).toContain('data-estado="atrasado"');
    expect(html).toContain('urgente');
    expect(html).toContain('2 domicílio(s) neste ponto · 1 atrasado(s)');
    const muitos = agruparPorPonto(Array.from({ length: 11 }, (_, i) => dom(i + 1, 10)));
    expect(popupDoPonto(muitos[0])).toContain('+ 3 domicílio(s) de menor prioridade');
  });

  it('janela de atendimento em horário real', () => {
    expect(janelaHorario(0, 420)).toBe('qualquer horário');
    expect(janelaHorario(0, 180, '08:00:00')).toBe('manhã (08:00–11:00)');
    expect(janelaHorario(180, 360, '07:30:00')).toBe('tarde (10:30–13:30)');
  });

  it('setas ao longo da rota, no sentido do percurso', () => {
    // ~111 m para o leste e depois ~111 m para o norte (no equador)
    const rota = [[0, 0], [0.001, 0], [0.001, 0.001]];
    expect(comprimentoM(rota)).toBeCloseTo(221.9, 0);
    const setas = setasDaRota(rota, 100);
    expect(setas).toHaveLength(2); // em 50 m e em 150 m
    expect(setas[0].angulo).toBeCloseTo(0); // leste
    expect(setas[1].angulo).toBeCloseTo(-90); // norte (para cima na tela)
    expect(setas[0].lon).toBeCloseTo(0.000449, 5);
  });

  it('nomes de condição legíveis', () => {
    expect(nomeCondicao('crianca_menor_2')).toBe('criança < 2 anos');
    expect(nomeCondicao('outra')).toBe('outra');
  });
});
