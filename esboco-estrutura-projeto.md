## 1. Resumo e Palavras-chave

O projeto prevê a criação de uma ferramenta computacional para ajudar Agentes Comunitários de Saúde (ACS) a planejar suas visitas domiciliares na Atenção Primária à Saúde (APS) do SUS.

Hoje o planejamento é manual com divisão por microárea. Contar apenas com a lógica informal pode facilmente gerar desequilíbrio de carga entre agentes, entre outras situações subótimas.

A proposta é modelar o problema como uma variante do *Problema de Roteamento de Veículos com Janelas de Tempo* (VRPTW) chamada *Problema de Roteamento e Agendamento de Cuidados de Saúde ao Domicílio* (HHCRSP). A solução se dá em 2 etapas:

1. construção rápida e gulosa,
2. algoritmo de *Busca Adaptativa em Grandes Vizinhanças* (ALNS) para refinar a solução.

As distâncias são calculadas em perfil pedestre, e um dashboard permite conferir as rotas.

Palavras-chave: Roteirização em Saúde Domiciliar; HHCRSP; Atenção Primária à Saúde; Otimização de Rotas a Pé; ALNS.

## 2. Introdução e Contextualização

O contexto é a rede de visitas domiciliares da APS/SUS. Essas visitas são organizadas por microárea e feitas a pé pelo ACS.

O planejamento manual já consegue bom tempo de deslocamento ou boa distância percorrida. Porém, por ser um problema com muitos fatores, as rotas podem ignorar medidas como balanceamento de carga, urgência ou intervalo máximo entre visitas. 

A revisão de literatura reuniu 6 trabalhos publicados entre 2011 e 2026: *Trautsamwieser & Hirsch* (2011), *Cattafi et al.* (2015), *Yu, Guan & Zhong* (2024), *Abdolhamidi & Lurkin* (2026), *Özsakallı* (2023) e *Neves* (2026). Nenhum desses trabalhos trata do contexto da APS pública brasileira ou do ACS especificamente. Ainda assim, a estrutura do problema é a mesma da literatura internacional de home health care, o que justifica o seu uso como base teórica do projeto.

## 3. Justificativa

Reduzir o tempo de deslocamento não é o principal ganho esperado. A microárea do ACS já é uma divisão territorial contígua, parecida com o caso de Cattafi et al. (2015), no qual a divisão manual já produzia bons tempos de viagem, embora falhasse em equidade de carga e continuidade do cuidado.

O ganho esperado está em garantir que urgências sejam atendidas a tempo, disponibilizar dados para justificar a necessidade do aumento das equipes, equilibrar a carga entre agentes e priorizar corretamente os casos clínicos.

Solucionadores exatos como CPLEX e Xpress demoram horas para conseguir resolver instâncias médias/grandes. Isso torna inviável atingir a solução ótima em tempo para uso no cotidiano, mas abre espaço para soluções heurísticas que atinjam resultados mais próximos do ótimo.

## 4. Objetivos

**Objetivo geral:** modelar e implementar um protótipo de roteirização e escalonamento diário a pé para ACS na APS/SUS. O protótipo deve considerar urgência clínica, intervalo máximo entre visitas e balanceamento de carga, além de ser validado contra uma linha de base gulosa ou manual.

**Objetivos específicos:**

1. Modelar o problema como HHCRSP, dividido por microárea, com pré-processamento de viabilidade temporal e de limites de jornada.
2. Implementar a arquitetura em dois estágios: construção gulosa, depois ALNS.
3. Definir uma função objetivo multicritério, normalizada em minutos, agregando o tempo de caminhada, o equilíbrio de jornada e a penalidade proporcional aos dias de atraso desde a última visita.
4. Garantir a precedência de urgência e teto de casos por agente.
5. Integrar uma matriz de distâncias em perfil pedestre, usando OpenRouteService ou OSRM, com cache local.
6. Validar o modelo, com múltiplas sementes, comparando com uma heurística gulosa e com o planejamento manual, além de usar Programação Linear Inteira Mista (MILP) para casos pequenos.
7. Construir um dashboard em Leaflet/OSM, com exportação de itinerários e relatório de demanda não atendida e desequilíbrio entre microáreas.