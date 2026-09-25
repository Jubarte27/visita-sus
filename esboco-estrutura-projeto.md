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

1. Modelar o problema com elementos de OPTWVP e HHCRSP, dividido por microárea, com pré-processamento de viabilidade temporal e de limites de jornada.
2. Implementar a arquitetura em dois estágios: construção gulosa, depois ALNS.
3. Definir uma função objetivo multicritério, normalizada em minutos, agregando o tempo de caminhada, o equilíbrio de jornada e a penalidade proporcional aos dias de atraso desde a última visita.
4. Garantir a precedência de urgência e teto de casos por agente.
5. Integrar uma matriz de distâncias em perfil pedestre, usando OpenRouteService ou OSRM, com cache local.
6. Validar o modelo, com múltiplas sementes, comparando com uma heurística gulosa e com o planejamento manual, além de usar Programação Linear Inteira Mista (MILP) para casos pequenos.
7. Construir um dashboard em Leaflet/OSM, com exportação de itinerários e relatório de demanda não atendida e desequilíbrio entre microáreas.

## 5. Revisão de Literatura e Soluções de Mercado


### 5.1 Fundamentação teórica

O **HHCRSP** estende o roteamento com janelas de tempo ao combinar atribuição de visitas a profissionais, sequenciamento e restrições de atendimento e jornada. O **OPTWVP** modela 1 profissional em sua área específica e com um orçamento de tempo, além de diferentes pesos para diferentes pacientes. Essa estrutura fundamenta o projeto, embora os trabalhos estudem principalmente serviços de enfermagem e hospitalização domiciliar, com condições distintas das visitas de ACS.

Para resolver o problema, Neves (2026) combina construção gulosa e **ALNS**: o algoritmo remove e reinsere visitas, adaptando a escolha dos operadores conforme seu desempenho. Özsakallı (2023) também emprega ALNS, com operadores próprios para transporte compartilhado. Esses trabalhos sustentam a arquitetura proposta; o modelo **MILP** será usado como referência em instâncias pequenas. A vantagem das heurísticas depende da formulação e dos dados: Abdolhamidi e Lurkin (2026) obtêm resultados competitivos com MILP reforçado por pré-processamento, portanto não cabe descartar métodos exatos de forma geral.

Na função objetivo, Trautsamwieser e Hirsch (2011) agregam critérios em uma escala temporal comum, fundamentando a conversão das penalidades do projeto para minutos equivalentes. Para o equilíbrio de carga, Cattafi et al. (2015) mostram que minimizar desvios entre jornadas pode induzir deslocamentos desnecessários para igualá-las. Isso favorece o critério de minimizar a maior jornada, avaliado em conjunto com o tempo total de caminhada.

### 5.2 Trabalhos relacionados

A tabela compara objetivo, método, resultados e limites de aplicação ao projeto.

| Trabalho | Objetivo e método | Resultados reportados | Relação com a proposta e limitações |
|---|---|---|---|
| **Trautsamwieser e Hirsch (2011)** | Planejar visitas diárias com jornada, qualificações e preferências; MILP e busca em vizinhança variável (VNS). | Redução de cerca de **45% no tempo de viagem** frente a um plano real da Cruz Vermelha Austríaca. | Fundamenta o objetivo multicritério e a comparação com planejamento manual. O ganho observado não pode ser presumido para microáreas percorridas a pé. |
| **Cattafi et al. (2015)** | Equilibrar carga e manter o vínculo paciente–enfermeiro; programação por restrições e busca em grandes vizinhanças (LNS). | No serviço de Ferrara, melhora a carga máxima e a continuidade do cuidado frente ao planejamento manual por zonas, que já apresentava bons tempos de viagem. | É o caso mais próximo da divisão territorial do projeto. Mostra ganhos além da distância, mas permite decisões de atribuição que podem ser limitadas pelas microáreas dos ACS. |
| **Özsakallı (2023)** | Planejar cuidadores em veículos compartilhados, com desembarque e recolhimento; MILP, heurística construtiva e ALNS. | A política de desembarque/recolhimento reduz em até **25% o tempo total de fluxo**, comparada ao compartilhamento sem essa política; apresenta um sistema de apoio à decisão. | Sustenta ALNS e a separação entre dados, otimização e visualização. A política de transporte e seus ganhos não se transferem diretamente à caminhada. |
| **Yu, Guan e Zhong (2024)** | Integrar escolha de clínicas, modalidade de atendimento e rotas em uma rede de telessaúde; heurística em dois níveis com geração de colunas. | Obtém soluções próximas ou superiores às melhores encontradas pelo Gurobi no tempo limite, com execução de aproximadamente nove minutos nas instâncias maiores. | Amplia a análise para acesso ao cuidado e demanda no mesmo dia. Sua regra de inserção depende das hipóteses da rede híbrida e precisa ser reavaliada para ACS. |
| **Abdolhamidi e Lurkin (2026)** | Integrar continuidade, estabilidade de horários, pausas e visitas sincronizadas; MILP, Hexaly e heurísticas. | Em dados operacionais suíços, o MILP reforçado apresenta desvio mediano de **0,4% do melhor valor conhecido** nas 21 instâncias de comparação. Aumentar a prioridade de cobertura não elimina o déficit de capacidade. | Fundamenta pré-processamento, análise de compromissos e reporte de demanda não atendida. Estabilidade de horário não equivale a intervalo entre visitas. É um **preprint sem revisão por pares**. |
| **Neves (2026)** | Planejar hospitalização domiciliar com múltiplas bases e precedência de urgências; construção gulosa, ALNS e MILP. | A ALNS produz soluções próximas às referências do MILP, com menor tempo nos casos maiores; apresenta protótipo com matriz viária via OpenRouteService. | É a referência mais direta para a arquitetura e as regras de prioridade. O contexto é hospitalar, com equipes médicas e de enfermagem, e não acompanhamento territorial por ACS. |

Os resultados usam métricas, dados e linhas de base diferentes; não formam um ranking de algoritmos. Nos trabalhos recentes, o avanço está na integração de restrições assistenciais e operacionais, além da redução do deslocamento. A proposta aproveita essa direção, mas depende de validação própria no contexto da APS.

### 5.3 Estado da técnica e soluções de mercado

Na operação do SUS, o **e-SUS Território** oferece registro e histórico de visitas individuais e familiares, integrado ao prontuário da APS. O capítulo consultado documenta apoio ao acompanhamento territorial, mas não descreve otimização conjunta de rotas, jornadas e prioridades. A ferramenta proposta pode complementar esse processo com planejamento computacional. Fonte: [Ministério da Saúde — Visita Domiciliar e Territorial](https://sisaps.saude.gov.br/sistemas/esusaps/docs/manual/TERRITORIO/territorio_04/).

No mercado, a API **Timefold Field Service Routing** documenta atribuição e roteirização de cuidadores, considerando aspectos como qualificações, janelas de atendimento e continuidade do cuidado. Isso mostra que parte das restrições estudadas na literatura já aparece em produtos comerciais. A documentação, porém, não comprova desempenho equivalente ao dos estudos nem adequação à combinação específica de microáreas, caminhada e periodicidade das visitas de ACS. Fonte: [Timefold — Use case guide](https://docs.timefold.ai/field-service-routing/latest/user-guide/use-cases). Documentações consultadas em 24/09/2026.

### 5.4 Lacuna e posicionamento do projeto

Nenhum dos seis trabalhos aborda especificamente ACS na APS brasileira. Além disso, o conjunto não trata o atraso em relação ao intervalo máximo entre visitas como critério: frequência previamente definida e estabilidade do horário de atendimento são conceitos distintos da decisão sobre quando revisitar um usuário.

A contribuição pretendida é adaptar métodos existentes para reunir **rotas a pé, prioridade clínica, atraso entre visitas e diagnóstico de sobrecarga por microárea**. Com territórios fixos, o balanceamento deve respeitar as atribuições permitidas; diferenças que não puderem ser resolvidas pelo planejamento serão reportadas à gestão. A avaliação comparará a construção gulosa, a ALNS e, quando disponível, o plano manual, medindo deslocamento, atrasos, carga e demanda não atendida. Os percentuais dos estudos serão referências de comparação, não metas presumidas para o SUS.

### 5.5 Referências científicas

- ABDOLHAMIDI, D.; LURKIN, V. **An Integrated Optimization Model for Home Healthcare Routing and Scheduling with Synchronization, Break Scheduling, and Temporal Stability**. Preprint, 2026. [Texto consultado](artigos/abdolhamidi.pdf).
- CATTAFI, M. et al. **An application of constraint solving for home health care**. AI Communications, v. 28, n. 2, p. 215–237, 2015. [Texto consultado](artigos/cattafi.pdf).
- NEVES, M. E. F. **A Metaheuristic Approach to Routing and Scheduling Hospital-at-Home Visits**. Dissertação de mestrado — Louvain School of Management e Instituto Superior Técnico, 2026. [Texto consultado](artigos/neves.pdf).
- ÖZSAKALLI, G. **Home Healthcare Scheduling and Routing Problems**. Tese de doutorado — Yaşar University, 2023. [Texto consultado](artigos/ozsakalli.pdf).
- TRAUTSAMWIESER, A.; HIRSCH, P. **Optimization of daily scheduling for home health care services**. Journal of Applied Operational Research, v. 3, n. 3, p. 124–136, 2011. [Texto consultado](artigos/trautsamwieser.pdf).
- YU, T.; GUAN, Y.; ZHONG, X. **Visiting nurses assignment and routing for decentralized telehealth service networks**. Annals of Operations Research, v. 341, p. 1191–1221, 2024. [Texto consultado](artigos/yu.pdf).
