# Passos de implementação: MVP do visita-sus

Roteiro sequencial para implementar o MVP com **Angular** (`frontend/`), **Django** (`backend/`) e **PostgreSQL** (via `docker compose`). Cada passo é uma unidade de trabalho fechada: tem objetivo, dependências, tarefas, entregáveis e um critério de pronto verificável. Os passos são pedidos um de cada vez ("implemente o passo P05").

O problema e o modelo estão em [estrutura-projeto.md](estrutura-projeto.md) (texto da proposta) e no [README](../README.md). As especificações usadas por vários passos ficam nos apêndices, no fim deste documento.

---

## Como usar este roteiro

**Regras para cada passo (valem para o Claude e para quem mais pegar um passo):**

1. Antes de começar: ler o passo, os apêndices citados por ele e o `git log`/`git status` desde o último passo. Se houver mudança feita fora do roteiro, incorporar em vez de sobrescrever.
2. Fazer só o que o passo pede. O que ficar fora vai em "Notas" do passo ou em um passo futuro.
3. Terminar rodando o critério de pronto e reportar o resultado real, inclusive o que falhou.
4. Atualizar a tabela de status abaixo (e as decisões, se alguma mudou).
5. Nunca fazer commit, `git add` nem push: as mudanças ficam só no working tree e o usuário cuida do git.

**Passos que precisam de rede** (Overpass/IBGE, leva minutos): P04 e P12. Os testes automatizados nunca dependem de rede.

### Status

| Passo | Título | Depende de | Status |
|---|---|---|---|
| P01 | Reorganizar o repositório | n/a | ☑ |
| P02 | Banco no docker e esqueleto Django | P01 | ☑ |
| P03 | Contrato do `engine` e avaliação de rotas | P01 | ☑ |
| P04 | Matriz de tempos, leitura de instância e pré-processamento | P03 | ☑ |
| P05 | Construção gulosa e CLI do solver | P04 | ☑ |
| P06 | ALNS sobre o novo objetivo | P05 | ☑ |
| P07 | Exportação CSV, GPX e GeoJSON | P05 | ◐ feito; falta abrir o GPX num visualizador (conferência visual) |
| P08 | Modelos Django e importação de instâncias | P02, P04 | ☑ |
| P09 | API de microárea e de planos | P06, P07, P08 | ☑ |
| P10 | Planejamento da equipe e relatório | P09 | ☑ |
| P11 | Frontend: esqueleto e mapa da microárea | P09 | ☑ |
| P12 | Frontend: painel da equipe e plano do ACS | P10, P11 | ☑ |
| P13 | Frontend: relatório da equipe | P12 | ☑ |
| P14 | Gerador com vários ACS por equipe | P08 | ☑ |
| P15 | MILP e comparação de métodos | P06 | ☑ |
| P16 | Validação experimental | P14, P15 | ☑ |
| P17 | Fechamento do MVP | todos | ◐ feito; falta o ensaio com banco e frontend numa máquina com Docker e Node |
| P18+ | Pós-MVP | P17 | ☐ |

**Marcos:**
- Fim do P07: algoritmo completo por linha de comando, sem banco.
- Fim do P10: backend do MVP completo.
- Fim do P13: MVP demonstrável.
- Fim do P16: resultados para a apresentação.

---

## Contexto

- **Problema:** planejar o dia de cada Agente Comunitário de Saúde (ACS): **quais** domicílios da sua microárea visitar, **em que ordem**, **em que horário** e **por qual caminho a pé**.
- **Unidade de planejamento:** 1 ACS × 1 dia × 1 microárea. As microáreas são fixas e não se sobrepõem, então nenhuma visita passa de um agente para outro e os planos podem ser calculados em paralelo.
- **Objetivo** (em minutos equivalentes): `min caminhada + β · Σ_{candidatas não visitadas} w_i·(d_i+1)/P_i + γ · max(0, H − T)`.
- **Restrições:** rota UBS → … → UBS, janelas de horário, `H ≤ Tmax`, todas as urgências visitadas e **antes** das não urgentes, e no máximo `K` casos graves.
- **Algoritmo:** construção gulosa, seguida de ALNS (destruição/reparo adaptativos, Simulated Annealing e sanitização das urgências). O MILP serve só para medir o *gap* em instâncias pequenas.
- **Saídas:** itinerário (CSV/GPX), mapa com as rotas, e relatório da equipe com demanda não atendida e sobrecarga por microárea.
- **Dados:** sintéticos sobre mapas reais (Censo 2022 + OSM).

### Estado atual (08/10/2026)

- **`backend/src/generator.py` (Eduardo):** pronto. Microárea = setor da UBS + vizinhos até a população-alvo. Domicílios do Censo distribuídos pelas edificações do OSM, cada um inserido como nó da malha a pé (`travel_time` em min). Atributos clínicos sintéticos. Candidatas = urgentes + 40 de maior penalidade.
- **`backend/src/solver.py`:** parcial. O objetivo maximiza `profit`. O `main` usa metros com orçamento 3000 (o certo, como o Eduardo apontou, é `travel_time` com 360 min). Faltam urgência obrigatória e precedente, teto de graves, `T` × `Tmax`, janelas (não são passadas), semente e saída serializável. Usa `nearest_nodes` em vez da coluna `node` do gerador.
- **"Só 13 pontos visitados" não era bug:** os pontos que faltavam passavam de 3 km e não cabiam no orçamento. Por isso, toda visita deixada de fora precisa ter um motivo explícito.
- **Instâncias Bom Jesus:** só `meta.json`/`mapa.html` estão no git. Os `.gpkg`/`.graphml` precisam ser gerados de novo.
- **Caminhos quebrados pela reorganização de pastas:** o gerador procura `backend/data/`, mas o `fetch.sh` (em `docs/`) baixa para `docs/data/`. O README aponta para os caminhos antigos.

### Divisão de trabalho

Toda a implementação é feita pelo **Claude**, passo a passo, sob pedido: algoritmo (guloso, ALNS e MILP), backend, frontend e validação (P01–P17 e pós-MVP). A única exceção é a **apresentação**, que fica com o grupo, por último.

O gerador (`generator.py`, feito pelo Eduardo) é o ponto de partida e é ajustado pelo Claude nos passos P01, P04 e P14.

### Decisões

| # | Decisão | Valor adotado | Situação |
|---|---|---|---|
| D1 | Banco | PostgreSQL puro (sem PostGIS). Geometrias em GeoJSON (`JSONField`), coordenadas em `lat`/`lon`. | adotada |
| D2 | Grafo e matriz | Em arquivo (`graph.graphml`, `matrix.npz`) em `backend/data/instances/<nome>/`. O banco guarda o caminho. | adotada |
| D3 | Execução da otimização | Síncrona, com tempo limite por ACS. A equipe roda os ACS em paralelo (`ProcessPoolExecutor`). | adotada |
| D4 | Algoritmo isolado | `backend/engine/` em Python puro, sem importar Django. | adotada |
| D5 | Urgente com janela | O gerador cria urgentes **sem janela**. | a confirmar |
| D6 | Urgentes graves e teto `K` | Contam no `K`, mas são obrigatórias. O `K` limita só as graves não urgentes. | a confirmar |
| D7 | β e γ | β = 30, γ = 20 (calibrados no P16, ver [resultados.md](resultados.md)). ALNS: destruição 20–50%, T0 = 200, resfriamento 0,999. | adotada |
| D8 | Dias desde a última visita | O banco guarda `ultima_visita` (data). O `d` é calculado para a data do plano. | adotada |
| D9 | Nomes de exibição | ACS com nomes fictícios e microáreas como "Microárea 02 · Bom Jesus" (`Microarea.rotulo`); equipe padrão "eSF <bairro> (N ACS)". `Microarea.nome` e `Equipe.nome` continuam sendo as chaves da importação. Bancos antigos: `manage.py nomes_ficticios`. | adotada |
| D10 | Paralelismo | Pool de processos compartilhado (`services.pool()`): os ACS de uma equipe e as requisições simultâneas de ACS diferentes rodam em paralelo. O painel planeja um ACS por requisição, para mostrar o progresso de cada card. | adotada |

---

## Passos

### P01: Reorganizar o repositório

**Objetivo:** deixar a estrutura de pastas do [Apêndice A](#apêndice-a-estrutura-de-pastas) com os caminhos funcionando, sem mudar comportamento.

**Tarefas:**
1. Mover `backend/src/generator.py` e `backend/src/solver.py` para `backend/engine/` (com `__init__.py`). Mover o notebook para `backend/legacy/`.
2. No gerador: `ROOT` passa a ser `backend/` e os dados ficam em `backend/data/` (`SETORES_PATH`, `OUT_DIR`, cache do osmnx).
3. Mover `docs/fetch.sh` para `backend/fetch.sh` e baixar para `backend/data/`.
4. `backend/requirements.txt` só com o necessário para gerador e solver. `contextily`, `fudgeo` e `pyrosm` vão para `backend/requirements-legacy.txt`.
5. `.gitignore`: ignorar `backend/data/`, `.venv`, `__pycache__`, `node_modules`, `.env`, `frontend/dist`. Remover as exceções de `instances/`, que não funcionavam. `docs/data/instances/` fica como amostra versionada.
6. README: corrigir os caminhos (proposta em `docs/`, comandos a partir de `backend/`).

**Entregáveis:** `backend/engine/{__init__,generator,solver}.py`, `backend/fetch.sh`, `backend/requirements*.txt`, `.gitignore`, `README.md`.

**Pronto quando:**
- `cd backend && .venv/bin/python -m engine.generator --help` mostra a ajuda;
- `python -c "import engine.solver"` importa sem erro;
- `git status` mostra só movimentações e as edições acima.

---

### P02: Banco no docker e esqueleto Django

**Objetivo:** subir o Postgres e um projeto Django vazio, conectado a ele.

**Tarefas:**
1. `docker-compose.yml` na raiz com o serviço `db` ([Apêndice B](#apêndice-b-docker-e-ambiente)) e `.env.example`.
2. Adicionar ao `requirements.txt`: `django`, `djangorestframework`, `django-cors-headers`, `psycopg[binary]`, `django-environ`, `pytest`, `pytest-django`.
3. `django-admin startproject config .` em `backend/` e app `core`.
4. `settings.py` lendo `../.env` (django-environ): banco, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`. DRF e CORS configurados, `LANGUAGE_CODE="pt-br"`, `TIME_ZONE="America/Sao_Paulo"`.
5. `GET /api/health/` devolve `{"status": "ok", "db": true}` (faz um `SELECT 1`).
6. `pytest.ini` com `DJANGO_SETTINGS_MODULE` e um teste do health.

**Entregáveis:** `docker-compose.yml`, `.env.example`, `backend/manage.py`, `backend/config/`, `backend/core/`, `backend/pytest.ini`, `backend/tests/test_health.py`.

**Pronto quando:**
- `docker compose up -d db` fica *healthy*;
- `manage.py migrate` roda sem erro;
- `curl localhost:8000/api/health/` responde `ok`;
- `pytest` passa.

---

### P03: Contrato do `engine` e avaliação de rotas

**Objetivo:** fixar as estruturas de dados compartilhadas por guloso, ALNS, MILP e backend, e implementar a **única** função de avaliação do objetivo.

**Tarefas:**
1. `engine/instance.py`: dataclasses `Visit`, `Instance`, `Params`, `Stop` e `Solution` ([Apêndice C](#apêndice-c-contrato-do-engine)).
2. `engine/evaluation.py`:
   - `schedule(inst, route)`: chegada, espera até `a_i`, início e fim de cada parada, e `H`;
   - `evaluate(inst, params, route)`: caminhada, penalidade residual (soma sobre as candidatas fora da rota), excesso, objetivo e lista de violações (janela, `Tmax`, graves `> K`, urgente ausente, urgente depois de não urgente);
   - `is_feasible`;
   - `build_solution(...)`, que monta a `Solution` com os motivos de cada visita feita (`urgencia`/`atraso`/`risco`).
3. `tests/engine/test_evaluation.py`: instância de 4 a 5 pontos com matriz escrita à mão, cronograma e objetivo conferidos manualmente, e um caso para cada violação.

**Entregáveis:** `engine/instance.py`, `engine/evaluation.py`, testes.

**Pronto quando:** os testes de avaliação passam e `engine/` não importa nada de Django.

**Notas:** este contrato é a base de todos os passos seguintes (guloso, ALNS, MILP, backend). Mudanças nele depois deste passo exigem revisar os passos já feitos.

---

### P04: Matriz de tempos, leitura de instância e pré-processamento

**Objetivo:** sair dos arquivos do gerador e chegar a uma `Instance` pronta para otimizar.

**Tarefas:**
1. Gerador: urgentes sem janela (D5). Gravar `data_base` no `meta.json`.
2. `engine/matrix.py`:
   - `build_matrix(G, nodes)`: Dijkstra com `weight="travel_time"` a partir de cada nó de acesso;
   - `save_matrix`/`load_matrix` (`matrix.npz` com `nodes` e `t`);
   - `leg_path(G, u, v)`: nós e geometria de um trecho;
   - `load_graph(path)`: `ox.load_graphml` com os `edge_dtypes` do solver atual.
3. `engine/io.py`: `load_instance_files(dir)` lê `instance.gpkg` (camada `visits`) e `meta.json`, e usa a coluna `node` (não `nearest_nodes`).
4. `engine/preprocess.py`:
   - calcula `d` a partir de `ultima_visita` e da data do plano;
   - calcula a penalidade;
   - seleciona as candidatas (urgentes + top `n_candidatas`);
   - descarta inviáveis: ida e volta + serviço `> Tmax`, ou chegada mais cedo possível depois de `b_i`. Motivo: `inviavel`;
   - urgentes que não cabem: `urgencia_excedente`;
   - devolve `Instance` + lista de descartes com motivo.
5. Regenerar `bomjesus` e `bomjesus_2000` com os comandos do README (precisa de rede) e calcular a matriz delas.
6. Testes com um grafo sintético pequeno (grade do networkx) para a matriz e o pré-processamento.

**Entregáveis:** `engine/{matrix,io,preprocess}.py`, gerador ajustado, testes, instâncias em `backend/data/instances/`.

**Pronto quando:**
- os testes passam;
- um script curto carrega `bomjesus`, monta a `Instance` e imprime: número de candidatas, descartes por motivo, e tempo máximo e médio da matriz em minutos (valores plausíveis para 0,15 km²).

**Notas (implementação):**
- **Entrada comum:** o pré-processamento recebe `Household` (domicílio com `ultima_visita`) e `Agent` (nó da UBS, T, Tmax, K), tanto do CLI quanto do banco. Devolve `Preprocessed`:
  - `instance`;
  - `discarded`: `(id, motivo)` para `inviavel` e `urgencia_excedente`;
  - `not_candidates`: ids viáveis que ficaram fora das candidatas do dia. Não são descartes, mas contam como demanda no relatório (P10).
- **Urgências que não cabem juntas:** a verificação usa a rota de vizinho mais próximo só com as urgentes. É uma heurística, não o ótimo.
- **Resumo da instância:** `python -m engine.io <pasta> [--data]` imprime o resumo e cria o `matrix.npz` na primeira leitura.
- **Fixture sem rede:** a instância mínima em `tests/fixtures/mini_instance.py` (grade 4×4) é reaproveitada no P08.

---

### P05: Construção gulosa e CLI do solver

**Objetivo:** primeira solução viável com o objetivo da proposta, rodando por linha de comando.

**Tarefas:**
1. `engine/greedy.py`, seguindo a §6.5 da proposta:
   - urgências primeiro, por vizinho mais próximo a partir da UBS;
   - depois insere a candidata com maior `β·penalidade ÷ minutos acrescentados`, na melhor posição viável (janelas, `Tmax`, `K`);
   - repete até nenhuma caber; as que sobram ficam com o motivo `nao_coube` ou `teto_graves`.
   - Reaproveitar a lógica de inserção do `solver.py` atual.
2. `engine/solve.py` (CLI): `python -m engine.solve <dir_instancia> --metodo guloso [--data AAAA-MM-DD] [--beta --gamma]`. Imprime métricas e roteiro e grava `solucao.json` (Solution serializada).
3. Testes: a solução é viável, urgentes estão no início, graves `≤ K` e o resultado é determinístico.

**Entregáveis:** `engine/greedy.py`, `engine/solve.py`, testes.

**Pronto quando:** os testes passam e `python -m engine.solve data/instances/bomjesus --metodo guloso` mostra um roteiro de 10 a 20 visitas com `H ≤ 420`, em menos de 1 s.

**Notas (implementação):**
- **Posição de inserção:** a que menos aumenta caminhada + γ·excesso (empate: menor `H`). Escolher só pelo menor `H` perdia posições de caminhada zero.
- **Critério de inserção:** a candidata só entra se **melhora o objetivo**. Por isso o guloso pode deixar de fora visitas que caberiam no tempo.
- **Função `timing(inst, route)`:** acrescentada a `evaluation.py`. É o cronograma rápido (H, caminhada, janelas ok), sem montar paradas, e vai ser usada também pela ALNS.
- **Resultado em `bomjesus`:** 19 visitas, H = 411 (excesso de 51 min), 17 ms. Com β = 30 e γ = 2, deixar uma visita de penalidade ~2,7 para depois custa ~80 min equivalentes, e fazê-la em horário extra custa ~30 min (2 × 15). Então o plano sempre enche até perto de `Tmax`. Para o excesso frear as inserções, seria preciso γ ≳ β·penalidade/s (~5 nesse exemplo). **Calibrar β/γ no P16 (D7).**

---

### P06: ALNS sobre o novo objetivo

**Objetivo:** refinar o guloso com a ALNS da proposta, usando a avaliação do P03.

**Tarefas:**
1. `engine/alns.py`, refatorando `ALNSOrienteeringSolver`:
   - o critério de melhor e de aceitação passa a ser **minimizar o objetivo** de `evaluation.py`;
   - `random.Random(seed)` por execução; para por iterações **ou** por `time_limit_s`;
   - inserções nunca violam janela, `Tmax` ou `K`; a destruição não remove urgentes;
   - **sanitização** depois de cada reparo (urgentes no início);
   - pesos adaptativos por segmento;
   - manter os operadores atuais e o 2-opt.
2. `solve_multi_seed(inst, params)`: roda as sementes de `params.seeds`, devolve a melhor e preenche `seeds_stats` (média, desvio, melhor, pior).
3. CLI: `--metodo alns`.
4. Testes: viável; nunca pior que o guloso na mesma instância; mesma semente dá o mesmo resultado; respeita o tempo limite.
5. Depois de validado, remover o `engine/solver.py` antigo.

**Entregáveis:** `engine/alns.py`, CLI atualizada, testes.

**Pronto quando:** os testes passam e, em `bomjesus`, `--metodo alns` com 5 sementes dá objetivo `≤` guloso, imprime a variação entre sementes e termina em até ~5 s por semente.

**Notas (implementação):**
- **Inserção em O(1):** usa o esquema de folgas de Savelsbergh (`RouteState`: chegada, espera, soma das esperas e folga máxima por posição). Um teste confere contra o cronograma completo em centenas de inserções aleatórias. A rota final sempre passa pelo `evaluate`.
- **Operadores:** destruição (aleatória, pior custo, Shaw, segmento, arestas caras) e reparo (guloso, regret-2, maior penalidade, maior ganho líquido, agrupada), todos sobre o objetivo novo. O reparo só insere com ganho no objetivo.
- **Bloco de urgentes:** os operadores não mexem nele. O 2-opt age dentro de cada bloco, e por isso pode reordenar as urgentes.
- **Recompensas e SA:** 33/9/13 (Ropke & Pisinger), segmento de 25 iterações, inércia 0,2, peso mínimo 0,05. τ inicial 50 com resfriamento 0,995 por iteração.
- **Várias sementes:** `solve_multi_seed` parte do mesmo guloso em todas as sementes e roda em sequência.
- **Resultados:**

  | Instância | Guloso | ALNS (melhor) | ALNS (média ± desvio) | Visitas | Tempo por semente |
  |---|---|---|---|---|---|
  | `bomjesus` | 3026,9 | 2984,5 (−1,4%) | 3000,4 ± 13,0 | 20 (guloso 19) | ~2 s |
  | `bomjesus_2000` | 6043,1 | 6017,3 (−0,4%) | 6029,1 ± 6,1 | 19 | ~0,5 s |

- **Remoções:** o `engine/solver.py` antigo foi removido. As colunas `profit`/`cost` continuam no gerador só por compatibilidade.

---

### P07: Exportação CSV, GPX e GeoJSON

**Objetivo:** gerar as saídas do itinerário a partir de uma `Solution`.

**Tarefas:**
1. `requirements.txt`: `gpxpy`.
2. `engine/export.py`:
   - `route_geojson(G, inst, sol)`: `LineString` pela malha, concatenando `leg_path`;
   - `to_csv(...)`: ordem, id, condição, motivo, chegada, início, fim e caminhada, com horas reais a partir de `hora_inicio`;
   - `to_gpx(...)`: trilha pela malha + waypoints numerados.
3. CLI: `--export csv,gpx,geojson`, gravando na pasta da instância.

**Entregáveis:** `engine/export.py`, CLI atualizada, testes de formato.

**Pronto quando:** os três arquivos são gerados para `bomjesus`, e o GPX abre em um visualizador (ex.: gpx.studio) com a trilha seguindo as ruas.

**Notas (implementação):**
- **Entrada comum:** `itinerary(inst, sol, início, info)` recebe `info[id] = {condicao, lat, lon}` (UBS = id -1). Vem de `InstanceFiles.info()` no comando e vai vir do banco no P09.
- **Arquivos gravados:**
  - `itinerario.csv`: vírgula, ponto decimal, UTF-8 com BOM para o Excel; última linha = retorno à UBS;
  - `itinerario.gpx`: trilha pela malha + waypoints `UBS`, `01 · domicílio N`, …;
  - `rota.geojson`: FeatureCollection com a rota e as paradas.
- **Conferência automática em `bomjesus`:** a trilha GPX tem 3283 m, igual à caminhada da solução (43,8 min × 75 m/min). Todos os 335 vértices ficam sobre arestas da malha (distância máxima 0,000 m).

---

### P08: Modelos Django e importação de instâncias

**Objetivo:** levar as instâncias para o banco.

**Tarefas:**
1. Modelos do [Apêndice D](#apêndice-d-modelos-django), migrations e admin para todos.
2. Comando `importar_instancia <dir> [--equipe NOME] [--agente NOME] [--data-base AAAA-MM-DD]`:
   - cria ou reutiliza `Ubs` e `Equipe`;
   - cria `Microarea`, `Agente` e `Domicilio` (com `ultima_visita = data_base − d`);
   - calcula `matrix.npz` se não existir;
   - é idempotente: reimportar a mesma instância atualiza em vez de duplicar.
3. Comando `gerar_instancia --ubs=lat,lon --name X [opções do gerador] [--equipe]`: gera e importa.
4. Testes do import com uma instância mínima em `tests/fixtures/` (gpkg + graphml pequenos, sem rede).

**Entregáveis:** `core/models.py`, `core/admin.py`, migrations, `core/management/commands/`, fixture, testes.

**Pronto quando:** `importar_instancia data/instances/bomjesus` cria 1 UBS, 1 equipe, 1 microárea, 1 agente e 439 domicílios; o admin lista tudo; reimportar não duplica; os testes passam.

**Notas (implementação):**
- **Lógica da importação:** fica em `core/importer.py`, e os dois comandos só a chamam.
- **Chaves de reaproveitamento:**
  - UBS: pela coordenada;
  - equipe: por UBS + nome (padrão "eSF <bairro>");
  - microárea: pelo nome da instância;
  - domicílio: por (microárea, `codigo` = linha do gpkg).
- **Reimportar:**
  - atualiza tudo, mas preserva ajustes manuais do agente (ex.: `hora_inicio`);
  - remove domicílios que sumiram do arquivo;
  - falha, sem alterar nada, se algum plano depende deles.
- **Nomes no banco:** `peso` (w), `intervalo_max_dias` (P), `duracao_min` (s). Os horários dos planos ficam em minutos desde o início da jornada, com a `hora_inicio` guardada no `Plano` (Apêndice D atualizado).
- **Pasta das instâncias:** `INSTANCES_DIR` (padrão `backend/data/instances`). `Microarea.instancia_dir` é relativa a ela.
- **Mesma equipe:** `bomjesus` e `bomjesus_2000` foram importadas na mesma equipe ("eSF Bom Jesus"), como pede o P10.

---

### P09: API de microárea e de planos

**Objetivo:** expor ao frontend os dados da microárea e o planejamento de um ACS.

**Tarefas:**
1. `core/services.py`:
   - `montar_instancia(agente, data, params)`: domicílios + matriz + ACS → preprocess → `Instance`;
   - `planejar(agente, data, metodo, params)`: roda o solver e grava `Plano`, `ItemRoteiro` e `NaoAtendida` (inclusive os descartes do pré-processamento) e a `rota_geojson`;
   - grafo em `lru_cache` por microárea.
2. Serializers e views (DRF) das rotas marcadas como P09 no [Apêndice E](#apêndice-e-api), no formato de JSON definido lá.
3. Erros de solver devolvem o plano parcial com os motivos, não 500.
4. Testes de API com a fixture do P08.

**Entregáveis:** `core/services.py`, `core/serializers.py`, `core/views.py`, `core/urls.py`, testes.

**Pronto quando:**
- `curl -X POST /api/planos/ -d '{"agente":1,"data":"2026-10-09","metodo":"alns"}'` devolve o plano no formato do Apêndice E;
- os links `itinerario.csv`/`.gpx` baixam os arquivos;
- `/api/microareas/1/domicilios/?data=...` devolve uma FeatureCollection válida;
- os testes passam.

**Notas (implementação):**
- **Planejamento síncrono:** a ALNS com 5 sementes leva ~10 s na `bomjesus`. Os parâmetros têm teto por requisição (≤ 10 sementes, ≤ 30 s por semente, ≤ 100 mil iterações).
- **Fotografia do plano:** o `Plano` guarda T, Tmax, K, velocidade e hora de início usados (`params.acs`, `hora_inicio`). Alterar o ACS depois não muda planos antigos.
- **Velocidade do ACS:** a matriz foi calculada na velocidade do gerador. Se o ACS tiver outra (PATCH), os tempos são reescalados, sem recalcular a malha.
- **Não atendidas:** gravadas com o motivo, inclusive os descartes do pré-processamento. As viáveis que ficaram fora das candidatas só entram na contagem (`n_fora_candidatas`).
- **Erros:**
  - parâmetros inválidos: 400;
  - arquivos da instância ausentes: 409;
  - plano sem nenhuma visita viável: 201 com todos os domicílios como `inviavel`, não 500.
- **Além do previsto:** `GET /api/planos/` (lista, com filtros `?agente=`, `?microarea=`, `?data=`) e `DELETE /api/planos/{id}/`.
- **Pendência para o P19:** `dias_sem_visita` dos itens é recalculado a partir de `ultima_visita`. Quando houver "confirmar execução", vale gravar `d` no item.

---

### P10: Planejamento da equipe e relatório

**Objetivo:** planejar todos os ACS de uma equipe numa chamada e produzir o relatório para a gestão.

**Tarefas:**
1. `POST /api/equipes/{id}/planejar/`: roda `planejar` para cada agente em paralelo (`ProcessPoolExecutor`) e devolve a lista de planos resumidos.
2. `GET /api/equipes/{id}/relatorio/?data=`: uma linha por microárea, usando o último plano de cada ACS na data (colunas no Apêndice E), mais um total da equipe e o alerta de sobrecarga (limiares configuráveis em settings).
3. `GET /api/equipes/`, `GET /api/equipes/{id}/`.
4. Testes.

**Entregáveis:** views, serializers e serviço do relatório, testes.

**Pronto quando:** com `bomjesus` e `bomjesus_2000` importadas na mesma equipe, `planejar` devolve 2 planos e o relatório mostra 2 linhas com totais coerentes com os planos.

**Notas:** `bomjesus` e `bomjesus_2000` se sobrepõem no território. Isso serve só para testar; a equipe realista vem no P14.

**Notas (implementação):**
- **Fluxo do `planejar_equipe`:**
  1. monta todas as instâncias no processo principal (se faltar arquivo de alguma microárea, devolve 409 e nada é gravado);
  2. resolve cada ACS em um processo (`spawn`, módulo leve `engine.methods`, sem Django);
  3. grava todos os planos numa transação.
- **Liga/desliga:** `PLANEJAMENTO_PARALELO` (padrão ligado).
- **Relatório (`core/relatorio.py`):** usa o último plano de cada ACS na data. Microárea sem plano aparece com `sem_plano: true`. Em cada linha:
  - domicílios e atrasados;
  - candidatas, planejadas, não atendidas (total e por motivo), fora das candidatas;
  - atrasados e urgentes sem visita;
  - penalidade residual (e em min = β·Σ), caminhada, jornada usada, excesso, retorno;
  - `alerta_sobrecarga` com `motivos_alerta`.

  A resposta também traz o total da equipe.
- **Alerta de sobrecarga** (`RELATORIO_LIMIARES`), disparado quando:
  - o excesso passa de 30 min;
  - alguma urgência fica sem visita;
  - mais de 25% dos domicílios estão atrasados e não foram visitados.
- **Resultado em `bomjesus` + `bomjesus_2000` (09/10):** 2 planos em 9,6 s em paralelo (só a `bomjesus` leva 9,0 s). As duas microáreas ficam em alerta, por excesso (57 e 41 min) e por ~28% e ~34% de atrasados sem visita. Isso é esperado com os dados sintéticos (`--atraso 1.5`) e com β/γ ainda não calibrados (P16).

---

### P11: Frontend: esqueleto e mapa da microárea

**Objetivo:** projeto Angular rodando, conectado à API, com o mapa base.

**Tarefas:**
1. `ng new frontend` (versão estável atual, standalone, roteamento, SCSS) e Angular Material.
2. `proxy.conf.json` (`/api` → `localhost:8000`), `environment.ts`.
3. Interfaces TypeScript que espelham o Apêndice E. Serviços `EquipeService`, `MicroareaService`, `PlanoService`.
4. Layout: barra superior com a escolha da equipe e da data, e roteamento das telas do [Apêndice F](#apêndice-f-telas).
5. `MapComponent` reutilizável com `leaflet` direto:
   - tiles do OSM com atribuição;
   - camadas: polígono da microárea, domicílios coloridos por `w` (paleta do `mapa.html`), borda grossa para urgentes, e UBS.

**Entregáveis:** `frontend/` com o esqueleto, os serviços e o `MapComponent`.

**Pronto quando:** `ng build` passa e, com o backend no ar, `ng serve` mostra o mapa da microárea `bomjesus` com os domicílios e um popup de atributos ao clicar.

**Notas (implementação):**
- **Angular 21 (LTS):** o 22 (latest) exige Node ≥ 22.22.3, e o apt do Ubuntu 26.04 instala o 22.22.1.
- **npm:** o npm 9.2 do Ubuntu falha (`edgesOut`), e o 10 também (ciclo de *peers* do vitest). Instalar com `npx npm@11 install` (`packageManager` no `package.json`).
- **Estrutura:**
  - `core/`: tipos do Apêndice E, serviços `EquipeService`, `MicroareaService` e `PlanoService`, e `SelecaoService` (equipe e data da barra superior; a equipe fica guardada no navegador);
  - `shared/map/`: `MapComponent` e `map-utils.ts`;
  - `pages/`: início, microárea, painel (esboço), plano e relatório (esboços para P12/P13).
- **`MapComponent`:** Leaflet direto. Domicílios agrupados por ponto de acesso, um marcador por ponto (como o `mapa.html`), com cor = w máx, borda grossa = urgente e popup com a tabela dos domicílios. Camadas: microárea, malha a pé (desligada por padrão), domicílios, UBS e dois fundos OSM. A instância do Leaflet é exposta como signal (`mapa`), e `focar()` centraliza um ponto; os dois servem às telas do P12.
- **Conferência no navegador:** Chromium headless via `puppeteer-core`, fora do projeto. A página `/microareas/1` mostra 309 marcadores (= pontos de acesso), o polígono, a UBS e o resumo do dia (125 atrasados, 6 urgentes, 23 graves); o popup lista os domicílios do ponto; sem erros no console. Testes unitários de `map-utils` passam no vitest (`ng test`).

---

### P12: Frontend: painel da equipe e plano do ACS

**Objetivo:** fluxo principal do MVP: planejar o dia e conferir as rotas.

**Tarefas:**
1. **Painel da equipe** (Apêndice F, tela 1): data, método, botão "Planejar dia" com indicador de carregamento, e cards por ACS.
2. **Plano do ACS** (tela 2):
   - mapa com a rota e marcadores numerados; não atendidas destacadas;
   - itinerário lateral (clicar centraliza o marcador) e lista de não atendidas com o motivo;
   - camadas liga/desliga;
   - barra de jornada `T`/`Tmax` e selos de regras;
   - botões de exportação CSV/GPX.

**Pronto quando:** do navegador, dá para planejar o dia da equipe, abrir cada plano, ver a rota seguindo as ruas na ordem do itinerário e baixar CSV/GPX.

**Notas (implementação):**
- **Painel (`/equipes/:id`):**
  - método guloso/ALNS e parâmetros opcionais (β, γ, sementes, tempo por semente);
  - "Planejar dia", com barra de progresso e estimativa de tempo;
  - um card por ACS com o último plano da data: visitas, não atendidas, caminhada, retorno/excesso, penalidade e barra de jornada;
  - ações "Abrir plano", "Microárea" e "(Re)planejar só este ACS".
- **Plano (`/planos/:id`):**
  - números da jornada, barra T/Tmax e selos das regras (urgências primeiro, graves ≤ K, jornada ≤ Tmax, janelas, urgências atendidas), calculados em `core/plano-utils.ts`;
  - CSV/GPX;
  - abas Itinerário e Não atendidas: clicar numa linha centraliza o marcador e abre o popup.
  - **Mapa:** rota pela malha, paradas numeradas (cor = w, borda preta = urgente), não atendidas (×) e demais domicílios esmaecidos. Todas as camadas podem ser ligadas e desligadas.
- **Backend:** `GET /api/planos/?equipe=`, e `nao_atendidas` no plano resumido.
- **Conferência de ponta a ponta (Chromium headless, `bomjesus` + `bomjesus_2000`, 08/10):**
  - "Planejar dia" (ALNS) gerou os 2 planos e os cards se atualizaram;
  - cada plano mostra a rota e as paradas 1…20 / 1…19 em sequência, com os 5 selos ✓;
  - clicar na 3ª linha abre o popup da 3ª visita;
  - CSV e GPX respondem 200 pelo proxy;
  - sem erros no console.

---

### P13: Frontend: relatório da equipe

**Objetivo:** tela de apoio à gestão.

**Tarefas:** tela 3 do Apêndice F: tabela por microárea, barras de penalidade residual e de excesso, microáreas sobrecarregadas em destaque, e total da equipe.

**Pronto quando:** o relatório bate com os números da API e a microárea sobrecarregada aparece destacada (testar com um cenário de alta urgência).

**Marco:** MVP demonstrável.

**Notas (implementação):**
- **Tela (`/equipes/:id/relatorio`):** usa a data da barra superior.
  - **indicadores:** microáreas em sobrecarga, planejadas/candidatas, não atendidas, atrasados sem visita, urgências sem visita e excesso total;
  - **dois gráficos** de barras horizontais: penalidade residual (min) e excesso de jornada, este com a linha do limiar;
  - **tabela por microárea** com o total da equipe e uma nota explicando os critérios.
- **`BarrasComponent` (`shared/barras/`):** SVG próprio, uma série por gráfico (sem legenda; o título diz o que é).
  - cor de série `#2a78d6` (passou no validador do skill de visualização);
  - barras de 16 px, quadradas na base e com ponta arredondada de 4 px; valor na ponta;
  - tooltip ao passar o mouse ou focar, com área de clique igual à linha inteira;
  - microárea sem plano aparece como "sem plano".
- **Sobrecarga** em vermelho de status (`#d03b3b`), sempre com ícone ⚠ e texto, nunca só cor: linha destacada com os motivos, rótulo nos gráficos e indicadores críticos.
- **Cenário de teste:** equipe "eSF Bom Jesus · cenários" no banco, com `cenario_base` (`--atraso 1.0`) e `cenario_urgencia` (`--urgencia 0.3`, 76 urgentes). Ambos gerados com o cache do osmnx, ~6 s cada, sem rede.
  - Planejada com ALNS e γ = 10: a base fica ok (16 visitas, retorno 13:59, sem excesso);
  - a de alta urgência fica em sobrecarga: 59 urgências excedentes, 43 min de excesso, 26% de atrasados sem visita.
  - A tela bate com a API (1 alerta, 33 planejadas de 103, 129 não atendidas, 114 atrasados sem visita, 59 urgências, penalidade 6147 min). Conferido no Chromium headless.
- **Calibração:** com o γ = 2 padrão, as duas microáreas encheriam até perto de Tmax e entrariam em alerta por excesso. Isso reforça calibrar β/γ no P16.

---

### P14: Gerador com vários ACS por equipe

**Objetivo:** equipe realista, com N microáreas contíguas em torno da mesma UBS.

**Tarefas:**
1. Opção `--acs N` no gerador: monta a área com `populacao = N × 750` e a divide em N microáreas contíguas:
   - crescimento de regiões sobre os setores, a partir dos mais distantes entre si;
   - se houver menos setores que N, k-means nos domicílios (`scikit-learn`).
   - Grafo e UBS compartilhados.
2. Saída: uma subpasta por microárea, ou uma coluna `microarea_id` em `visits`, e `meta.json` com a equipe.
3. `importar_instancia` reconhece o formato de equipe: 1 equipe, N microáreas, N agentes.
4. Mapa do gerador colorindo as microáreas.

**Pronto quando:** `gerar_instancia --ubs=... --name bomjesus_eq4 --acs 4` cria uma equipe com 4 microáreas sem sobreposição. O painel e o relatório mostram os 4 ACS.

**Notas (implementação):**
- **Formato:** uma pasta por equipe, com grafo e matriz compartilhados.
  - `visits.microarea` (1..N; a UBS fica com 0);
  - camada `microareas` (polígono e códigos dos setores de cada uma);
  - bloco `meta.equipe` (partição usada e, por microárea, setores, bairros, população, domicílios, pontos de acesso, urgentes e atrasados).
- **Compatibilidade:** com `--acs 1` (padrão), a saída é idêntica à anterior. A divisão não consome o gerador aleatório.
- **Partição (`partition_setores`):**
  - sementes afastadas (máxima distância mínima entre centroides);
  - a região de menor população anexa o setor vizinho livre mais próximo da sua semente;
  - setores isolados vão para a região mais próxima.
  - Com menos setores que ACS, `partition_kmeans` nas edificações (peso = domicílios). Domicílios da mesma edificação ficam juntos.
- **Importação:** `importar_instancia` devolve a lista de microáreas. Numa equipe, cria "eSF <instância>" com as microáreas `<instância>_<k>` e os agentes "ACS <instância> <k>" (`--agente` vira prefixo). Também funciona via `gerar_instancia --acs N`.
- **Engine:** `engine.io`/`engine.solve` ganharam `--microarea k`, com saídas `solucao_m<k>.json` etc.
- **Mapa do gerador:** colore as microáreas.
- **Resultado `bomjesus_eq4`** (UBS Bom Jesus, 4 × 750 hab.; ~3 min, quase tudo esperando o Overpass):
  - 7 setores (3222 moradores) divididos em 4 microáreas contíguas, de 1–2 setores, 505–951 hab. e 271–427 domicílios;
  - interseção 0 m² entre todos os pares;
  - planejada com ALNS e γ = 10: 4 planos em 21,7 s em paralelo;
  - painel e relatório mostram os 4 ACS (conferido no Chromium headless). Três microáreas ficam em alerta por mais de 25% de atrasados sem visita, efeito do `--atraso 1.5` padrão dos dados sintéticos.

---

### P15: MILP e comparação de métodos

**Objetivo:** referência exata para medir o *gap* da ALNS.

**Tarefas:**
1. `requirements.txt`: `pulp` (CBC embutido).
2. `engine/milp.py`: formulação da §6.4 da proposta:
   - variáveis `x_ij`, `y_i`, `h_i`, `H` e `E ≥ H − T`, `E ≥ 0`;
   - tempo com big-M;
   - urgentes obrigatórias;
   - precedência `h_j ≥ h_i + s_i − M(1 − y_j)` para `i ∈ U`, `j ∉ U`;
   - `Σ_G y_i ≤ K`;
   - tempo limite e *gap* reportado.
   - A solução é conferida por `evaluation.evaluate`.
3. `engine/subinstance.py`: sorteia subinstâncias de n candidatas (8 a 15) de uma instância real.
4. CLI `--metodo milp`. Endpoint `POST /api/planos/{id}/comparar/` (guloso × ALNS × MILP) e, se houver tempo, a tela 4 do Apêndice F.
5. Testes: em `n ≤ 7`, o MILP bate com a força bruta.

**Pronto quando:** os testes passam e, em subinstâncias de 10 candidatas de `bomjesus`, o MILP fecha em tempo razoável. Fica impresso o *gap* da ALNS em relação a ele.

**Notas (implementação):**
- **Solver: HiGHS direto (`highspy`), sem PuLP.**
  - O PuLP 4.0 mudou a API, e o 2.9 não passa solução inicial ao HiGHS.
  - O `highspy` modela, aceita solução inicial (`setSolution`) e informa o *gap*.
  - O objetivo leva a constante β·Σ penalidades como *offset*, para o *gap* ser relativo ao objetivo verdadeiro. A tolerância é 10⁻⁶.
- **Solução inicial:** o MILP parte da rota gulosa (ou de `initial`), então nunca devolve nada pior. A rota extraída é reavaliada por `evaluation.evaluate`.
- **Testes:** em 16 instâncias aleatórias de 6–7 candidatas, o MILP bate com a força bruta. Em 9 candidatas, guloso e ALNS nunca ficam abaixo do ótimo.
- **`engine/subinstance.py`:** sorteia n candidatas, de forma determinística por semente.
- **Comandos:**
  - `python -m engine.solve <inst> --metodo milp`;
  - `python -m engine.compare <inst> --n 10 --reps 5 [--csv]`, que imprime guloso × ALNS × MILP e os *gaps*.
- **API e tela:**
  - `POST /api/planos/{id}/comparar/` (`{tempo_milp, n?, seed?}`), sem gravar nada;
  - aba "Comparar métodos" na tela do plano (tela 4, versão enxuta): tabela e rota de cada método sobreposta no mapa.
- **Resultados em `bomjesus` (β = 30, γ = 2; ALNS com 5 sementes × 2 s):**

  | Subinstâncias | MILP | *gap* médio do guloso | *gap* médio da ALNS | ALNS = ótimo |
  |---|---|---|---|---|
  | 10 candidatas (5) | ótimo provado em 5/5, 0,3 s em média | 5,39% | 0,33% | 4/5 (a outra: 1,67%) |
  | 15 candidatas (3) | ótimo provado em 3/3, ≤ 2 s | 5,88% | 0% | 3/3 |

- **Instância inteira (46 candidatas):** em 60 s o MILP não melhora a ALNS (2984,5), e o *gap* provado fica em 59% (limitante 1217,5). O limitante big-M é fraco. Confirma o uso do MILP só como referência em subinstâncias.
- **Achado para o P16:** na subinstância 0 de 10 candidatas, a ALNS ficou 1,67% acima do ótimo, com as mesmas 9 visitas e só a ordem pior. Um operador de realocação (*or-opt*) ou 2-opt entre os blocos pode fechar esse *gap*.

---

### P16: Validação experimental

**Objetivo:** números e gráficos para o texto e a apresentação (§6.8 da proposta).

**Tarefas:**
1. Gerar os cenários: base, aglomerado, alta urgência (`--urgencia 0.15`), alto atraso (`--atraso 3`) e a equipe de 4 ACS.
2. Comando `validar --instancias ... --sementes 10 --milp-n 10`: guloso, ALNS com 10 sementes e MILP nas subinstâncias. Grava um CSV em `backend/data/resultados/` com as métricas do [Apêndice G](#apêndice-g-métricas-de-validação).
3. Calibração preliminar (grade pequena) de β, γ, taxa de destruição, temperatura inicial e resfriamento. Atualizar D7 com os valores escolhidos.
4. Script de gráficos a partir do CSV (matplotlib) para os slides.

**Pronto quando:** o CSV e os gráficos existem para todos os cenários, e um resumo curto dos resultados está em `docs/resultados.md`.

**Notas:**
- Tabelas e gráficos em [docs/resultados/](resultados/) (gerados por `engine.graficos`); resumo em [resultados.md](resultados.md).
- Uma `bomjesus` gerada de novo em 08/10 reproduziu exatamente o objetivo do cenário base (3185,9).

---

### P17: Fechamento do MVP

**Tarefas:**
1. README completo: o que é, como rodar ([Apêndice B](#apêndice-b-docker-e-ambiente)), estrutura e comandos.
2. Passada de limpeza: código morto do solver antigo, avisos do linter, testes rodando do zero.
3. Ensaio do critério de pronto do MVP, partindo de um clone limpo.

**Critério de pronto do MVP:** com `docker compose up -d db`, `migrate`, `gerar_instancia`/`importar_instancia`, `runserver` e `ng serve`, dá para:
- escolher a equipe e a data;
- planejar o dia;
- ver no mapa a rota de cada ACS respeitando urgências, janelas, jornada e teto de graves;
- exportar CSV/GPX;
- abrir o relatório da equipe com a demanda não atendida por microárea.

**Notas (08/10):**
- README com o manual completo: pré-requisitos, variáveis de ambiente, passo a passo do zero, uso das telas, testes e problemas comuns. Variáveis opcionais documentadas no `.env.example`.
- Limpeza: o solver antigo já tinha saído. Faltava `matplotlib` no `requirements.txt` (usado por `engine.graficos`). `ruff check --select F,E9` limpo.
- Ensaio feito numa máquina **sem Docker e sem Node**: venv novo + `requirements.txt`, `fetch.sh`, `engine.generator` (3 min 47 s), `engine.solve --metodo alns --export csv,gpx,geojson` e `engine.compare` funcionam. `pytest tests/engine`: 128 passaram. Os 30 testes que usam banco não rodaram (sem PostgreSQL).
- **Falta:** rodar o critério de pronto acima com `docker compose`, `migrate`, `runserver` e `ng serve`, mais o `pytest` completo e o `ng test`. Também falta abrir um GPX num visualizador (pendência do P07).

---

### P18+: Pós-MVP (só se sobrar tempo, um item por pedido)

- **P18 Urgência surgida no dia:** `engine/dynamic.py` insere a urgência após a visita em andamento e retira as não urgentes de menor penalidade se `H > Tmax` (motivo `retirada_por_urgencia`). Endpoint `POST /api/planos/{id}/urgencia/` e botão na tela do plano.
- **P19 Vários dias seguidos:** "confirmar execução" de um plano atualiza `ultima_visita` dos visitados. A tela permite avançar o dia.
- **P20 Tarefas assíncronas:** fila (Celery/Redis ou `django-q2`) para gerar instâncias pela interface.
- **P21 Autenticação** e perfis (gestor × ACS).

---

## Apêndice A: estrutura de pastas

```
visita-sus/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── requirements-legacy.txt
│   ├── fetch.sh
│   ├── pytest.ini
│   ├── config/                 # settings, urls, wsgi
│   ├── core/                   # app Django: models, serializers, views, services, admin
│   │   └── management/commands/  # gerar_instancia, importar_instancia, validar
│   ├── engine/                 # Python puro, sem Django
│   │   ├── generator.py        # M1
│   │   ├── instance.py         # contrato (Apêndice C)
│   │   ├── evaluation.py       # objetivo e viabilidade
│   │   ├── matrix.py           # M2
│   │   ├── io.py               # leitura dos arquivos do gerador
│   │   ├── preprocess.py       # M3
│   │   ├── greedy.py           # M4 etapa 1
│   │   ├── alns.py             # M4 etapa 2
│   │   ├── milp.py             # M4 etapa 3
│   │   ├── subinstance.py
│   │   ├── export.py           # CSV / GPX / GeoJSON
│   │   └── solve.py            # CLI
│   ├── legacy/                 # data_generator.ipynb
│   ├── tests/
│   │   ├── engine/
│   │   └── fixtures/
│   └── data/                   # gitignored: IBGE, cache osmnx, instâncias, resultados
├── frontend/
└── docs/
```

## Apêndice B: docker e ambiente

`docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:17
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-visitasus}
      POSTGRES_USER: ${POSTGRES_USER:-visitasus}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-visitasus}
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER:-visitasus}"]
      interval: 5s
      retries: 10
volumes:
  pgdata:
```

`.env.example`: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST=localhost`, `POSTGRES_PORT=5432`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=true`, `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`, `CORS_ALLOWED_ORIGINS=http://localhost:4200`.

Como rodar (alvo):

```sh
cp .env.example .env
docker compose up -d db

cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
./fetch.sh
.venv/bin/python manage.py migrate
.venv/bin/python manage.py gerar_instancia --ubs=-30.0431944,-51.1563369 --name bomjesus
.venv/bin/python manage.py runserver

cd ../frontend
npm install
npx ng serve        # http://localhost:4200
```

## Apêndice C: contrato do `engine`

Implementado no P03 em [backend/engine/instance.py](../backend/engine/instance.py) (estruturas) e [backend/engine/evaluation.py](../backend/engine/evaluation.py) (avaliação). Resumo:

```python
@dataclass
class Visit:                     # índice 0 = UBS (id = -1, P = 0)
    id: int; node: int
    s: float; w: float; P: int; d: int
    tw: tuple[float, float]      # janela de início [a, b] em min desde o início da jornada
    urgent: bool = False; grave: bool = False
    penalty -> float             # w·(d+1)/P; 0 para a UBS
    overdue -> bool              # d + 1 > P (mesmo critério do gerador)

@dataclass
class Instance:                  # 1 ACS × 1 dia: UBS + candidatas já pré-processadas
    visits: list[Visit]; t: np.ndarray   # t[i, j] em min, indexada como visits
    T: float = 360; Tmax: float = 420; K: int = 3
    n, candidates (1..n-1), urgent

@dataclass
class Params:  beta=30, gamma=2, n_candidatas=40, iterations=1000, time_limit_s=5,
               seeds=[0..4], destroy_min=0.10, destroy_max=0.40, t_start=50, cooling=0.995

@dataclass
class Stop:       visit, arrival, start, end, walk_from_prev, reason   # urgencia | atraso | risco | rotina
@dataclass
class Violation:  kind, visit=None, amount=0.0
@dataclass
class Solution:   route, stops, unvisited: list[(índice, motivo)], walk, residual_penalty, overtime,
                  objective, H, method, seed=None, runtime_s=0, seeds_stats=None, gap=None,
                  violations=[]; feasible -> bool; to_dict()
```

**Convenções:**
- A `Instance` contém só a UBS e as candidatas. Os descartes do pré-processamento (`inviavel`, `urgencia_excedente`) ficam fora dela e são reportados à parte (P04). Por isso, **toda urgente da `Instance` é obrigatória**.
- O cronograma começa em 0 na UBS. Em cada parada, chegada = fim anterior + caminhada, e início = max(chegada, a). `H` inclui as esperas.
- **Violações** (`evaluation.violations`):
  - `janela`: início > b;
  - `jornada`: H > Tmax;
  - `teto_graves`: graves > max(K, graves urgentes), conforme D6;
  - `urgente_ausente`;
  - `urgencia_fora_de_ordem`.
- Rota mal formada (sem UBS nas pontas, visita repetida, índice inválido) é erro de programação e levanta `ValueError`. Não é violação.
- **Motivo de visita feita:** urgência > atraso > risco (w ≥ 3) > rotina.
- **Motivos de não atendimento:** `inviavel`, `urgencia_excedente`, `nao_coube` (padrão), `teto_graves`, `retirada_por_urgencia` (pós-MVP).

**Funções:**
- avaliação: `schedule(inst, route)`, `evaluate(inst, params, route) -> Evaluation`, `is_feasible(inst, route)`, `build_solution(inst, params, route, method, ...) -> Solution`;
- solvers (passos seguintes): `greedy.solve(inst, params) -> Solution`, `alns.solve(inst, params, initial=None) -> Solution`, `alns.solve_multi_seed(inst, params) -> Solution`, `milp.solve(inst, params, time_limit_s=None, initial=None) -> Solution` (HiGHS; `gap` = gap provado pelo solver).

## Apêndice D: modelos Django

Implementados no P08 em [backend/core/models.py](../backend/core/models.py).

| Modelo | Campos principais |
|---|---|
| `Ubs` | `nome`, `lat`, `lon` (única por coordenada) |
| `Equipe` | `nome`, `ubs` (FK; nome único por UBS) |
| `Microarea` | `equipe` (FK), `nome` (único = nome da instância), `setores`, `bairros`, `poligono` (GeoJSON), `area_km2`, `moradores_censo`, `domicilios_censo`, `instancia_dir`, `ubs_node`, `meta` |
| `Agente` | `microarea` (1:1), `nome`, `hora_inicio` (08:00), `jornada_min` (360), `jornada_max_min` (420), `velocidade_m_min` (75), `teto_graves` (3) |
| `Domicilio` | `microarea` (FK), `codigo` (linha do gpkg; único por microárea), `node`, `lat`, `lon`, `edificacao`, `n_moradores`, `condicao`, `peso` (w), `intervalo_max_dias` (P), `duracao_min` (s), `ultima_visita`, `tw_inicio`, `tw_fim`, `urgente`, `grave` |
| `Plano` | `agente` (FK), `data`, `metodo` (guloso/alns/milp), `params`, `status` (viavel/com_violacoes), `violacoes`, `hora_inicio`, `objetivo`, `caminhada_min`, `penalidade_residual`, `excesso_min`, `retorno_min` (H), `n_candidatas`, `n_fora_candidatas`, `runtime_s`, `seed`, `seeds_stats`, `gap`, `rota_geojson`, `criado_em` |
| `ItemRoteiro` | `plano` (FK), `ordem`, `domicilio` (FK, PROTECT), `chegada_min`, `inicio_min`, `fim_min`, `caminhada_min`, `motivo` |
| `NaoAtendida` | `plano` (FK), `domicilio` (FK, PROTECT), `motivo`, `penalidade`, `dias_sem_visita`, `atraso_dias` (max(0, d − P)) |

## Apêndice E: API

| Passo | Método | Rota | Descrição |
|---|---|---|---|
| P02 | GET | `/api/health/` | Saúde do serviço e do banco |
| P09 | GET | `/api/microareas/{id}/` | Dados e polígono (GeoJSON) |
| P09 | GET | `/api/microareas/{id}/domicilios/?data=` | FeatureCollection com atributos, penalidade e atraso para a data |
| P09 | GET | `/api/microareas/{id}/malha/` | Arestas da malha a pé (GeoJSON) |
| P09 | GET/PATCH | `/api/agentes/{id}/` | Parâmetros do ACS |
| P09 | GET | `/api/planos/?agente=&microarea=&data=` | Lista resumida dos planos |
| P09 | POST | `/api/planos/` | `{agente, data, metodo, params?}` → executa e devolve o plano |
| P09 | GET/DELETE | `/api/planos/{id}/` | Plano completo / apagar |
| P09 | GET | `/api/planos/{id}/itinerario.csv` | CSV |
| P09 | GET | `/api/planos/{id}/itinerario.gpx` | GPX |
| P10 | GET | `/api/equipes/`, `/api/equipes/{id}/` | Equipes, UBS, microáreas e agentes |
| P10 | POST | `/api/equipes/{id}/planejar/` | `{data, metodo, params?}` → todos os ACS |
| P10 | GET | `/api/equipes/{id}/relatorio/?data=` | Relatório por microárea |
| pós-MVP | GET | `/api/equipes/{id}/relatorio.csv?data=` | Relatório em CSV (uma linha por microárea + total) |
| P15 | POST | `/api/planos/{id}/comparar/` | Guloso × ALNS × MILP |
| P18 | POST | `/api/planos/{id}/urgencia/` | `{domicilio, apos_ordem}` |

`GET /api/planos/{id}/` (implementado no P09; valores ilustrativos):

```json
{
  "id": 1, "agente": {"id": 1, "nome": "ACS bomjesus"}, "microarea": 1, "data": "2026-10-09",
  "metodo": "alns", "status": "viavel", "violacoes": [], "hora_inicio": "08:00:00",
  "params": {"beta": 30, "gamma": 2, "n_candidatas": 40, "iterations": 1000, "time_limit_s": 5, "seeds": [0,1,2,3,4],
             "acs": {"T": 360, "Tmax": 420, "K": 3, "velocidade_m_min": 75}, "...": "..."},
  "metricas": {
    "objetivo": 3167.8, "caminhada_min": 42.1, "penalidade_residual": 100.4, "penalidade_residual_min": 3011.4,
    "excesso_min": 57.1, "H": 417.1, "retorno": "14:57", "jornada_min": 360, "jornada_max_min": 420, "teto_graves": 3,
    "visitas": 19, "candidatas": 46, "fora_das_candidatas": 393, "urgentes_atendidas": 6, "graves": 3,
    "nao_atendidas": 27, "runtime_s": 10.5, "seed": 0, "gap": null,
    "seeds_stats": {"sementes": [0,1,2,3,4], "objetivos": ["..."], "media": 3172.5, "desvio": 5.7, "melhor": 3167.8,
                    "pior": 3178.0, "tempos_s": ["..."]}
  },
  "ubs": {"id": 1, "nome": "UBS Bom Jesus", "lat": -30.0431944, "lon": -51.1563369},
  "itens": [
    {"ordem": 1, "domicilio": 71, "codigo": 71, "lat": -30.0418, "lon": -51.1540, "condicao": "acamado",
     "motivo": "urgencia", "w": 4, "urgente": true, "grave": true, "dias_sem_visita": 10, "P": 15,
     "chegada": "08:05", "inicio": "08:05", "fim": "08:35", "espera_min": 0, "caminhada_min": 5.7, "duracao_min": 30}
  ],
  "nao_atendidas": [
    {"domicilio": 260, "codigo": 260, "lat": -30.0440, "lon": -51.1553, "condicao": "tuberculose",
     "motivo": "teto_graves", "w": 5, "urgente": false, "grave": true, "penalidade": 6.43, "dias_sem_visita": 8,
     "atraso_dias": 1}
  ],
  "rota": {"type": "LineString", "coordinates": [[-51.1564, -30.0431], "..."]},
  "links": {"csv": "http://localhost:8000/api/planos/1/itinerario.csv",
            "gpx": "http://localhost:8000/api/planos/1/itinerario.gpx"},
  "criado_em": "2026-10-08T16:40:00-03:00"
}
```

- `nao_atendidas` vem ordenada por penalidade decrescente.
- `domicilio` é o id no banco; `codigo` é a linha na instância.
- `GET /api/microareas/{id}/domicilios/?data=` devolve uma FeatureCollection de pontos. As propriedades são `id`, `codigo`, `condicao`, `w`, `P`, `duracao_min`, `ultima_visita`, `dias_sem_visita`, `penalidade`, `atrasado`, `atraso_dias`, `urgente`, `grave`, `tw_inicio`, `tw_fim`, `n_moradores` e `node`.

**Relatório da equipe** (`GET /api/equipes/{id}/relatorio/?data=`, implementado no P10):

```json
{
  "equipe": {"id": 1, "nome": "eSF Bom Jesus"}, "ubs": {"id": 1, "nome": "UBS Bom Jesus", "lat": -30.04, "lon": -51.15},
  "data": "2026-10-09", "limiares": {"excesso_min": 30.0, "fracao_atrasados_fora": 0.25},
  "linhas": [
    {"microarea": {"id": 1, "nome": "bomjesus"}, "agente": {"id": 1, "nome": "ACS bomjesus"},
     "plano": {"id": 2, "metodo": "alns", "status": "viavel"}, "sem_plano": false,
     "domicilios": 439, "atrasados": 136, "candidatas": 46, "planejadas": 19, "nao_atendidas": 27,
     "nao_atendidas_por_motivo": {"teto_graves": 11, "nao_coube": 16}, "fora_das_candidatas": 393,
     "atrasados_fora": 122, "urgentes_fora": 0, "penalidade_residual": 100.4, "penalidade_residual_min": 3011.4,
     "caminhada_min": 42.1, "jornada_usada_min": 417.1, "jornada_min": 360, "jornada_max_min": 420,
     "excesso_min": 57.1, "retorno": "14:57",
     "alerta_sobrecarga": true, "motivos_alerta": ["excesso de jornada de 57 min", "122 de 439 domicílios atrasados sem visita"]}
  ],
  "total": {"domicilios": 1340, "atrasados": 451, "candidatas": 103, "planejadas": 38, "nao_atendidas": 65,
            "nao_atendidas_por_motivo": {"teto_graves": 37, "nao_coube": 28}, "fora_das_candidatas": 1237,
            "atrasados_fora": 428, "urgentes_fora": 0, "penalidade_residual_min": 9226.3, "caminhada_min": 88.0,
            "jornada_usada_min": 817.8, "excesso_min": 97.8, "microareas": 2, "com_plano": 2, "sem_plano": 0, "alertas": 2}
}
```

Campos acrescentados depois do P10, para a gestão (a penalidade em minutos equivalentes virou detalhe técnico):
- **linha:** `prioritarios` (urgentes ou atrasados), `prioritarios_fora`, `atrasados_visitados`, `em_dia_sem_visita`
  (visitados + atrasados sem visita + em dia sem visita = domicílios), `cobertura_atrasados` (fração dos atrasados
  visitados; `null` sem atrasados), `dias_atraso_fora` (Σ max(0, d − P) dos atrasados sem visita), `situacao`
  (`ok` | `atencao` | `sobrecarga` | `sem_plano`) e `resumo_situacao` (frase curta). Em `atencao`: sem alerta, mas
  com hora extra ou com atrasados sem visita acima de metade do limiar;
- **total:** os mesmos somatórios, mais `acs_com_hora_extra`, `excesso_max_min`, `caminhada_media_min` e
  `cobertura_atrasados`. O `excesso_min` e o `caminhada_min` somados continuam no total, mas a tela mostra os novos;
- **raiz:** `resumo`, frase para o topo do relatório (quantas microáreas dão conta do dia, quais precisam de reforço
  e por quê, cobertura dos atrasados, microáreas sem plano).

`POST /api/equipes/{id}/planejar/` recebe `{data, metodo, params?}` e devolve `{equipe, data, metodo, planos: [plano resumido, …]}`. `GET /api/equipes/` e `/api/equipes/{id}/` trazem a UBS e as microáreas, cada uma com o nº de domicílios e o agente com seus parâmetros.

## Apêndice F: telas

0. **Início** (`/`): um card por equipe com a situação do dia (frase-resumo do relatório, microáreas em sobrecarga) e atalhos para o painel e o relatório.
1. **Painel da equipe** (`/equipes/:id`): "Planejar dia" (uma requisição por ACS, com progresso em cada card). Um card por ACS com selo de situação, visitas, atrasados sem visita, volta à UBS e barra de jornada, com link para o plano. Método e parâmetros ficam em "Opções avançadas".
2. **Plano do ACS** (`/planos/:id`):
   - **mapa:** polígono da microárea, rota com setas no sentido do percurso, marcadores numerados coloridos pelo risco (paleta do `mapa.html`: verde → vinho), borda grossa para urgentes, não atendidas em X, UBS destacada e legenda recolhível com texto; popups em linguagem simples, com a janela em horário real;
   - **lateral:** números do dia, linha do tempo (visitas, caminhadas, esperas, fim da jornada e hora extra), itinerário em linguagem natural ("risco alto", "última visita há 45 dias (máx. 30)", "atrasado 15 dias"); passar o ponteiro numa visita destaca a parada no mapa, clicar centraliza;
   - **conferência:** selos com a regra explicada no tooltip e, se houver, a lista de regras descumpridas por extenso;
   - **detalhes técnicos:** objetivo, penalidade, sementes e comparação de métodos numa aba à parte;
   - **exportação:** CSV e GPX.
3. **Relatório da equipe** (`/equipes/:id/relatorio?data=`): frase-resumo no topo; indicadores (microáreas em sobrecarga, visitas e cobertura dos atrasados, atrasados e urgências sem visita, dias de atraso acumulados, ACS com hora extra); barras empilhadas com a composição dos domicílios de cada microárea (visitados / atrasados sem visita / em dia sem visita) e barras de hora extra (só quando houver); tabela compacta com selo de situação e linha de detalhes expansível; exportação em CSV e impressão/PDF; nota em linguagem simples, com as fórmulas em "Como calculamos".
4. **Comparação de métodos** (opcional, P15): guloso × ALNS × MILP lado a lado, com as rotas sobrepostas.

## Apêndice G: métricas de validação

Por instância e por método:
- caminhada (min);
- urgências atendidas e sua posição no roteiro;
- penalidade residual;
- atrasados deixados de fora;
- jornada usada e excesso;
- número de visitas;
- tempo de execução;
- *gap* em relação ao MILP (subinstâncias);
- objetivo melhor, médio e desvio entre sementes.

Uma linha do CSV por (instância, método, semente).
