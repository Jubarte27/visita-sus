# visita-sus
Objetivo definido em [Proposta.pdf](Proposta.pdf)

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

## Uso

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
./fetch.sh

# microárea ao redor de uma UBS (coordenada lat,lon); padrão: setores vizinhos até 750 moradores
.venv/bin/python src/generator.py --ubs=-30.0431944,-51.1563369 --name bomjesus
.venv/bin/python src/generator.py --ubs=-30.0431944,-51.1563369 --name bomjesus_2000 --populacao 2000 --seed 3

# solver sobre as candidatas do dia
.venv/bin/python src/solver.py data/instances/bomjesus/candidatas.gpkg data/instances/bomjesus/graph.graphml
```

A microárea é o setor censitário que contém a UBS mais os setores vizinhos (os mais próximos primeiro) até atingir `--populacao`. O número de domicílios é o do Censo 2022 (V0007), distribuído pelas edificações residenciais do OSM (cada uma comporta área × pavimentos / 80 m² domicílios; casas ficam com 1). A malha a pé e as edificações vêm do OpenStreetMap via Overpass (online, só durante a geração).

Cada instância fica em `data/instances/<nome>/`:

- `graph.graphml`: malha a pé (faixa de 200 m ao redor da microárea); cada domicílio e a UBS são nós, inseridos no ponto da rua em frente à edificação. Arestas têm `length` (m) e `travel_time` (min, a 4,5 km/h).
- `instance.gpkg`: camada `visits` (linha 0 é a UBS; demais são domicílios com `condicao`, `w` peso clínico, `P` intervalo máximo em dias, `d` dias desde a última visita, `s` duração em min, `tw_start`/`tw_end` janela em min desde o início da jornada, `urgente`, `grave`, `penalidade` = w·(d+1)/P, `candidata`, `node`) e camada `microarea` (setores). `profit`/`cost` repetem `penalidade`/`s` para o `solver.py`.
- `candidatas.gpkg`: UBS + candidatas do dia (todas as urgentes + as `--candidatas` de maior penalidade), entrada do solver.
- `meta.json`: setores, contagens do Censo e do que foi gerado, parâmetros.
- `mapa.html`: mapa interativo (clique nos pontos para ver os domicílios).

Os parâmetros clínicos (probabilidade de cada condição, `w`, `P`, `s`) ficam no topo de `src/generator.py` e são ilustrativos. `--urgencia` e `--atraso` permitem montar os cenários de alta urgência e alto atraso.

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
