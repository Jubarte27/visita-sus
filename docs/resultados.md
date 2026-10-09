# Resultados da validação experimental (P16)

Resumo dos experimentos do §6.8 da proposta. As tabelas completas estão em [resultados/tabelas.md](resultados/tabelas.md) e os gráficos para os slides em [resultados/](resultados/). Os dois são gerados por `engine.graficos` a partir dos CSVs de `backend/data/resultados/`.

## Cenários

Todos os cenários usam a mesma UBS (Bom Jesus, Porto Alegre), 1 ACS por microárea e jornada `T = 360` min (`Tmax = 420`):

| cenário | instância | como foi gerado |
|---|---|---|
| base | `bomjesus` | padrão (750 moradores, urgência 2%, atraso 1,5) |
| aglomerado | `val_aglomerado` | `--aglomerado` |
| alta urgência | `val_urgencia` | `--urgencia 0.15` |
| alto atraso | `val_atraso` | `--atraso 3` |
| equipe 4 ACS | `bomjesus_eq4` | `--acs 4` (4 microáreas, planejadas em paralelo) |

## Principais números

- **A ALNS melhora o guloso em 1% a 3%** nas instâncias completas (46 a 58 candidatas por ACS) e é estável entre sementes (desvio ≤ 6,5 em objetivos de ~3000 a 6000). Leva de 0,5 a 3,7 s por semente.
- **Distância para o ótimo (MILP em subinstâncias de 10 candidatas):** o *gap* médio da ALNS fica entre 0% e 0,4% em 4 dos 5 cenários, e a ALNS acha o ótimo em 80% a 100% das rodadas. O guloso fica entre 3% e 22% do ótimo. O MILP prova o ótimo em todas as subinstâncias, em menos de 1 s.
- **Regras clínicas:** em todos os cenários, todas as urgências que cabem na jornada são atendidas, sempre antes das demais visitas, e todos os planos são viáveis (janelas, jornada e teto de graves).
- **Demanda não atendida:** de 51% a 82% dos domicílios atrasados entre as candidatas ficam sem visita no dia (por exemplo, 22 de 33 no base e 74 de 134 na equipe). Com os dados sintéticos, uma jornada não dá conta da demanda. O relatório da equipe sinaliza essa sobrecarga.

## Calibração

**Pesos β e γ** (grade 3 × 4, 4 cenários × 3 sementes). Como β e γ definem o próprio objetivo, os pares foram julgados pelo plano que produzem. Critério adotado ("hora extra é exceção"): o menor γ com excesso médio de jornada ≤ 10 min, para β = 30.

- Com γ = 2 (valor inicial), o plano enche até perto de `Tmax`, com 57 min de excesso em média.
- **β = 30, γ = 20:** 8 min de excesso médio, 17,5 visitas, com custo de ~2 atrasados a mais sem visita em relação ao γ = 2.

**Parâmetros da ALNS** (Taguchi L9, β = 30, γ = 20, 3 cenários × 5 sementes; resposta = *gap* para a melhor solução conhecida). Pelos efeitos principais, o melhor nível de cada fator foi: destruição 20%–50%, temperatura inicial 200 e resfriamento 0,999. Os três níveis são os padrões atuais de `Params` ([backend/engine/instance.py](../backend/engine/instance.py)).

## Limitações e próximos passos

- **Alta urgência:** é o pior caso da ALNS contra o MILP, com *gap* médio de 2,96% e pior caso de 14,78%. Com 18 urgências obrigatórias e precedentes, sobra pouca liberdade e a ALNS às vezes fixa uma ordem ruim. Um operador de realocação (*or-opt*/2-opt) dentro do bloco de urgências deve reduzir esse *gap* (achado do P15).
- **Instâncias completas:** em 60 s, o MILP não prova a otimalidade (limitante *big-M* fraco). Por isso, ele só serve de referência em subinstâncias.
- **Dados sintéticos:** os parâmetros clínicos (`w`, `P`, `s`, probabilidades) são ilustrativos. Os números de demanda não atendida dizem mais sobre o gerador do que sobre uma equipe real.

## Como reproduzir

A partir de `backend/`, com as instâncias dos cenários geradas (comandos do gerador no [README](../README.md)):

```sh
.venv/bin/python -m engine.validate --sementes 10 --milp-n 10          # data/resultados/validacao.csv
.venv/bin/python -m engine.calibrate pesos --cenarios base=data/instances/bomjesus,...
.venv/bin/python -m engine.calibrate alns --cenarios base=data/instances/bomjesus,...
.venv/bin/python -m engine.graficos                                     # PNGs e tabelas.md em docs/resultados/
```

Conferência em 08/10/2026: uma `bomjesus` gerada de novo (mesma UBS e semente) reproduziu exatamente o objetivo do cenário base (3185,9).
