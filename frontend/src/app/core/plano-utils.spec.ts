import { describe, expect, it } from 'vitest';

import { ItemRoteiro, NaoAtendida, Plano, PlanoResumo } from './models';
import {
  intervaloVisual, relogio, rotuloRisco, selosDoPlano, situacaoVisita, ultimaVisita, ultimoPorMicroarea,
} from './plano-utils';

function item(ordem: number, extra: Partial<ItemRoteiro> = {}): ItemRoteiro {
  return {
    ordem, domicilio: ordem, codigo: ordem, lat: 0, lon: 0, condicao: 'idoso', motivo: 'rotina', w: 2,
    urgente: false, grave: false, dias_sem_visita: 1, P: 30, chegada: '08:00', inicio: '08:00', fim: '08:15',
    espera_min: 0, caminhada_min: 1, duracao_min: 15, ...extra,
  };
}

function plano(itens: ItemRoteiro[], extra: Partial<Plano> = {}, H = 300): Plano {
  return {
    id: 1, agente: { id: 1, nome: 'ACS' }, microarea: 1, data: '2026-10-09', metodo: 'alns', params: {},
    status: 'viavel', violacoes: [], hora_inicio: '08:00:00',
    metricas: {
      objetivo: 0, caminhada_min: 0, penalidade_residual: 0, penalidade_residual_min: 0, excesso_min: 0, H,
      retorno: '13:00', jornada_min: 360, jornada_max_min: 420, teto_graves: 1, visitas: itens.length,
      candidatas: 10, fora_das_candidatas: 0, urgentes_atendidas: itens.filter((i) => i.urgente).length, graves: 0,
      nao_atendidas: 0, runtime_s: 1, seed: 0, seeds_stats: null, gap: null,
    },
    ubs: { id: 1, nome: 'UBS', lat: 0, lon: 0 }, itens, nao_atendidas: [], rota: null,
    links: { csv: '', gpx: '' }, criado_em: '', ...extra,
  };
}

const ok = (p: Plano) => Object.fromEntries(selosDoPlano(p).map((s) => [s.rotulo, s.ok]));

describe('selosDoPlano', () => {
  it('plano correto passa em tudo', () => {
    const p = plano([item(1, { urgente: true, grave: true }), item(2), item(3)]);
    expect(Object.values(ok(p)).every(Boolean)).toBe(true);
  });

  it('urgência depois de visita comum', () => {
    expect(ok(plano([item(1), item(2, { urgente: true })]))['urgências primeiro']).toBe(false);
  });

  it('teto de graves considera as urgentes graves (D6)', () => {
    const duas = [item(1, { urgente: true, grave: true }), item(2, { urgente: true, grave: true })];
    expect(ok(plano(duas))['graves no limite']).toBe(true);
    expect(ok(plano([...duas, item(3, { grave: true })]))['graves no limite']).toBe(false);
  });

  it('jornada, janelas e urgências sem visita', () => {
    expect(ok(plano([], {}, 421))['volta no horário']).toBe(false);
    expect(ok(plano([], { violacoes: [{ tipo: 'janela', domicilio: 3, quanto: 2 }] }))['horários respeitados']).toBe(false);
    const fora = { urgente: true } as NaoAtendida;
    expect(ok(plano([], { nao_atendidas: [fora] }))['urgências atendidas']).toBe(false);
  });
});

describe('linguagem do itinerário', () => {
  it('risco, situação e última visita', () => {
    expect(rotuloRisco(1)).toBe('risco baixo');
    expect(rotuloRisco(5.4)).toBe('risco máximo');
    expect(situacaoVisita(45, 30)).toEqual({ texto: 'atrasado 15 dias', atrasado: true });
    expect(situacaoVisita(31, 30)).toEqual({ texto: 'atrasado 1 dia', atrasado: true });
    expect(situacaoVisita(30, 30)).toEqual({ texto: 'vence hoje', atrasado: true });
    expect(situacaoVisita(10, 30)).toEqual({ texto: 'em dia (faltam 20 dias)', atrasado: false });
    expect(ultimaVisita(45, 30)).toBe('última visita há 45 dias (máx. 30)');
    expect(ultimaVisita(1, 7)).toBe('última visita há 1 dia (máx. 7)');
  });

  it('barra do intervalo: marca de P em 2/3, preenchimento limitado a 1,5×P', () => {
    const emDia = intervaloVisual(15, 30);
    expect(emDia).toMatchObject({ estado: 'em_dia', curto: '15/30 dias' });
    expect(emDia.pctLimite).toBeCloseTo(66.7, 1);
    expect(emDia.pctCheio).toBeCloseTo(33.3, 1);
    expect(intervaloVisual(30, 30)).toMatchObject({ estado: 'vence', curto: 'vence hoje' });
    const atrasado = intervaloVisual(100, 30);
    expect(atrasado).toMatchObject({ estado: 'atrasado', curto: '+70 dias', pctCheio: 100 });
    expect(atrasado.completo).toBe('última visita há 100 dias (máx. 30) · atrasado 70 dias');
  });
});

describe('utilitários', () => {
  it('último plano por microárea', () => {
    const p = (id: number, microarea: number, criado_em: string) => ({ id, microarea, criado_em }) as PlanoResumo;
    const m = ultimoPorMicroarea([p(3, 1, '2026-10-08T12:00'), p(2, 2, '2026-10-08T11:00'), p(1, 1, '2026-10-08T10:00')]);
    expect(m.get(1)!.id).toBe(3);
    expect(m.get(2)!.id).toBe(2);
  });

  it('relógio a partir da hora de início', () => {
    expect(relogio('08:00:00', 0)).toBe('08:00');
    expect(relogio('07:30:00', 417.1)).toBe('14:27');
    expect(relogio('08:00:00', 418.6)).toBe('14:58'); // trunca como o backend
  });
});
