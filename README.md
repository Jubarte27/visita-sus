# visita-sus
Objetivo definido em [Proposta.pdf](Proposta.pdf)

## O que fazer

- **Percurso a pé:** sequenciamento diário de visitas sobre malha viária real no perfil pedestre.
- **Urgência e prioridade clínica:** escore ponderado de risco, garantia de precedência no início do turno, teto de casos graves por agente e regra analítica para urgências surgidas no dia.
- **Intervalo máximo:** penalização contínua do atraso em relação à periodicidade clínica de cada usuário.
- **Equilibrar carga:** balanceamento min-max de jornada e reporte de demanda reprimida/desequilíbrio entre microáreas para dimensionamento.
- **Visualização:** mapa interativo com rotas por ACS e conferência visual de regras clínicas.
- **Reportar Falhas:** Demandas não atendidas, desequilíbrio entre microáreas, etc devem ser reportados a fim de requisito de mais recursos para a área. 

## Como Fazer

- **Modelagem (MDVRPTW/HHCRSP):**
  - Eliminar pares (visita, agente) inviáveis antes de otimizar.
  - Decomposição por microárea: subproblemas diários tratáveis de 10 a 20 visitas por ACS a partir da base populacional da eSF.
  - Função objetivo multicritério normalizada em minutos: deslocamento a pé + penalidades de atraso + sobrecarga de jornada.
  - Testes com cenários extremos (aglomerado, alta urgência, alto atraso)
- **Arquitetura algorítmica em três camadas:**
  1. *Construtiva rápida:* inserção gulosa de menor custo para solução inicial imediata (< 1 s).
  2. *ALNS:* destruição/reparo adaptativo, aceitação por *Simulated Annealing* e sanitização determinística para ordenar urgências.
  3. *MILP:* solucionador em instâncias pequenas para validação do *gap* de otimalidade.
- **Georreferenciamento e dados:** OpenRouteService ou OSRM local (perfil pedestre) com cache local da matriz; dados sintéticos/anonimizados (LGPD).
- **Validação experimental:** calibração formal (DoE/Taguchi), múltiplas sementes e comparação contra linhas de base (heurística gulosa e planejamento manual).
- **Dashboard:** visualizador de mapas leve (Leaflet/OSM) com exportação de itinerários em CSV e infromações sobre demandas não atendidas.


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
