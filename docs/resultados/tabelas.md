<!-- gerado por python -m engine.graficos; não editar à mão -->

### Instâncias completas (ALNS: 10 sementes; equipe = soma das 4 microáreas)

| cenário | candidatas | guloso | ALNS melhor | ALNS média ± desvio | redução média (pior–melhor) | visitas g/a | caminhada g/a (min) | excesso g/a (min) | t ALNS/semente |
|---|---|---|---|---|---|---|---|---|---|
| base | 46 | 3220.3 | 3185.9 | 3186.1 ± 0.6 | 1.06% (1.07–1.01%) | 16/16 | 37/40 | 0/0 | 2.2 s |
| aglomerado | 43 | 2857.3 | 2795.2 | 2798.3 ± 6.5 | 2.07% (2.17–1.46%) | 19/19 | 39/40 | 4/0 | 3.7 s |
| alta urgência | 58 | 5183.6 | 5021.9 | 5021.9 ± 0.0 | 3.12% (3.12–3.12%) | 18/18 | 44/36 | 39/31 | 0.5 s |
| alto atraso | 46 | 6256.8 | 6181.1 | 6182.5 ± 2.9 | 1.19% (1.21–1.10%) | 17/17 | 38/36 | 8/1 | 2.9 s |
| equipe 4 ACS | 171 | 12085.9 | 11839.4 | 11858.0 ± 2.1 | 1.89% (2.68–1.50%) | 69/70 | 119/129 | 0/0 | 3.4 s |

### Regras clínicas e demanda (melhor semente da ALNS)

| cenário | urgentes atendidas | urgências excedentes (fora da jornada) | urgências primeiro | atrasados entre as candidatas | atrasados não visitados | planos viáveis |
|---|---|---|---|---|---|---|
| base | 6/6 | 0 | sim | 33 | 22 | todos |
| aglomerado | 3/3 | 0 | sim | 35 | 18 | todos |
| alta urgência | 18/18 | 22 | sim | 40 | 33 | todos |
| alto atraso | 6/6 | 0 | sim | 44 | 29 | todos |
| equipe 4 ACS | 11/11 | 0 | sim | 134 | 74 | todos |

### Subinstâncias de 10 candidatas × MILP (5 sorteios por cenário/microárea; ALNS: 10 sementes)

| cenário | MILP ótimo provado | t MILP | gap médio guloso | gap médio ALNS | pior gap ALNS | ALNS = ótimo |
|---|---|---|---|---|---|---|
| base | 5/5 | 0.15 s | 5.39% | 0.33% | 1.67% | 40/50 |
| aglomerado | 5/5 | 0.37 s | 3.24% | 0.40% | 2.22% | 41/50 |
| alta urgência | 5/5 | 0.42 s | 6.57% | 2.96% | 14.78% | 40/50 |
| alto atraso | 5/5 | 0.15 s | 11.33% | 0.00% | 0.00% | 50/50 |
| equipe 4 ACS | 20/20 | 0.83 s | 22.26% | 0.02% | 0.43% | 191/200 |

### Calibração de β e γ (ALNS, 4 cenários × 3 sementes; médias)

| β | γ | excesso (min) | visitas | penalidade residual | atrasados não visitados |
|---|---|---|---|---|---|
| 10 | 2 | 31.5 | 18.6 | 129.9 | 24.4 |
| 10 | 5 | 8.7 | 17.4 | 136.4 | 25.6 |
| 10 | 10 | 8.1 | 17.3 | 136.8 | 25.7 |
| 10 | 20 | 7.9 | 17.2 | 137.0 | 25.8 |
| 30 | 2 | 57.5 | 19.7 | 125.6 | 23.3 |
| 30 | 5 | 50.9 | 19.5 | 126.6 | 23.5 |
| 30 | 10 | 18.1 | 18.0 | 133.0 | 25.0 |
| 30 | 20 | 8.0 | 17.5 | 136.8 | 25.5 |
| 60 | 2 | 58.0 | 19.5 | 125.8 | 23.5 |
| 60 | 5 | 57.4 | 19.5 | 125.8 | 23.5 |
| 60 | 10 | 52.1 | 19.5 | 126.4 | 23.5 |
| 60 | 20 | 18.2 | 18.0 | 133.0 | 25.0 |

### Calibração da ALNS (Taguchi L9; β=30, γ=20; 3 cenários × 5 sementes)

| config | destruição | T0 | resfriamento | gap médio | pior |
|---|---|---|---|---|---|
| 1 | 0.05–0.2 | 10 | 0.99 | 0.423% | 0.82% |
| 2 | 0.05–0.2 | 50 | 0.995 | 0.186% | 0.53% |
| 3 | 0.05–0.2 | 200 | 0.999 | 0.116% | 0.38% |
| 4 | 0.1–0.4 | 10 | 0.995 | 0.317% | 0.77% |
| 5 | 0.1–0.4 | 50 | 0.999 | 0.093% | 0.44% |
| 6 | 0.1–0.4 | 200 | 0.99 | 0.202% | 0.44% |
| 7 | 0.2–0.5 | 10 | 0.999 | 0.297% | 0.69% |
| 8 | 0.2–0.5 | 50 | 0.99 | 0.236% | 0.53% |
| 9 | 0.2–0.5 | 200 | 0.995 | 0.046% | 0.38% |
