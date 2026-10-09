# visita-sus
Objetivo definido em [docs/Proposta.pdf](docs/Proposta.pdf) (texto em [docs/estrutura-projeto.md](docs/estrutura-projeto.md)). O roteiro de implementação do MVP está em [docs/passos-implementacao.md](docs/passos-implementacao.md).

## Estrutura

- `backend/engine/`: Python puro, sem Django. Contém o gerador de instâncias (`generator.py`), a matriz de tempos (`matrix.py`), o pré-processamento (`preprocess.py`, `io.py`), a avaliação (`evaluation.py`), a construção gulosa (`greedy.py`), a ALNS (`alns.py`), o MILP (`milp.py`), as exportações (`export.py`), o comando `solve.py` e a validação (`validate.py`, `calibrate.py`, `graficos.py`).
- `backend/core/`: app Django com modelos, API REST, admin, planejamento da equipe, relatório e os comandos `gerar_instancia`, `importar_instancia` e `validar`. As configurações ficam em `backend/config/`.
- `backend/legacy/`: notebook antigo do gerador (`data_generator.ipynb`).
- `backend/data/`: dados baixados, instâncias geradas e resultados (fora do git).
- `frontend/`: Angular 21 + Material + Leaflet (telas do MVP).
- `docs/`: proposta, revisão de literatura, artigos, apresentações, roteiro de implementação, [resultados da validação](docs/resultados.md) e amostras de instâncias (`docs/data/instances/`, só `meta.json` e `mapa.html`).

## Como rodar (do zero)

### Pré-requisitos

- **Python 3.12** com `venv`. No Ubuntu: `sudo apt install python3-venv`. Alternativa: [uv](https://docs.astral.sh/uv/).
- **Docker** com o plugin `compose`, para o PostgreSQL 17. Para usar um PostgreSQL já instalado, aponte as variáveis `POSTGRES_*` para ele.
- **Node.js 20.19+ ou 22.12+** (exigência do Angular 21). Use o npm 11: o npm 9 do Ubuntu falha neste projeto, e `npx npm@11` resolve.
- **Internet** para baixar a malha do IBGE (`fetch.sh`, ~55 MB, uma vez) e para gerar instâncias (OpenStreetMap via Overpass, 3 a 5 min por instância). Depois disso, tudo roda offline.

### Variáveis de ambiente

Copie `.env.example` para `.env` **na raiz do repositório**. O mesmo arquivo é lido pelo `docker compose` e pelo Django. Para desenvolvimento local, os valores do exemplo funcionam sem mudanças. Variáveis definidas no ambiente do processo têm precedência sobre o `.env`.

| variável | padrão | para que serve |
|---|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `visitasus` | banco, usuário e senha. O `docker compose` cria o banco com eles na primeira subida. |
| `POSTGRES_HOST`, `POSTGRES_PORT` | `localhost`, `5432` | onde o Django encontra o banco. Se a porta 5432 já estiver em uso, troque aqui e no `ports` do `docker-compose.yml`. |
| `DJANGO_SECRET_KEY` | (sem padrão fora do DEBUG) | chave de criptografia do Django. Obrigatória com `DJANGO_DEBUG=false`. Gere uma com `python -c "import secrets; print(secrets.token_urlsafe(50))"`. |
| `DJANGO_DEBUG` | `false` (`true` no exemplo) | modo de desenvolvimento: páginas de erro detalhadas e navegador da API. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | nomes pelos quais o backend aceita ser acessado. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:4200` | origens do frontend autorizadas a chamar a API. Com o `ng serve` e o proxy, só importa se o frontend for servido de outro endereço. |
| `INSTANCES_DIR` (opcional) | `backend/data/instances` | pasta das instâncias (grafo, matriz, arquivos do gerador). |
| `PLANEJAMENTO_PARALELO` (opcional) | `true` | planeja os ACS de uma equipe em processos paralelos. Use `false` para depurar. |
| `ALERTA_EXCESSO_MIN`, `ALERTA_FRACAO_ATRASADOS` (opcionais) | `30`, `0.25` | limiares do alerta de sobrecarga no relatório da equipe: excesso de jornada (min) e fração de domicílios atrasados sem visita. |

### Passo a passo

```sh
# 1. ambiente e banco (na raiz do repositório)
cp .env.example .env
docker compose up -d db                 # PostgreSQL 17; `docker compose ps` deve mostrar "healthy"

# 2. backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./fetch.sh                              # malha de setores do Censo 2022 em data/ (uma vez)
.venv/bin/python manage.py migrate

# 3. dados: gera a instância (rede, alguns minutos) e importa no banco
.venv/bin/python manage.py gerar_instancia --ubs=-30.0431944,-51.1563369 --name bomjesus
# opcional, equipe com 4 ACS:
.venv/bin/python manage.py gerar_instancia --ubs=-30.0431944,-51.1563369 --name bomjesus_eq4 --acs 4
# se a instância já foi gerada com `python -m engine.generator`, basta importar:
# .venv/bin/python manage.py importar_instancia data/instances/bomjesus

# 4. backend no ar (deixe este terminal aberto)
.venv/bin/python manage.py runserver    # API em http://localhost:8000/api/ (teste: /api/health/)

# 5. frontend, em outro terminal
cd frontend
npx npm@11 install
npx ng serve                            # http://localhost:4200 (o /api é encaminhado ao Django)
```

Para o admin do Django (`http://localhost:8000/admin/`), crie um usuário com `.venv/bin/python manage.py createsuperuser`.

### Usando a aplicação

1. Abra `http://localhost:4200`, escolha a **equipe** (por exemplo, "eSF Bom Jesus"; uma instância de equipe vira "eSF <nome>") e a **data** na barra superior.
2. No **painel da equipe**, escolha o método (ALNS ou guloso) e clique em **Planejar dia**. Cada ACS é planejado em paralelo, em poucos segundos, e aparece um card com visitas, caminhada, jornada e não atendidas.
3. Abra o **plano de um ACS** para ver a rota no mapa, o itinerário com horários e motivos, as visitas não atendidas e os selos de conferência (urgências primeiro, graves ≤ K e a barra de jornada). Os botões **CSV** e **GPX** exportam o itinerário. O GPX abre em apps de mapa e em <https://gpx.studio>.
4. O **relatório da equipe** mostra a demanda não atendida por microárea e destaca as sobrecarregadas.

### Testes

```sh
cd backend
.venv/bin/python -m pytest tests/engine   # só o motor: não precisa de banco nem de rede
.venv/bin/python -m pytest                # tudo: precisa do banco no ar (docker compose up -d db)

cd ../frontend
npx ng test --watch=false
```

### Problemas comuns

- **`OperationalError: connection refused` no `migrate` ou nos testes:** o banco não está no ar. Rode `docker compose up -d db` e confira a porta em `.env`.
- **`ImproperlyConfigured: Set the DJANGO_SECRET_KEY`:** falta o `.env` na raiz, ou `DJANGO_DEBUG=false` está sem chave.
- **`npm install` falha com "edgesOut":** é o npm 9. Use `npx npm@11 install`.
- **`gerar_instancia` demora ou falha com erro HTTP:** o Overpass (OpenStreetMap) está lento ou limitando requisições. Espere e rode de novo: as respostas já baixadas ficam em cache em `backend/data/osmnx_cache/`.
- **O frontend abre sem equipes:** nenhuma instância foi importada (passo 3), ou o `runserver` não está no ar.

## O que fazer

- **Percurso a pé:** sequenciamento diário de visitas sobre malha viária real no perfil pedestre.
- **Urgência e prioridade clínica:** escore ponderado de risco, garantia de precedência no início do turno, teto de casos graves por agente e regra analítica para urgências surgidas no dia.
- **Intervalo máximo:** penalização contínua do atraso em relação à periodicidade clínica de cada usuário.
- **Carga de trabalho:** limite de jornada por agente e reporte de demanda reprimida/desequilíbrio entre microáreas para dimensionamento (sem redistribuir visitas entre agentes).
- **Visualização:** mapa interativo com rotas por ACS e conferência visual de regras clínicas.
- **Reportar Falhas:** Demandas não atendidas, desequilíbrio entre microáreas, etc devem ser reportados a fim de requisito de mais recursos para a área. 

## Como Fazer

- **Modelagem (OPTWVP/HHCRSP):**
  - Eliminar visitas inviáveis (janela de tempo, jornada) antes de otimizar.
  - Um subproblema independente por ACS e por dia, restrito à sua microárea: 10 a 20 visitas a partir da base populacional da eSF. Os resultados de todos os agentes são agregados num relatório por microárea.
  - Função objetivo multicritério normalizada em minutos: deslocamento a pé + penalidades de atraso + sobrecarga de jornada.
  - Testes com cenários extremos (aglomerado, alta urgência, alto atraso)
- **Arquitetura algorítmica em três camadas:**
  1. *Construtiva rápida:* inserção gulosa de menor custo para solução inicial imediata (< 1 s).
  2. *ALNS:* destruição/reparo adaptativo, aceitação por *Simulated Annealing* e sanitização determinística para ordenar urgências.
  3. *MILP:* solucionador em instâncias pequenas para validação do *gap* de otimalidade.
- **Georreferenciamento e dados:** malha de caminhos a pé do OpenStreetMap via osmnx (OpenRouteService/OSRM como alternativa) com cache local da matriz; dados sintéticos/anonimizados (LGPD).
- **Validação experimental:** calibração formal (DoE/Taguchi), múltiplas sementes e comparação contra linhas de base (heurística gulosa e planejamento manual).
- **Dashboard:** visualizador de mapas leve (Leaflet/OSM) com exportação de itinerários em CSV/GPX e informações sobre demandas não atendidas.


## Parâmetros

### Agentes
- jornada máxima diária
- ponto de início e fim (UBS ou residência)
- velocidade de caminhada
- microárea de atuação

### Pacientes
- coordenadas geográficas
- data da última visita
- condição clínica e nível de risco
- intervalo máximo recomendado entre visitas
- duração estimada da visita
- janela de horário de atendimento

### Rotas e território
- vias ou trechos excluídos

### Otimização e pesos
- peso do tempo de deslocamento
- peso da penalidade de atraso
- peso do excesso de jornada
- peso relativo por condição clínica

## Motor pela linha de comando (sem banco)

Comandos a partir de `backend/`:

```sh
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
# sem python3-venv no sistema: uv venv --python 3.12 --seed .venv && uv pip install --python .venv/bin/python -r requirements.txt
./fetch.sh            # malha de setores do Censo 2022 em data/ (--legacy baixa também os dados do notebook)

# microárea ao redor de uma UBS (coordenada lat,lon); padrão: setores vizinhos até 750 moradores
.venv/bin/python -m engine.generator --ubs=-30.0431944,-51.1563369 --name bomjesus
.venv/bin/python -m engine.generator --ubs=-30.0431944,-51.1563369 --name bomjesus_2000 --populacao 2000 --seed 3

# equipe de 4 ACS: área para 4 × 750 moradores, dividida em 4 microáreas contíguas (uma instância, um grafo)
.venv/bin/python -m engine.generator --ubs=-30.0431944,-51.1563369 --name bomjesus_eq4 --acs 4

# resumo da instância após o pré-processamento (calcula e guarda matrix.npz na primeira vez)
.venv/bin/python -m engine.io data/instances/bomjesus [--data AAAA-MM-DD]

# roteiro do dia (guloso ou ALNS com várias sementes); grava data/instances/bomjesus/solucao.json
.venv/bin/python -m engine.solve data/instances/bomjesus --metodo alns [--data AAAA-MM-DD] [--beta 30 --gamma 2]
                                 [--iteracoes 1000 --tempo 5 --sementes 0,1,2,3,4] [--export csv,gpx,geojson]
                                 # --metodo milp: referência exata (HiGHS), só para instâncias pequenas

# guloso × ALNS × MILP em subinstâncias de 10 candidatas (gap da ALNS para o ótimo)
.venv/bin/python -m engine.compare data/instances/bomjesus --n 10 --reps 5 [--csv resultados.csv]
```

A microárea é o setor censitário que contém a UBS mais os setores vizinhos (os mais próximos primeiro) até atingir `--populacao`. O número de domicílios é o do Censo 2022 (V0007), distribuído pelas edificações residenciais do OSM (cada uma comporta área × pavimentos / 80 m² domicílios; casas ficam com 1). A malha a pé e as edificações vêm do OpenStreetMap via Overpass (online, só durante a geração).

Cada instância fica em `backend/data/instances/<nome>/`:

- `graph.graphml`: malha a pé (faixa de 200 m ao redor da microárea); cada domicílio e a UBS são nós, inseridos no ponto da rua em frente à edificação. Arestas têm `length` (m) e `travel_time` (min, a 4,5 km/h).
- `instance.gpkg`: camada `visits` (linha 0 é a UBS; demais são domicílios com `condicao`, `w` peso clínico, `P` intervalo máximo em dias, `d` dias desde a última visita, `s` duração em min, `tw_start`/`tw_end` janela em min desde o início da jornada, `urgente`, `grave`, `penalidade` = w·(d+1)/P, `candidata`, `node`) e camada `microarea` (setores). `profit`/`cost` repetem `penalidade`/`s` (formato do solver antigo, mantido por compatibilidade).
- `candidatas.gpkg`: UBS + candidatas do dia (todas as urgentes + as `--candidatas` de maior penalidade), para conferência; o `engine.solve` recalcula as candidatas para a data do plano.
- `meta.json`: setores, contagens do Censo e do que foi gerado, parâmetros e `data_base` (data até a qual os `d` são contados; `--data-base`, padrão hoje).
- `mapa.html`: mapa interativo (clique nos pontos para ver os domicílios; numa equipe, as microáreas coloridas).
- Equipe (`--acs N`): `visits` ganha a coluna `microarea` (1..N; UBS = 0), `instance.gpkg` ganha a camada `microareas` (polígono de cada uma) e `meta.json` o bloco `equipe` (setores, população, domicílios e urgentes por microárea). A divisão é por setores censitários (crescimento de regiões a partir de sementes afastadas, equilibrando a população) ou, com menos setores que ACS, por k-means nas edificações. `importar_instancia` cria a equipe "eSF <nome>" com N microáreas `<nome>_<k>`; `engine.io`/`engine.solve` aceitam `--microarea k`.
- `matrix.npz`: matriz de tempos a pé (min) entre todos os nós de acesso, criada por `engine.io` na primeira leitura.
- `solucao.json`, e com `--export` também `itinerario.csv`, `itinerario.gpx` (trilha pela malha + paradas numeradas; abre em apps de mapa e em <https://gpx.studio>) e `rota.geojson`: saídas do `engine.solve`.

Os parâmetros clínicos (probabilidade de cada condição, `w`, `P`, `s`) ficam no topo de `backend/engine/generator.py` e são ilustrativos. `--urgencia` e `--atraso` permitem montar os cenários de alta urgência e alto atraso.

## Backend (Django + PostgreSQL)

```sh
cp .env.example .env          # na raiz do repositório
docker compose up -d db       # PostgreSQL 17

cd backend
.venv/bin/python manage.py migrate
.venv/bin/python manage.py importar_instancia data/instances/bomjesus [--equipe "eSF Bom Jesus"] [--data-base AAAA-MM-DD]
.venv/bin/python manage.py gerar_instancia --ubs=-30.0431944,-51.1563369 --name outra   # gera (rede) e importa
.venv/bin/python manage.py createsuperuser   # acesso ao admin em http://localhost:8000/admin/
.venv/bin/python manage.py runserver
.venv/bin/python -m pytest                    # testes (o banco precisa estar no ar)
```

## Frontend (Angular)

```sh
cd frontend
npx npm@11 install     # o npm 9 do Ubuntu falha neste projeto; o npm 11 via npx resolve
npx ng serve           # http://localhost:4200 (com o backend no ar em localhost:8000)
```

Detalhes em [frontend/README.md](frontend/README.md).

## Ferramentas possivelmente úteis

- Gerador de dados fictícios para teste: <https://github.com/afkummer/ovig>
- Resolução de problemas de otimização no geral: <https://developers.google.com/optimization>

### Saúde
- Mapa das Unidades Básicas de Saúde da APS: <https://github.com/ms-deaps/mapas>
  - Mapa interativo: <https://mapas.sus.c3sl.ufpr.br>
  - Artigo que introduz: <https://www.scielosp.org/article/csc/2026.v31n5/e24432025/pt/>
- Mapa de setores censitários (possível placeholder para microáreas): <https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/26565-malhas-de-setores-censitarios-divisoes-intramunicipais.html>

### Mapas
- Mapas open source: <https://www.openstreetmap.org>
  - API para obter os dados: <https://wiki.openstreetmap.org/wiki/Overpass_API>
- Biblioteca em javascript para visualizar mapas: https://leafletjs.com/

### Otimização do percurso
- Motor gerador de rotas usando OpenStreetMap: <https://project-osrm.org/>, <https://openrouteservice.org/>
