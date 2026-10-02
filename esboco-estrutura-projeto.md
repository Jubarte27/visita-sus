## 1. Resumo e Palavras-chave

O projeto prevê a criação de uma ferramenta computacional para ajudar Agentes Comunitários de Saúde (ACS) a planejar suas visitas domiciliares na Atenção Primária à Saúde (APS) do SUS.

Hoje o planejamento é manual com divisão por microárea. Contar apenas com a lógica informal pode facilmente gerar desequilíbrio de carga entre agentes, entre outras situações subótimas.

A proposta é modelar o problema como uma variante do *Problema de Orientação com Janelas de Tempo e Lucros Variáveis* (OPTWVP) com elementos do *Problema de Roteamento e Agendamento de Cuidados de Saúde ao Domicílio* (HHCRSP). A solução se dá em 2 etapas:

1. construção rápida e gulosa,
2. algoritmo de *Busca Adaptativa em Grandes Vizinhanças* (ALNS) para refinar a solução.

As distâncias são calculadas em perfil pedestre, e um dashboard permite conferir as rotas.

Palavras-chave: Roteirização em Saúde Domiciliar; HHCRSP; OPTWVP; Atenção Primária à Saúde; Otimização de Rotas a Pé; ALNS.

## 2. Introdução e Contextualização

O contexto é a rede de visitas domiciliares da APS/SUS. Essas visitas são organizadas por microárea e feitas a pé pelo ACS.

O planejamento manual já consegue bom tempo de deslocamento ou boa distância percorrida. Porém, por ser um problema com muitos fatores, as rotas podem ignorar medidas como balanceamento de carga, urgência ou intervalo máximo entre visitas. 

A revisão de literatura reuniu 6 trabalhos publicados entre 2011 e 2026: *Trautsamwieser & Hirsch* (2011), *Cattafi et al.* (2015), *Yu, Guan & Zhong* (2024), *Abdolhamidi & Lurkin* (2026), *Özsakallı* (2023) e *Neves* (2026). Nenhum desses trabalhos trata do contexto da APS pública brasileira ou do ACS especificamente. Ainda assim, a estrutura do problema é a mesma da literatura internacional de home health care, o que justifica o seu uso como base teórica do projeto.

## 3. Justificativa

Reduzir o tempo de deslocamento não é o principal ganho esperado. A microárea do ACS já é uma divisão territorial contígua, parecida com o caso de Cattafi et al. (2015), no qual a divisão manual já produzia bons tempos de viagem, embora falhasse em equidade de carga e continuidade do cuidado.

O ganho esperado está em garantir que urgências sejam atendidas a tempo, respeitar o limite de jornada de cada agente, priorizar corretamente os casos clínicos e disponibilizar dados que evidenciem o desequilíbrio de carga entre microáreas, justificando a necessidade de aumento das equipes.

Solucionadores exatos como CPLEX e Xpress demoram horas para conseguir resolver instâncias médias/grandes. Isso torna inviável atingir a solução ótima em tempo para uso no cotidiano, mas abre espaço para soluções heurísticas que atinjam resultados mais próximos do ótimo.

## 4. Objetivos

**Objetivo geral:** modelar e implementar um protótipo de roteirização e escalonamento diário a pé para ACS na APS/SUS. O protótipo deve considerar urgência clínica, intervalo máximo entre visitas e limite de jornada do agente, além de ser validado contra uma linha de base gulosa ou manual.

**Objetivos específicos:**

1. Modelar o problema com elementos de OPTWVP e HHCRSP, resolvido de forma independente para cada ACS em sua microárea, com pré-processamento de viabilidade temporal e de limites de jornada.
2. Implementar a arquitetura em dois estágios: construção gulosa, depois ALNS.
3. Definir uma função objetivo multicritério, normalizada em minutos, agregando o tempo de caminhada, o excesso sobre a jornada do agente e a penalidade proporcional aos dias de atraso desde a última visita.
4. Garantir a precedência de urgência e teto de casos por agente.
5. Integrar uma matriz de tempos a pé calculada sobre a malha de caminhos do OpenStreetMap (osmnx), com cache local.
6. Validar o modelo, com múltiplas sementes, comparando com uma heurística gulosa e com o planejamento manual, além de usar Programação Linear Inteira Mista (MILP) para casos pequenos.
7. Construir um dashboard em Leaflet/OSM, com exportação de itinerários e relatório de demanda não atendida e desequilíbrio entre microáreas.

### 4.1 Escopo e delimitação

A unidade de planejamento é **um ACS, em um dia, dentro da sua microárea**. As microáreas são fixas e o vínculo entre o agente e as famílias do seu território faz parte do trabalho na APS; por isso, o sistema não transfere visitas de um agente para outro.

| Está no escopo | Fica fora do escopo |
|---|---|
| Seleção e sequenciamento diário das visitas de cada ACS | Redistribuição de visitas entre agentes ou cobertura de microáreas descobertas |
| Prioridade clínica, urgência e atraso em relação ao intervalo máximo entre visitas | Planejamento de vários dias de uma só vez (cada dia é otimizado com o estado atualizado das visitas) |
| Limite de jornada e teto de casos graves por agente | Redesenho das microáreas |
| Relatório agregado de demanda não atendida e de sobrecarga por microárea | Uso de dados reais de pacientes e integração com o e-SUS Território |
| Dados sintéticos, gerados sobre mapas reais | Aplicativo móvel para uso em campo |

**Coordenação entre planejamentos.** Como as microáreas não se sobrepõem, os planos de agentes diferentes não competem pelas mesmas visitas e podem ser calculados de forma independente (inclusive em paralelo). A coordenação acontece no nível da gestão: depois que todos os planos do dia são calculados, o sistema reúne em um relatório por equipe as visitas que ficaram de fora, os atrasos acumulados e a carga de cada microárea. Esse relatório é o subsídio para a gestão redimensionar as equipes ou rever as microáreas; essa decisão permanece humana.

## 5. Revisão de Literatura e Soluções de Mercado


### 5.1 Fundamentação teórica

O **HHCRSP** estende o roteamento com janelas de tempo ao combinar atribuição de visitas a profissionais, sequenciamento e restrições de atendimento e jornada. O **OPTWVP** modela 1 profissional em sua área específica e com um orçamento de tempo, além de diferentes pesos para diferentes pacientes. Essa estrutura fundamenta o projeto, embora os trabalhos estudem principalmente serviços de enfermagem e hospitalização domiciliar, com condições distintas das visitas de ACS.

Para resolver o problema, Neves (2026) combina construção gulosa e **ALNS**: o algoritmo remove e reinsere visitas, adaptando a escolha dos operadores conforme seu desempenho. Özsakallı (2023) também emprega ALNS, com operadores próprios para transporte compartilhado. Esses trabalhos sustentam a arquitetura proposta; o modelo **MILP** será usado como referência em instâncias pequenas. A vantagem das heurísticas depende da formulação e dos dados: Abdolhamidi e Lurkin (2026) obtêm resultados competitivos com MILP reforçado por pré-processamento, portanto não cabe descartar métodos exatos de forma geral.

Na função objetivo, Trautsamwieser e Hirsch (2011) agregam critérios em uma escala temporal comum, fundamentando a conversão das penalidades do projeto para minutos equivalentes. Para o equilíbrio de carga, Cattafi et al. (2015) mostram que minimizar desvios entre jornadas pode induzir deslocamentos desnecessários para igualá-las. Como as microáreas do projeto são fixas, não se busca igualar jornadas entre agentes: cada plano respeita o limite de jornada do próprio ACS, e as diferenças de carga entre microáreas são medidas e reportadas.

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

A contribuição pretendida é adaptar métodos existentes para reunir **rotas a pé, prioridade clínica, atraso entre visitas e diagnóstico de sobrecarga por microárea**. Com territórios fixos, o planejamento não redistribui visitas entre agentes; diferenças de carga entre microáreas serão reportadas à gestão. A avaliação comparará a construção gulosa, a ALNS e, quando disponível, o plano manual, medindo deslocamento, atrasos, carga e demanda não atendida. Os percentuais dos estudos serão referências de comparação, não metas presumidas para o SUS.

## 6. Metodologia

### 6.1 Visão geral do artefato

O artefato é um programa em Python que, para cada ACS e cada dia, recebe o cadastro dos usuários da microárea e devolve o roteiro do dia: **quais** domicílios visitar, **em que ordem**, **em que horário** e **por qual caminho**. Ele é organizado em cinco módulos encadeados:

| Módulo | Entrada | O que faz | Saída |
|---|---|---|---|
| **M1. Gerador de instâncias** | Setor censitário (IBGE) e mapa do OpenStreetMap | Recorta a microárea, extrai a malha de caminhos a pé e sorteia domicílios e usuários com atributos clínicos sintéticos | Instância: UBS, domicílios, usuários e ACS |
| **M2. Matriz de tempos a pé** | Malha de caminhos e pontos da instância | Calcula o caminho mínimo entre todos os pares de pontos e converte distância em minutos | Matriz de tempos, salva em cache |
| **M3. Pré-processamento** | Instância e data do planejamento | Calcula atraso e prioridade de cada usuário, identifica urgências e descarta visitas inviáveis | Visitas candidatas do dia |
| **M4. Otimizador** | Candidatas, matriz e parâmetros | Construção gulosa seguida de ALNS, com várias sementes | Roteiro do dia e lista de visitas que ficaram de fora |
| **M5. Saídas** | Roteiros de todos os ACS da equipe | Gera itinerários, arquivos GPX, mapa e relatório por microárea | Itinerários, mapa Leaflet e relatório da equipe |

M1 e M2 existem porque não há dados reais disponíveis; numa implantação, seriam substituídos pela leitura do cadastro do e-SUS Território e por uma matriz calculada uma vez por microárea. M3, M4 e M5 formam o núcleo reutilizável. Cada ACS é processado de forma independente (seção 4.1), e só o M5 junta os resultados da equipe.

### 6.2 Dados de entrada (instâncias sintéticas)

Como não há dados públicos de visitas de ACS, as instâncias são geradas artificialmente sobre mapas reais:

- **Território:** cada microárea é representada por um setor censitário da malha do IBGE. A malha de caminhos a pé do setor, com uma pequena faixa ao redor para não cortar caminhos na borda, é extraída do OpenStreetMap com osmnx (perfil `walk`).
- **Domicílios:** pontos sorteados sobre edificações ou áreas residenciais do OSM dentro do setor, cada um associado ao nó mais próximo da malha.
- **Usuários:** cada domicílio recebe um ou mais usuários com atributos sintéticos: condição de acompanhamento (por exemplo, gestante, pessoa idosa, hipertensão ou diabetes, tuberculose em tratamento, acamado ou nenhuma condição especial), nível de risco, intervalo máximo entre visitas, data da última visita, duração estimada da visita e, quando houver, janela de horário. Os valores seguem distribuições definidas pelo grupo; são ilustrativos, não clínicos.
- **ACS e UBS:** ponto de início e fim do turno (a UBS), duração da jornada de campo (por exemplo, 6 h), velocidade de caminhada (por exemplo, 4,5 km/h) e teto de casos graves por dia. Todos são parâmetros configuráveis.

Além de um cenário-base, serão geradas variações para testar o comportamento do algoritmo: domicílios aglomerados, alta proporção de urgências e alto atraso acumulado.

### 6.3 Matriz de tempos a pé

O tempo entre dois pontos é o comprimento do caminho mínimo na malha de pedestres (algoritmo de Dijkstra, via networkx) dividido pela velocidade de caminhada. A matriz é calculada uma vez por instância e salva em disco, de modo que as execuções do otimizador não recalculam caminhos. A sequência de nós de cada caminho também é guardada, para desenhar a rota no mapa e gerar o GPX. OpenRouteService ou OSRM com perfil pedestre são alternativas equivalentes, caso a extração local se mostre lenta.

### 6.4 Modelo do problema diário

Para um ACS em um dia, o problema é escolher **quais** visitas candidatas fazer e **em que ordem**, saindo da UBS e voltando a ela. Como nem todos os usuários cabem na jornada, trata-se de um problema de orientação (OPTWVP): cada visita tem um "lucro", que é a penalidade evitada ao fazê-la hoje, e o tempo do dia é o orçamento disponível.

**Notação**

| Símbolo | Significado |
|---|---|
| $V$ | visitas candidatas do dia; $0$ representa a UBS |
| $t_{ij}$ | tempo a pé de $i$ até $j$ (min) |
| $s_i$ | duração da visita $i$ (min) |
| $[a_i, b_i]$ | janela de horário da visita $i$ |
| $d_i$ | dias desde a última visita ao usuário $i$ |
| $P_i$ | intervalo máximo recomendado entre visitas (dias) |
| $w_i$ | peso clínico (nível de risco) |
| $U \subseteq V$ | visitas urgentes |
| $G \subseteq V$ | casos graves; $K$ é o teto de casos graves por dia |
| $T$, $T_{max}$ | jornada nominal e jornada máxima tolerada (min) |

**Decisões:** $y_i \in \{0,1\}$ indica se a visita $i$ é feita hoje; $x_{ij} \in \{0,1\}$ indica se o ACS vai de $i$ diretamente para $j$; $h_i$ é o horário de chegada em $i$; $H$ é o horário de retorno à UBS.

**Função objetivo (em minutos equivalentes):**

$$
\min \;\; \underbrace{\sum_{i,j} t_{ij}\,x_{ij}}_{\text{caminhada}}
\;+\; \beta \underbrace{\sum_{i \in V} w_i \,\frac{d_i + 1}{P_i}\,(1 - y_i)}_{\text{penalidade de quem fica para depois}}
\;+\; \gamma \underbrace{\max(0,\; H - T)}_{\text{excesso de jornada}}
$$

O segundo termo é o centro do modelo. Se o usuário $i$ não for visitado hoje, amanhã terão se passado $d_i + 1$ dias desde a última visita; a razão $(d_i + 1)/P_i$ mede quanto do intervalo máximo terá sido consumido (acima de 1, o usuário está atrasado). Multiplicada pelo peso clínico, ela cresce continuamente com o tempo sem visita e com o risco: deixar de fora quem está atrasado e é de alto risco custa caro, e deixar de fora quem foi visitado recentemente custa pouco. Os coeficientes $\beta$ (minutos por unidade de penalidade) e $\gamma$ (minutos por minuto de excesso) convertem os três termos para a mesma escala, como em Trautsamwieser e Hirsch (2011), e serão calibrados nos experimentos.

**Restrições:**

1. **Rota:** o roteiro sai da UBS e volta a ela; cada visita feita tem exatamente uma chegada e uma saída ($\sum_j x_{ij} = \sum_j x_{ji} = y_i$).
2. **Tempo:** se o ACS vai de $i$ para $j$, chega em $j$ depois de terminar $i$ e caminhar até $j$ ($h_j \ge h_i + s_i + t_{ij}$). Essa restrição também impede subciclos.
3. **Janelas:** visitas com horário marcado começam dentro da janela ($a_i \le h_i \le b_i$).
4. **Jornada:** o retorno à UBS não ultrapassa a jornada máxima ($H \le T_{max}$).
5. **Urgência:** toda urgência é visitada ($y_i = 1$ para $i \in U$) e antes de qualquer visita não urgente.
6. **Teto de casos graves:** $\sum_{i \in G} y_i \le K$.

Se as urgências sozinhas não couberem na jornada, o excedente é registrado como demanda não atendida e vai para o relatório da equipe.

**Urgências que surgem durante o dia.** Não se reotimiza o dia inteiro: a nova urgência é inserida logo após a visita em andamento, partindo da posição atual do ACS. Se isso ultrapassar $T_{max}$, retiram-se do restante do roteiro as visitas não urgentes de menor penalidade até que o roteiro volte a caber na jornada. As visitas retiradas entram no relatório.

### 6.5 Algoritmo de solução

**Etapa 1: construção gulosa**

1. Começa com o roteiro vazio (UBS → UBS).
2. Insere as urgências primeiro, em ordem de vizinho mais próximo a partir da UBS.
3. Para cada candidata ainda fora do roteiro, calcula a melhor posição de inserção (a que menos aumenta o tempo, respeitando janelas, jornada e teto) e a razão *penalidade evitada ÷ minutos acrescentados*. Insere a candidata com a maior razão.
4. Repete o passo 3 até que nenhuma candidata caiba.

O resultado é uma solução viável obtida em fração de segundo, já que cada dia tem algumas dezenas de candidatas para 10 a 20 visitas.

**Etapa 2: ALNS (Busca Adaptativa em Grandes Vizinhanças)**

A solução gulosa é refinada por iterações de "destruir e reparar":

1. **Destruição:** remove de 10% a 40% das visitas do roteiro, com um dos operadores:
   - *aleatória*: remove visitas sorteadas;
   - *pior custo*: remove as visitas que mais aumentam a caminhada em relação à penalidade que evitam;
   - *geográfica*: remove uma visita e suas vizinhas mais próximas, abrindo espaço para reorganizar um trecho inteiro.
2. **Reparo:** reinsere visitas, tanto as removidas quanto as que já estavam fora do roteiro, com um dos operadores:
   - *inserção gulosa*: mesmo critério da etapa 1;
   - *inserção por arrependimento (regret-2)*: prioriza a visita que mais perderia se não fosse inserida agora em sua melhor posição.
3. **Sanitização:** as urgências são recolocadas no início do roteiro, garantindo a precedência mesmo que algum operador a tenha quebrado.
4. **Aceitação (Simulated Annealing):** a nova solução substitui a atual se for melhor. Se for pior por uma diferença $\Delta$, é aceita com probabilidade $e^{-\Delta/\tau}$, em que a temperatura $\tau$ diminui ao longo das iterações. Isso permite escapar de ótimos locais no início e estabilizar no fim.
5. **Adaptação:** cada operador ganha pontos quando gera uma nova melhor solução, uma melhora ou uma solução aceita. A cada bloco de iterações, a probabilidade de escolher cada operador é atualizada de acordo com esses pontos, de forma que os operadores mais úteis para a instância passam a ser usados com mais frequência.

O laço termina por número de iterações ou por tempo limite (alvo: poucos segundos por ACS). A ALNS é executada com várias sementes aleatórias; entrega-se a melhor solução e reporta-se a variação entre as sementes.

**Etapa 3: referência exata (MILP)**

O modelo da seção 6.4 é escrito como programa linear inteiro misto (com a restrição de tempo linearizada por "big-M") e resolvido por um solver (OR-Tools ou PuLP com CBC/HiGHS) em instâncias pequenas, para medir a distância (*gap*) entre a solução da ALNS e o ótimo. Essa etapa serve só para validação e não faz parte do uso cotidiano.

### 6.6 Saídas

- **Itinerário por ACS:** lista ordenada de visitas com horário previsto de chegada e saída, tempo de caminhada entre elas e motivo de cada visita (urgência, atraso ou risco). É exportado em CSV e em GPX (gpxpy), este com o trajeto real pela malha, para abrir em aplicativos de mapa no celular.
- **Mapa (Leaflet/OSM):** rota de cada ACS, domicílios coloridos por prioridade e marcação dos usuários que ficaram de fora.
- **Relatório da equipe:** por microárea, número de candidatas e de visitas planejadas, usuários não atendidos com seus atrasos e pesos, jornada usada e excesso, e a penalidade residual em minutos, que indica quanto trabalho "não coube" no dia. É esse relatório que sustenta pedidos de reforço da equipe ou de revisão das microáreas.

### 6.7 Ambiente de desenvolvimento

Python como linguagem principal; osmnx e networkx para a malha de caminhos e os caminhos mínimos; geopandas e fudgeo para os dados geoespaciais; numpy para o cálculo; gpxpy para os arquivos GPX; folium para o mapa em Leaflet; OR-Tools ou PuLP para o MILP. A lista não é exaustiva: outras dependências podem surgir durante o desenvolvimento.

### 6.8 Plano de validação

- **Comparações:** a ALNS é comparada com (i) a construção gulosa isolada, (ii) a solução ótima do MILP em instâncias pequenas e (iii) um planejamento feito manualmente por uma pessoa sobre o mesmo mapa, também em instâncias pequenas.
- **Métricas:** tempo total de caminhada; urgências atendidas e sua posição no roteiro; penalidade residual e número de usuários atrasados que ficaram de fora; jornada usada e excesso; número de visitas no dia; tempo de execução; *gap* em relação ao MILP; variação entre sementes.
- **Cenários:** base, domicílios aglomerados, alta proporção de urgências e alto atraso acumulado.
- **Calibração:** os pesos $\beta$ e $\gamma$ e os parâmetros da ALNS (taxa de destruição, temperatura inicial, fator de resfriamento) são ajustados num experimento preliminar antes das comparações.

## 7. Resultados esperados

Espera-se entregar um protótipo funcional de roteirização e escalonamento diário a pé para ACS na APS/SUS, construído em duas etapas (construção gulosa e refinamento por ALNS), que considere urgência clínica, intervalo máximo entre visitas e limite de jornada de cada agente.

Como resultados concretos, o projeto deve produzir:

1. um modelo matemático do problema, com função objetivo multicritério normalizada em minutos (deslocamento, excesso de jornada e atraso entre visitas);
2. uma implementação do algoritmo de duas etapas, com matriz de tempos a pé calculada sobre o OpenStreetMap (osmnx) e cache local;
3. uma avaliação comparativa entre a construção gulosa, a ALNS, o planejamento manual (quando disponível) e, em instâncias pequenas, uma formulação MILP de referência, usando múltiplas sementes;
4. um dashboard (Leaflet/OSM) para conferência das rotas, exportação de itinerários em CSV e GPX e relatório de demanda não atendida e de desequilíbrio entre microáreas.

Espera-se que a ALNS produza soluções melhores que a construção gulosa isolada e competitivas com o planejamento manual existente, com ganhos sobretudo no respeito à jornada, atendimento tempestivo de urgências e visibilidade de dados para a gestão — e não necessariamente em redução de distância percorrida, já que a divisão por microárea já tende a produzir bons tempos de deslocamento. Os percentuais de ganho reportados na literatura (seção 5) servem apenas como referência de comparação, não como metas presumidas para o contexto do SUS: os resultados reais dependerão dos dados e das instâncias avaliadas, e serão reportados com suas limitações.

## 8. Cronograma

O projeto deve ser concluído em 2 a 3 semanas, com acompanhamento semanal. As semanas são contadas a partir desta entrega.

| Atividade | Concluído | Semana 1 | Semana 2 | Semana 3 |
|---|:-:|:-:|:-:|:-:|
| Definição do problema, revisão de literatura e proposta | X | | | |
| OE1 — Modelagem e pré-processamento de viabilidade | | X | | |
| OE5 — Geração de dados sintéticos e matriz de distâncias a pé | | X | | |
| OE2 — Construção gulosa e ALNS | | X | X | |
| OE3 e OE4 — Função objetivo, precedência de urgência e teto de casos | | | X | |
| OE6 — Validação (múltiplas sementes, comparação com guloso e manual; MILP em instâncias pequenas) | | | X | X |
| OE7 — Dashboard e relatório por microárea | | | | X |
| Escrita do texto e apresentações semanais | | X | X | X |

A semana 3 funciona como margem. Se o prazo final for antecipado, a prioridade é entregar o algoritmo (guloso + ALNS) e sua comparação com a construção gulosa; a referência MILP e o dashboard são reduzidos ao mínimo necessário (por exemplo, um mapa estático das rotas e o relatório em tabela).

## 9. Referências

- ABDOLHAMIDI, D.; LURKIN, V. **An Integrated Optimization Model for Home Healthcare Routing and Scheduling with Synchronization, Break Scheduling, and Temporal Stability**. Preprint, 2026. [Texto consultado](artigos/abdolhamidi.pdf).
- CATTAFI, M. et al. **An application of constraint solving for home health care**. AI Communications, v. 28, n. 2, p. 215–237, 2015. [Texto consultado](artigos/cattafi.pdf).
- NEVES, M. E. F. **A Metaheuristic Approach to Routing and Scheduling Hospital-at-Home Visits**. Dissertação de mestrado — Louvain School of Management e Instituto Superior Técnico, 2026. [Texto consultado](artigos/neves.pdf).
- ÖZSAKALLI, G. **Home Healthcare Scheduling and Routing Problems**. Tese de doutorado — Yaşar University, 2023. [Texto consultado](artigos/ozsakalli.pdf).
- TRAUTSAMWIESER, A.; HIRSCH, P. **Optimization of daily scheduling for home health care services**. Journal of Applied Operational Research, v. 3, n. 3, p. 124–136, 2011. [Texto consultado](artigos/trautsamwieser.pdf).
- YU, T.; GUAN, Y.; ZHONG, X. **Visiting nurses assignment and routing for decentralized telehealth service networks**. Annals of Operations Research, v. 341, p. 1191–1221, 2024. [Texto consultado](artigos/yu.pdf).
