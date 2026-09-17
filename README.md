# visita-sus
Objetivo definido em [Proposta.pdf](Proposta.pdf)

## Problema
Nome comumente usado para problemas parecidos: **Home Health Care Routing and Scheduling Problem (HHCRSP)**.

## Requisitos que devem ser contemplados
- Funcionar em tempo razoável para pelo menos 6000 pacientes, que é o dobro do tamanho [estipulado](https://www.gov.br/saude/pt-br/composicao/saps/esf/equipe-saude-da-familia/faq/qual-e-o-parametro-populacional-das-esf) para cada equipe de saúde da família
  - O número real de paciente por região pode ser diferente, utilizar os mapas das APSs e atualizar este valor
    - A maioria das ferramentas suporta bem mais do que isso, fazer um protótipo

## Ferramentas possivelmente úteis

- Gerador de dados fictícios para teste: <https://github.com/afkummer/ovig>
- Resolução de problemas de otimização no geral: <https://developers.google.com/optimization>

### Saúde
- Mapa das Unidades Básicas de Saúde da APS: <https://github.com/ms-deaps/mapas>
  - Mapa interativo: <https://mapas.sus.c3sl.ufpr.br>
  - Artigo que introduz: <https://www.scielosp.org/article/csc/2026.v31n5/e24432025/pt/>
  - Confirmar com o professor se esse mapa corresponde as equipes que são referidas na proposta

### Mapas
- Mapas open source: <https://www.openstreetmap.org>
  - API para obter os dados: <https://wiki.openstreetmap.org/wiki/Overpass_API>
- Biblioteca em javascript para visualizar mapas: https://leafletjs.com/

### Otimização do percurso
- Motor gerador de rotas usando OpenStreetMap: <https://project-osrm.org/>
