# Ciclo 2 — Etapa: Pesquisa na Literatura

**Disciplina:** INF99003 — Projeto em Ciência e Inovação
**Problema do ciclo:** artefato computacional para apoiar o planejamento das visitas domiciliares
dos Agentes Comunitários de Saúde (ACS) na Atenção Primária à Saúde (APS) do SUS.
**Corpus revisado:** 8 trabalhos (`artigos/`), todos utilizados.
**Data da revisão:** 17/09/2026.

---

## 1. Objetivo e questões da revisão

O desafio do Ciclo 2 pede um artefato que considere, isolada ou conjuntamente: (i) otimização do
percurso, (ii) tamanho da equipe, (iii) indicadores de urgência por paciente e (iv) intervalo máximo
entre visitas na série temporal. Esta revisão foi conduzida para fundamentar cientificamente a
proposta de solução, respondendo a cinco questões:

| # | Questão de pesquisa | Onde é respondida |
|---|---|---|
| QP1 | Como a literatura **formaliza** o problema de roteirizar e escalonar profissionais de saúde em domicílio? | §3 e §4 |
| QP2 | Que **restrições e critérios de qualidade** são modelados, além da distância percorrida? | §5 |
| QP3 | Quais **métodos de solução** são viáveis em que escala de instância? | §6 |
| QP4 | Que **fontes de dados, APIs de georreferenciamento e formas de validação** são usadas? | §7 |
| QP5 | Qual o **ganho empírico** frente ao planejamento manual, e quais **lacunas** restam para o contexto do ACS/SUS? | §8 e §9 |

O escopo da revisão é o corpus fornecido para o ciclo. Ele é heterogêneo de forma proveitosa —
cobre artigo de periódico, artigo de conferência, preprint, dissertação de mestrado e tese de
doutorado, entre 2011 e 2026 — mas é um corpus fechado: não constitui revisão sistemática, e as
lacunas apontadas em §9 são lacunas *relativas a este corpus*, não necessariamente a toda a
literatura da área.

---

## 2. Método da revisão

Protocolo aplicado a cada trabalho:

1. **Identificação** — autoria, ano, veículo, país/contexto do caso.
2. **Extração estruturada** de sete campos: problema tratado; formulação matemática; função
   objetivo; restrições; método de solução; dados e instâncias; resultados quantitativos.
3. **Codificação por atributos**, usando a taxonomia consolidada em Cissé et al. (apud
   Özsakallı, 2023) que agrupa as restrições em **temporais**, **espaciais** e **de atribuição**,
   acrescida de dois eixos de interesse direto do nosso problema: *urgência/prioridade* e
   *periodicidade entre visitas*.
4. **Síntese comparativa** (§4 e §6) e **mapeamento de lacunas** contra os quatro elementos
   listados no desafio (§9).

---

## 3. Delimitação do problema na literatura

Há convergência entre todos os trabalhos quanto à natureza do problema. O planejamento diário de
visitas domiciliares é modelado como uma variante do **Problema de Roteamento de Veículos com
Janelas de Tempo (VRPTW)**, acrescida de restrições próprias do setor de saúde — daí a sigla
consolidada **HHCRSP** (*Home Health Care Routing and Scheduling Problem*), também grafada HHSRP
ou HHCP. Riazi et al. (2017) e Fathollahi-Fard et al. (2020) afirmam isso explicitamente; Neves
(2026) registra que, com múltiplas bases, o problema se estende para o **MDVRPTW** (multi-depósito).

Três consequências decorrem dessa filiação e orientam todo o resto da revisão:

- **O problema é NP-difícil.** Todos os oito trabalhos assumem essa condição, e ela é confirmada
  empiricamente: o CPLEX não fecha instâncias de 10 pacientes e 4 cuidadores em 6 horas
  (Özsakallı, 2023); o Xpress resolve na otimalidade apenas 20 tarefas e 4 enfermeiras
  (Trautsamwieser & Hirsch, 2011); a geração de colunas pura não termina em 7200 s com 8–10
  cuidadores e 90–100 pacientes (Riazi et al., 2017). **Métodos exatos servem como referencial
  (benchmark), não como motor de produção.**
- **O problema é intrinsecamente multicritério.** Nenhum dos trabalhos minimiza apenas distância;
  ver §5.
- **As decisões se organizam em três níveis** — estratégico (territorialização, localização),
  tático (dimensionamento de força de trabalho) e operacional (atribuição + sequenciamento diário)
  —, conforme Hulshof et al. e Makboul et al. (apud Neves, 2026) e o Capítulo 1 de Özsakallı
  (2023). O item *"tamanho da equipe"* do nosso desafio é tático; os demais são operacionais.

**Nota de transposição para a APS.** O corpus trata de enfermeiros/médicos de *home health care* e
*hospital-at-home*, não de ACS. As diferenças relevantes — o ACS é morador e caminha no seu
território, sua "visita" é de vigilância e vínculo e não procedimento clínico, e a microárea já é
uma partição territorial pré-existente — são discutidas em §9. A estrutura combinatória (atribuir
visitas a profissionais + sequenciar sob limite de jornada), entretanto, é a mesma, o que legitima
o uso deste corpus como fundamentação.

---

## 4. Síntese por trabalho

### 4.1 Trautsamwieser & Hirsch (2011) — VNS para escalonamento diário, Cruz Vermelha Austríaca

Modelo MILP cuja **função objetivo é uma soma ponderada de sete parcelas** (pesos somando 1,
definidos pelo decisor): tempo de viagem, horas extras, preferências não atendidas, violação de
janelas de tempo *soft* do cliente, violação das janelas *soft* da enfermeira (inclusive do
intervalo), tempo de serviço executado por profissional superqualificado e tempo de deslocamento
não remunerado. Preferências e superqualificação, medidas em número de tarefas, são multiplicadas
pela duração do serviço para ficarem na mesma escala (minutos) das demais parcelas — um recurso
simples e diretamente reaproveitável. Restrições *hard*: janelas de tempo, regulação de jornada,
intervalo obrigatório (modelado como viagem a um "nó de pausa" e retorno ao mesmo cliente),
compatibilidade de qualificação, idioma e recusas mútuas entre cliente e enfermeira.

**Método:** *Variable Neighborhood Search* com 12 vizinhanças (4 operadores *move* + 8
*cross-exchange*, dimensionadas por análise de sensibilidade), busca local 3-opt e critério de
aceitação em duas partes — função de penalidade com pesos dinâmicos no intervalo [1,10] e medida
probabilística decrescente (0,3 → 0,1).

**Resultados:** encontra todos os ótimos globais das instâncias pequenas; escala até **512 tarefas,
420 clientes e 75 enfermeiras**; tempos de viagem obtidos por ArcGIS. Comparado a um plano de rota
real, **reduz o tempo de viagem em cerca de 45%**. Observam que áreas urbanas têm tempos de viagem
muito menores que rurais e que, em cenário rural, nem sempre há solução viável se todos os clientes
tiverem de ser atendidos no mesmo dia.

### 4.2 Cattafi et al. (2015) — Programação por Restrições híbrida, Ferrara (Itália)

Caso real do serviço público (AUSL 109): 15 enfermeiras, 458 pacientes e 3.323 requisições em um
mês; jornada de 432 min/dia e 36 h/semana; **sem janelas de tempo** (os pacientes ficam em casa o
dia inteiro). O planejamento vigente era manual e partia de uma **partição estática do território
em 9 zonas** — situação estruturalmente idêntica à das microáreas de ACS.

**Modelo CP** com restrições globais: `multiknapsack` associa cada serviço (item de tamanho igual à
duração) a um par (enfermeira, dia) com capacidade igual à jornada; `NValue` conta quantas
enfermeiras distintas atendem cada paciente, materializando a **lealdade** (continuidade do
cuidado); e uma restrição definida pelo usuário, `traveltime`, embute um solucionador de TSP para
calcular o tempo de rota de cada dupla (enfermeira, dia), propagando limitantes durante a busca.
O TSP é resolvido por **relaxação lagrangiana** (Held–Karp com *one-tree* e subgradiente): 240
instâncias em 0,485 s, contra 1,12 s do CP puro e 24.405 s em ASP.

**Função objetivo:** soma ponderada de balanceamento de carga e penalidade de lealdade. Os autores
comparam duas formas de balancear e o resultado é uma das lições mais úteis do corpus: minimizar o
**desvio absoluto** da carga é perigoso quando parte da carga (o tempo de viagem) é ela própria uma
variável de decisão — nos Exemplos 2 e 3 do artigo, a minimização do desvio leva o solucionador a
*aumentar* deliberadamente o deslocamento das enfermeiras para igualar cargas. Minimizar a **carga
máxima** (min-max) produziu, no caso real, distribuição semanal mais justa *e* melhor lealdade.

**Busca:** comparam estratégia genérica (*first-fail* + valor aleatório + *restarts*), heurística
dedicada (maior duração primeiro; atribuir preferencialmente enfermeira que já atende o paciente,
desempatando pela menor carga semanal) e **Large Neighbourhood Search** (relaxar 10% das variáveis
de atribuição, limite de 50 falhas, *timeout* de 10 min). Todas superam a solução manual em carga
máxima; H+LNS é a melhor. Aproximam a fronteira de Pareto por ε-restrição e mostram que a solução
manual é **dominada** por vários pontos da fronteira.

### 4.3 Riazi et al. (2017) — Decomposição e algoritmo distribuído, Chalmers

Trata o HHCRSP como VRPTW com cuidadores heterogêneos (nível de qualificação do cuidador ≥ nível
exigido pelo paciente). Aplicam **decomposição de Dantzig-Wolfe**: o mestre vira um problema de
*set-covering* sobre rotas e os subproblemas são caminhos mínimos elementares com janelas de tempo,
resolvidos por *label-setting* com eliminação de 2-ciclos. Adotam **geração de colunas heurística**
(colunas geradas só na raiz da árvore de *branch-and-price*, seguidas de re-resolução do mestre como
MILP para forçar integralidade).

A contribuição distintiva é o **algoritmo *gossip***: após uma atribuição inicial, pares de
cuidadores são sorteados e apenas o subproblema local daquele par é reotimizado; repete-se até não
haver melhoria. É descentralizado e permite atacar instâncias grandes com subproblemas pequenos.
Instâncias: 3/25 (pequena) a 10/100 (grande), área de 5×5 km², velocidade 17 km/h, serviço de
10–20 min, janelas de 30–120 min. **Resultado:** *gossip*-MILP vence nas pequenas (solucionador
local exato); nas grandes a CG pura não termina em 2 h, enquanto *gossip*-CG entrega os melhores
limitantes inteiros.

Nota: observam que, havendo variáveis de tempo de início de serviço, **não são necessárias
restrições de eliminação de subrotas** — detalhe de modelagem que simplifica a formulação.

### 4.4 Fathollahi-Fard, Hajiaghaei-Keshteli & Mirjalili (2020) — heurísticas rápidas + VNS-SA

MILP em que cada enfermeiro parte de uma **farmácia**, visita seus pacientes (entregando
medicamentos e coletando amostras biológicas) e termina em um **laboratório**. Consideram
**múltiplos modos de transporte** (cada tipo *k* com capacidade `CAPk` e custo por distância `TCk`)
e introduzem uma **penalidade por distância excedente**: cada par (enfermeiro, veículo) tem uma
distância máxima desejada `MDISnk`, e o excesso é penalizado no custo. É o mecanismo mais direto do
corpus para induzir equilíbrio entre rotas sem recorrer a min-max.

**Métodos:** limitante inferior por relaxação lagrangiana; três heurísticas construtivas (H1, H2,
H3) que diferem apenas na escolha do primeiro paciente de cada rota sobre a matriz
`DTCijk = Dij × TCk`; e uma metaheurística híbrida **VNS-SA** (VNS no laço externo para
diversificação, SA no interno como critério de aceitação), com codificação *random-key*.
Parametrização por **experimentos de Taguchi**; 12 instâncias em três portes; implementação em Java.

**Resultados:** o limitante lagrangiano só é obtido em portes pequeno e médio; as heurísticas são
mais rápidas mas com desvio maior; **H2 é a melhor heurística e VNS-SA-H2 a melhor combinação
geral**. A leitura gerencial dos autores é pertinente ao nosso projeto: decisões operacionais
diárias exigem resposta rápida (heurística), decisões estratégicas justificam solucionador exato.

### 4.5 Yu, Guan & Zhong (2024) — rede híbrida de telessaúde, *Annals of Operations Research*

Único trabalho do corpus que trata **modalidade de atendimento como decisão**, e não só a rota.
Decide conjuntamente: quais clínicas comunitárias abrir (com taxa de colaboração), se cada paciente
é atendido em casa, na clínica ou no hospital, e as rotas dos enfermeiros visitadores — ou seja,
combina **localização de facilidades + atribuição + roteamento**. Pacientes Tipo I (mobilidade
reduzida) só podem ser atendidos em casa; Tipo II são flexíveis. Três categorias de enfermeiros com
salários distintos.

A função objetivo admite variante de **bem-estar social**, somando ao custo operacional a
*desutilidade* do paciente que precisa se deslocar (proporcional à distância) — formalização
explícita de que **o deslocamento do usuário também é custo**, ponto sensível em territórios
periféricos.

**Método:** formulação de particionamento de conjuntos resolvida por heurística **bi-nível** — nível
superior decide a abertura de clínicas; inferior aplica geração de colunas com (a) heurística
construtiva baseada em *pivot patients* (pacientes mutuamente incompatíveis por janela de tempo,
identificados por clique máxima, e pacientes distantes de tudo, ranqueados por escore
`w_j = w_avg + w_min`), (b) algoritmo de rotulagem com dominância e (c) busca local. C++ e Gurobi
10.0; dados sintéticos calibrados por uma organização real do norte-centro da Flórida.

**Contribuição diretamente reutilizável:** a **Proposição 1** dá regra fechada para inserir um
paciente de demanda no mesmo dia: sendo *d* a menor distância do paciente *q* a uma unidade de
saúde e (*i*,*j*) o segmento de rota mais próximo viável, se `d ≥ min{d_qi, d_qj}` então é sempre
melhor inserir *q* na rota do profissional visitador. É um critério O(1) para acolher demanda
urgente sem reotimizar o plano inteiro.

### 4.6 Abdolhamidi & Lurkin (2026, preprint) — modelo integrado com estabilidade temporal, Suíça

O trabalho mais rico em critérios centrados no paciente. Um único MILP diário integra:
sincronização (visitas que exigem dois cuidadores simultâneos), pausas obrigatórias (em local fixo
*e* flexíveis ao longo da rota), preferências paciente–cuidador, **continuidade com o cuidador
anterior**, coordenação de pacientes co-residentes no mesmo domicílio e **estabilidade do horário de
atendimento**.

A inovação central é a formulação de **duplo horizonte temporal**: penaliza-se separadamente o
desvio em relação (a) ao horário mais recentemente comunicado ao paciente (`S_i`, compromisso de
curto prazo) e (b) ao horário de referência estabelecido no início do episódio de cuidado (`O_i`,
rotina de longo prazo). As penalidades são **contínuas**, não restrições rígidas nem padrões
discretos — justamente o que permite *medir o custo marginal* de melhorar a estabilidade.

**Avaliação:** comparam MILP reforçado (Gurobi), formulação nativa de listas/intervalos (Hexaly),
um GA e uma matheurística ALNS, com orçamento de 600 s e 30 sementes. Dados operacionais reais:
31 dias de janeiro/2025, 103–219 atendimentos/dia, 8–18 turnos, 37 tipos de qualificação. O
pré-processamento que elimina pares atendimento–turno inviáveis reduz os não-zeros pré-resolvidos
em 41,1% e a mediana do *gap* de 58,9% para 33,0% — **evidência de que filtrar incompatibilidades
antes de otimizar vale mais que trocar de solucionador**.

**Achados gerenciais:** (i) a **cobertura** é limitada pelo *alinhamento* temporal, espacial e de
qualificação entre capacidade e demanda, não pelos pesos do objetivo — otimizar cobertura sozinha
por 12 h elevou a média de apenas 45,4% para 46,6%; (ii) ganhos iniciais em continuidade e
estabilidade custam quase nada em eficiência (numa instância, −23% de penalidade de experiência do
paciente sem alteração relevante de custo), tornando-se progressivamente caros; (iii) desvios de
curto e de longo prazo respondem de forma distinta, o que justifica mantê-los como termos separados.

### 4.7 Özsakallı (2023) — tese: compartilhamento de veículo, *drop-off/pick-up* e um SAD

Propõe variante nova (HHSRP-VS): vários cuidadores compartilham um mesmo veículo e podem ser
**deixados em um domicílio e recolhidos depois** (política DP), reduzindo espera improdutiva. Para
acomodar a política DP sem violar a eliminação de subrotas, adota uma **modelagem em duas camadas**
com nós-espelho (o nó `n+i` representa o recolhimento no domicílio *i*). Objetivo: minimizar o
*flow time* total mais penalidade por pacientes não visitados.

**Métodos:** matheurística construtiva de limitante superior baseada em *clustering* (UBA) e
**ALNS-VS** com heurísticas específicas de remoção, inserção, busca local DP e *caregiver swap*.
**Resultados:** o CPLEX só produz soluções inteiras com 10 pacientes, com *gap* médio de 40,7% em
6 h; o ALNS-VS obtém *flow time* em média 6% menor que o CPLEX em 1,8 s, e 13–19% melhor que
UBA+DP nas instâncias de 10 a 100 pacientes; a política DP economiza **até 25%** de *flow time*, com
ganho maior em áreas pequenas/densas e cuidados de maior dificuldade.

**Artefato:** protótipo de **HHDSS** (sistema de apoio à decisão) em Python — Tkinter, matplotlib,
NumPy, scikit-learn, folium e VeRoViz — com três módulos: *entrada de dados* (formulários → base
.xlsx), *solver* (matriz de distâncias via **Bing Maps Distance Matrix API**, mapa de pacientes,
algoritmo de otimização, rotas sobre a malha viária) e *visualização*. Aplicado a localizações
aproximadas de pacientes de COVID-19 em Ancara, Istambul e Izmir, extraídas do mapa de calor do
aplicativo oficial turco. Reporta, citando Kandakoglu et al. (2020), que um SAD análogo produziu
**redução de 33% no tempo total de viagem**, com economia estimada de ~100 mil dólares canadenses
anuais em uma única divisão hospitalar.

### 4.8 Neves (2026) — dissertação: ALNS multi-depósito para *Hospital-at-Home*, Portugal

É o trabalho **mais próximo do nosso desafio**, por quatro razões: trata urgência como restrição de
precedência, decompõe por território, usa API aberta de rotas e entrega um protótipo de visualização.

**Problema:** planejamento diário multi-depósito (4 unidades CUF em Lisboa, Cascais, Sintra e
Odivelas), **decomposto por depósito** — cada paciente é pré-atribuído à sua unidade (ou à mais
próxima) e cada depósito vira um subproblema independente, reduzindo a complexidade. Restrições:
compatibilidade de equipe (pacientes que exigem médico só podem ser atendidos por equipes com
médico), **precedência "urgentes primeiro"** dentro de cada rota, **teto de M = 3 urgentes por
equipe** (para não concentrar casos graves), jornada máxima `Tmax = 240 min` (turno da manhã) e uma
rota por equipe por dia. Objetivo: tempo de viagem (peso 1) + penalidade por ativar equipe com
médico (peso 200, calibrado para ficar na escala de um turno completo).

**Métodos:** MILP (com eliminação de subrotas MTZ) como referencial exato e **ALNS** (Ropke &
Pisinger) como motor prático: solução inicial gulosa por menor custo de inserção; três operadores de
destruição (*worst*, *shaw*, *random*); seleção adaptativa de operadores por roleta com pesos
atualizados por segmento; aceitação por *simulated annealing*; parada por número fixo de iterações
(escolhida em vez de tempo, para tornar as comparações justas). A ordem urgente→não-urgente é
preservada por uma rotina de *sanitização* após cada destruição — ou seja, **a política clínica é
garantida por construção**, não por penalidade. Calibração por **Design of Experiments (DoE)**.

**Dados e experimentos:** 316 pacientes reais; 5 portes (50 a 250 pacientes) × 4 cenários
(*balanced*, *clustered*, *high urgent*, *high doctor*) × 8 réplicas = **640 instâncias por
depósito**; matrizes de tempo/distância pela API **OpenRouteService**.

**Resultados:** o ALNS iguala o exato (desvios médios entre −0,060% e +0,030%) a uma fração do
custo — segundos a ~4,6 min contra 18–22 min do Gurobi, que frequentemente estoura o limite de
30 min nas instâncias maiores. O estudo de *ablation* mostra que **nenhum operador isolado responde
por mais de 0,5%** do desempenho: o valor está na reorganização repetida das rotas. Frente à
construção gulosa, o ALNS completo melhora o objetivo por paciente em ~7% e o tempo de viagem em
~17%.

**Protótipo:** fluxo dados → matriz (ORS) → ALNS por depósito → JSON → *dashboard* interativo, com
mapa das rotas coloridas por equipe, KPIs (pacientes, equipes ativas, urgentes, casos que exigem
médico), lista de equipes e *pop-up* por paciente (ID, equipe, ordem na rota, tempo de serviço,
rótulos de urgência). Os autores o descrevem como **camada de interpretação entre o algoritmo e o
usuário operacional** — e mostram que o *dashboard* serve também para *verificar* restrições
(conferir visualmente que os urgentes vêm primeiro).

Citando Varas et al. (2024), registram ganhos de **31,8% em tempo de viagem, 83,6% em tempo de
espera e 95,4% no desbalanceamento entre equipes** frente ao planejamento manual de enfermeiros.

---

## 5. Análise comparativa I — critérios e restrições modelados (QP2)

### 5.1 Atributos por trabalho

Legenda: ● modelado plenamente · ◐ modelado de forma parcial/implícita · — ausente.

| Atributo | Traut. 2011 | Cattafi 2015 | Riazi 2017 | Fath.-Fard 2020 | Yu 2024 | Abdolh. 2026 | Özsakallı 2023 | Neves 2026 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Temporais** ||||||||
| Janela de tempo do usuário | ● (hard+soft) | — | ● | ● | ● | ● | ◐ | — |
| Jornada máxima do profissional | ● (soft, hora extra) | ● (dia e semana) | ● | ◐ | ● (12 h) | ● | ● (hard) | ● (240 min) |
| Pausa/intervalo obrigatório | ● | — | — | — | — | ● (fixa e flexível) | — | — |
| Sincronização de visitas | — | — | — | — | — | ● | ◐ | — |
| Estabilidade do horário entre dias | — | — | — | — | — | ● (duplo horizonte) | — | — |
| **Espaciais** ||||||||
| Matriz de distância/tempo real | ● (ArcGIS) | ● (matriz fornecida) | — (euclid.) | — (euclid.) | ◐ (euclid. ajustada) | ● (por modal) | ● (Bing Maps) | ● (OpenRouteService) |
| Múltiplos depósitos/bases | — | — | — | — | ● (clínicas) | ◐ | — | ● |
| Múltiplos modais de transporte | ◐ (início em casa/base) | — | — | ● | — | ● (carro, bici, a pé, transp. público) | ● (veículo compartilhado) | — |
| Partição territorial prévia | ◐ | ● (9 zonas, manual) | — | — | — | — | — | ● (por depósito) |
| **Atribuição** ||||||||
| Qualificação/habilidade | ● (níveis) | — | ● (níveis) | — | ● (tipos de enfermeiro) | ● (37 tipos) | ● (demanda×habilidade) | ● (médico/enfermeiro) |
| Continuidade do cuidado / lealdade | ◐ (preferência) | ● (`NValue`) | — | — | — | ● (cuidador anterior) | — | — |
| Preferências e recusas mútuas | ● (inclui idioma) | — | — | — | — | ● | — | — |
| Balanceamento de carga | ◐ (hora extra) | ● (min-max vs. desvio) | — | ● (penalidade de distância) | — | ◐ | ◐ | ◐ (teto de urgentes) |
| **Eixos do nosso desafio** ||||||||
| **Urgência/prioridade clínica** | ◐ (janela mais estreita p/ nível 3) | — | — | — | ● (mesmo-dia, Prop. 1) | ◐ (cobertura ponderada) | ◐ (penalidade p/ não visitado) | ● (precedência + teto) |
| **Intervalo máximo entre visitas** | ◐ (frequência semanal como dado) | ◐ (requisições já datadas) | — | — | — | ◐ (rotina de longo prazo) | — | — |
| Horizonte multi-período | ◐ (semana, como entrada) | ● (semana/mês) | — | — | — | — (dia, com histórico) | — | — |

### 5.2 Leituras que emergem da tabela

**(a) Distância é o critério menos disputado — e o menos suficiente.** Os oito trabalhos incluem
deslocamento no objetivo, mas nenhum se limita a ele. Os critérios recorrentes são carga de
trabalho, continuidade, satisfação de preferências e cobertura da demanda.

**(b) Como agregar critérios: três abordagens observadas.**
- *Soma ponderada* — dominante (Trautsamwieser & Hirsch; Cattafi; Neves; Abdolhamidi & Lurkin).
  Simples e controlável pelo decisor, mas recupera apenas soluções eficientes suportadas.
- *Fronteira de Pareto aproximada* por ε-restrição (Cattafi et al.), usada para *verificar* se os
  pesos escolhidos produzem um compromisso razoável — e para demonstrar que a solução manual é
  dominada. Abdolhamidi & Lurkin fazem o mesmo por varredura de um escalar λ.
- *Restrição rígida garantida por construção* (Neves) — a regra "urgentes primeiro" nunca é violada
  porque a representação da solução a impõe.

Recomendação para o Ciclo 2: usar soma ponderada **com pesos na mesma unidade** (minutos, como em
Trautsamwieser & Hirsch) e **traçar a curva de compromisso** variando um multiplicador, como em
Abdolhamidi & Lurkin. Isso transforma a escolha de pesos de arbitrariedade em resultado
experimental.

**(c) Balanceamento tem uma armadilha documentada.** Cattafi et al. (2015) demonstram, com
contraexemplos, que minimizar o desvio absoluto de cargas *que incluem tempo de viagem* pode levar o
otimizador a aumentar o deslocamento para igualar cargas. Alternativas seguras: min-max da carga
(melhor resultado no caso real deles), desvio calculado **apenas sobre o tempo de serviço** somado
ao tempo de viagem total fora do termo de desvio, ou penalidade por distância excedente
(Fathollahi-Fard et al., 2020).

**(d) Urgência é pouco explorada e, quando aparece, aparece de duas formas distintas.** Neves (2026)
a trata como **precedência intra-rota + teto por equipe**; Yu et al. (2024) a tratam como **inserção
reativa de demanda do mesmo dia**. As duas formas são complementares e ambas são relevantes para o
ACS: a primeira para o plano do dia, a segunda para acomodar um caso que surge durante o turno.

**(e) A maior lacuna do corpus é exatamente um item do nosso desafio.** *Nenhum* dos oito trabalhos
modela **intervalo máximo entre visitas na série temporal** como restrição ou penalidade de primeira
classe. O mais próximo é a "rotina de longo prazo" `O_i` de Abdolhamidi & Lurkin (2026), que penaliza
desvio de *horário*, não de *periodicidade*. Detalhe: no caso de Trautsamwieser & Hirsch a
frequência semanal de cada cliente é *dado de entrada* (média 3, desvio 2, distribuída
uniformemente pelos dias) — ou seja, o problema de *quando revisitar* é resolvido fora do modelo.
Ver §9.

---

## 6. Análise comparativa II — métodos de solução e escala (QP3)

| Método | Trabalhos | Maior instância reportada | Tempo | Observação |
|---|---|---|---|---|
| MILP em solucionador comercial | todos (como referencial) | 20 tarefas/4 enferm. (Xpress); 10 pac./4 cuid. (CPLEX, *gap* 40,7% em 6 h) | horas | inviável como motor de produção |
| MILP reforçado + pré-processamento | Abdolhamidi & Lurkin 2026 | 219 atendimentos, 18 turnos | 600 s | desvio mediano de 0,4% do melhor conhecido |
| Formulação nativa de listas/intervalos (Hexaly) | Abdolhamidi & Lurkin 2026 | idem | 600 s | melhor valor conhecido em 12/21 instâncias |
| Geração de colunas / *branch-and-price* | Riazi 2017; Yu 2024 | 100 pacientes (falha em 2 h na CG pura) | minutos–horas | forte teoricamente; precisa de heurística para escalar |
| CG heurística + distribuído (*gossip*) | Riazi 2017 | 10 cuid./100 pac. | minutos | decomposição por pares; superou CG pura nas grandes |
| CG bi-nível + rotulagem + busca local | Yu 2024 | centenas de pacientes | curto | integra localização + atribuição + rota |
| CP + LNS + relax. lagrangiana p/ TSP | Cattafi 2015 | 82 pacientes/dia, 12 enferm., 4 semanas | 10 min | flexível para adicionar/relaxar restrições |
| VNS | Trautsamwieser & Hirsch 2011 | **512 tarefas, 420 clientes, 75 enferm.** | curto | maior instância do corpus |
| VNS-SA híbrido | Fathollahi-Fard 2020 | porte "grande" (12 instâncias) | curto | Taguchi para calibração |
| **ALNS** | Özsakallı 2023; Neves 2026; Abdolhamidi & Lurkin 2026 (benchmark) | 100 pac./12 cuid.; 250 pac./4 depósitos | 1,8 s a ~4,6 min | melhor relação qualidade/tempo do corpus |
| Heurísticas construtivas rápidas | Fathollahi-Fard 2020 (H1–H3); Neves 2026 (guloso); Özsakallı 2023 (UBA) | — | < 1 s | úteis como solução inicial e limitante superior |

### 6.1 Convergência metodológica

O corpus converge para um padrão de três camadas que recomendamos adotar:

1. **Heurística construtiva rápida** para obter solução inicial viável (inserção de menor custo, em
   Neves 2026 e Riazi et al. 2017; *clustering*, em Özsakallı 2023).
2. **Metaheurística de vizinhança ampla** para melhoria — ALNS é a escolha mais frequente nos
   trabalhos recentes, e Neves (2026) justifica a preferência: problemas fortemente restritos exigem
   vizinhanças grandes para escapar de ótimos locais, e a seleção adaptativa de operadores dispensa
   ajuste manual por instância.
3. **MILP exato como referencial de validação** em instâncias pequenas, para medir o *gap* da
   metaheurística — prática seguida por Trautsamwieser & Hirsch (2011), Özsakallı (2023),
   Abdolhamidi & Lurkin (2026) e Neves (2026), esta última com duas instâncias pequenas resolvidas na
   otimalidade em segundos, justamente para servirem de gabarito.

### 6.2 Boas práticas experimentais extraídas

- **Calibração sistemática de parâmetros**: Taguchi (Fathollahi-Fard et al., 2020), DoE (Neves,
  2026), análise de sensibilidade de vizinhanças (Trautsamwieser & Hirsch, 2011). Não calibrar "no
  olho".
- **Múltiplas sementes e reporte de mediana e melhor valor**: Abdolhamidi & Lurkin (2026) usam 30
  sementes e mostram que a mediana de uma execução única do GA/ALNS é bem pior que o melhor de 30 —
  reportar só o melhor superestima o método. Neves (2026) usa 5 sementes; Riazi et al. (2017), 10
  execuções com desvio-padrão.
- **Critério de parada por iterações, não por tempo**, quando o objetivo é comparar instâncias de
  portes diferentes (Neves, 2026).
- **Estudo de *ablation***: remover um componente por vez para medir sua contribuição (Neves, 2026).
- **Pré-processamento de inviabilidades** antes de otimizar (Abdolhamidi & Lurkin, 2026: −41,1% de
  não-zeros; Riazi et al., 2017: filtrar pacientes fora da qualificação antes do subproblema;
  Trautsamwieser & Hirsch, 2011: fixar em 0 as variáveis de atribuição proibidas).
- **Geração de cenários enviesados**, e não apenas de portes diferentes: Neves (2026) cria cenários
  *clustered*, *high urgent* e *high doctor* para testar o algoritmo sob composições adversas de
  demanda. Diretamente transponível para "alta densidade de gestantes", "alta densidade de casos em
  atraso" etc.

---

## 7. Dados, georreferenciamento e validação (QP4)

| Trabalho | Origem dos dados | Distância/tempo | Escala |
|---|---|---|---|
| Trautsamwieser & Hirsch 2011 | Cruz Vermelha Austríaca, 3 regiões (1 urbana, 2 rurais) | ArcGIS | 512 tarefas / 75 enferm. |
| Cattafi 2015 | AUSL 109, Ferrara — 4 semanas reais (fev/2010) | matriz de tempos fornecida | 458 pac. / 3.323 requisições |
| Riazi 2017 | sintético, parametrizado por condições reais | euclidiana (17 km/h) | 100 pac. |
| Fathollahi-Fard 2020 | sintético (sem *benchmark* prévio) | euclidiana 2D | 12 instâncias |
| Yu 2024 | sintético calibrado por organização real da Flórida | euclidiana ajustada p/ tempo | centenas de pacientes |
| Abdolhamidi & Lurkin 2026 | **operacional real**, 31 dias, parceiro suíço | tabela de tempos por modal | 219 atend./dia |
| Özsakallı 2023 | localizações de pacientes COVID-19 (app oficial turco) | **Bing Maps Distance Matrix API** | 100 pac. / 12 cuid. |
| Neves 2026 | 316 pacientes reais (CUF, região de Lisboa) | **OpenRouteService API** | 250 pac. / 4 depósitos |

**Lições para o nosso artefato:**

- **Distância euclidiana é aceitável para estudar algoritmos, insuficiente para um artefato de
  campo.** Os dois trabalhos que entregam protótipo utilizável (Özsakallı, 2023; Neves, 2026) usam
  API de rotas sobre malha viária. **OpenRouteService** é a escolha preferível para o Ciclo 2: é
  aberta, baseada em OpenStreetMap e suporta perfil de **pedestre** — essencial, já que o ACS
  frequentemente caminha no território.
- **Pré-cálculo da matriz é um passo explícito do pipeline**, não detalhe de implementação. Ambos os
  protótipos separam "construção da matriz" de "otimização", o que permite trabalhar offline, com
  chamadas limitadas à API e cache. Vale replicar.
- **Validar contra o plano manual é o padrão de evidência da área.** Trautsamwieser & Hirsch (2011),
  Cattafi et al. (2015) e Abdolhamidi & Lurkin (2026) comparam explicitamente com a solução humana
  vigente. Onde não há plano manual disponível, o substituto aceito é a comparação com uma
  **heurística gulosa** (Neves, 2026: ~17% de redução de tempo de viagem sobre a construção gulosa).
- **Dados sensíveis exigem anonimização e agregação.** Özsakallı (2023) trabalha com *localizações
  aproximadas* extraídas de mapa de calor; para o SUS, a LGPD e a natureza clínica dos dados
  (gestação, tuberculose, DSTs) tornam obrigatório operar com dados sintéticos ou desidentificados e
  com georreferenciamento em granularidade adequada.

---

## 8. Evidência de impacto frente ao planejamento manual (QP5)

| Fonte | Comparação | Ganho reportado |
|---|---|---|
| Trautsamwieser & Hirsch (2011) | VNS vs. plano de rota real da Cruz Vermelha | **−45% no tempo de viagem** |
| Varas et al. (2024), apud Neves (2026) | modelo vs. planejamento manual de enfermeiros (Hospital Padre Hurtado) | **−31,8% tempo de viagem; −83,6% tempo de espera; −95,4% desbalanceamento entre equipes** |
| Kandakoglu et al. (2020), apud Özsakallı (2023) | SAD vs. prática anterior (The Ottawa Hospital) | **−33% no tempo total de viagem**; ~CAD 100 mil/ano em uma divisão |
| Cattafi et al. (2015) | CP+LNS vs. solução manual por zonas (Ferrara) | melhora carga máxima semanal *e* lealdade em todas as 4 instâncias; solução manual **dominada** na fronteira de Pareto |
| Özsakallı (2023) | política *drop-off/pick-up* vs. compartilhamento sem DP | **até −25% de *flow time*** |
| Neves (2026) | ALNS vs. construção gulosa | **−7% no objetivo por paciente; −17% no tempo de viagem** |
| Abdolhamidi & Lurkin (2026) | modelo vs. escalas realizadas pela organização | cobertura **comparável** à realizada; ganho está em continuidade/estabilidade, não em volume |

Três observações sobre essa evidência:

1. **A magnitude típica do ganho está entre 30% e 45% de tempo de viagem** quando a linha de base é
   planejamento manual. É uma expectativa realista a declarar como hipótese no nosso projeto.
2. **O ganho não é só quilometragem.** Cattafi et al. (2015) observam que a solução manual, por ser
   baseada em zonas contíguas, já produz *bons tempos de viagem* — ela perde em **equidade de carga**
   e em **lealdade**. Isso é diretamente aplicável ao ACS, cuja microárea também é contígua por
   construção: **o ganho provável do nosso artefato não está em encurtar a caminhada, e sim em
   garantir cobertura tempestiva, equilíbrio entre agentes e priorização correta.**
3. **Há um limite duro que a otimização não vence.** Abdolhamidi & Lurkin (2026) mostram que
   insistir no peso da cobertura eleva o atendimento de 45,4% para apenas 46,6%: quando a demanda
   supera a capacidade útil, o modelo revela o déficit, não o elimina. O artefato deve, portanto,
   **reportar a demanda não atendida como saída de primeira classe** — informação de gestão para
   dimensionamento de equipe (o item "tamanho da equipe" do desafio).

---

## 9. Lacunas e posicionamento do Ciclo 2

### 9.1 Lacunas identificadas no corpus, relativas ao nosso problema

| # | Lacuna | Situação no corpus | Implicação para o projeto |
|---|---|---|---|
| L1 | **Intervalo máximo entre visitas** (periodicidade clínica) como restrição/penalidade | Ausente em todos os 8; frequência aparece como *entrada* (Trautsamwieser & Hirsch) ou como requisições já datadas (Cattafi) | Contribuição original possível: variável de *atraso desde a última visita*, no espírito do *Periodic VRP*, penalizada de forma contínua — análogo ao `Δo` de Abdolhamidi & Lurkin, mas sobre periodicidade e não sobre horário |
| L2 | **Índice composto de urgência clínica** (gestação, idoso, diabetes, tuberculose, DSTs) | Urgência aparece como rótulo binário (Neves) ou demanda de mesmo dia (Yu) | Definir escore contínuo de prioridade a partir dos dados clínicos disponíveis na unidade, combinando-o com L1 (urgência cresce com o atraso) |
| L3 | **Deslocamento a pé** como modal principal | Só Abdolhamidi & Lurkin listam caminhada entre modais; os demais assumem veículo | Usar perfil pedestre na API de rotas; a "economia de combustível" não é o objetivo — tempo e esforço do agente são |
| L4 | **Território pré-particionado como dado, e não como decisão** | Cattafi mostra que a partição estática em 9 zonas *causa* desequilíbrio de carga; Neves decompõe por depósito para reduzir complexidade | A microárea do ACS é fixa por normativa. Adotar a decomposição de Neves (um subproblema por microárea/equipe) e usar o diagnóstico de Cattafi para *medir* o desequilíbrio entre microáreas — resultado de interesse para a gestão |
| L5 | **Contexto de APS pública brasileira** | Nenhum trabalho; casos são Áustria, Itália, Suécia, Irã, EUA, Suíça, Turquia, Portugal | Registrar explicitamente como limitação de validade externa e transpor com cuidado (ver §3) |
| L6 | **Incerteza** (tempo de serviço, ausência do morador, clima) | Todos os 8 são determinísticos; Neves e Yu apontam isso como trabalho futuro | Fora do escopo do Ciclo 2; declarar como limitação e trabalho futuro |

### 9.2 Decisões de projeto fundamentadas na literatura

As decisões abaixo derivam diretamente da revisão e devem ser registradas como fundamentação da
solução computacional:

| Decisão | Fundamento |
|---|---|
| Modelar como **MDVRPTW/HHCRSP**, com um subproblema por microárea | Neves (2026); Cattafi et al. (2015) |
| **Arquitetura de três camadas**: construtiva gulosa → ALNS → MILP como referencial em instâncias pequenas | Neves (2026); Özsakallı (2023); Abdolhamidi & Lurkin (2026) |
| **ALNS** como motor principal, com seleção adaptativa de operadores por roleta e aceitação SA | Ropke & Pisinger apud Neves (2026); Özsakallı (2023) |
| Urgência como **precedência intra-rota + teto por agente**, garantida por construção | Neves (2026) |
| Regra O(1) para **inserir demanda urgente surgida no dia** | Proposição 1 de Yu et al. (2024) |
| **Intervalo máximo entre visitas** como penalidade contínua sobre o atraso (contribuição própria, por analogia) | analogia com o duplo horizonte de Abdolhamidi & Lurkin (2026) |
| Objetivo como **soma ponderada com todos os termos em minutos**, e curva de compromisso obtida variando um multiplicador λ | Trautsamwieser & Hirsch (2011); Abdolhamidi & Lurkin (2026) |
| Balanceamento por **min-max de jornada** ou penalidade por excesso — **evitar** desvio absoluto sobre carga que inclua viagem | Cattafi et al. (2015, Exemplos 2 e 3); Fathollahi-Fard et al. (2020) |
| **Pré-processamento** eliminando pares (visita, agente) inviáveis antes de otimizar | Abdolhamidi & Lurkin (2026); Riazi et al. (2017) |
| **OpenRouteService**, perfil pedestre, com matriz pré-calculada e cacheada | Neves (2026); Özsakallı (2023, com Bing Maps) |
| Cenários de teste **enviesados** (aglomerado, alta urgência, alto atraso) além de portes crescentes | Neves (2026) |
| Calibração por **DoE/Taguchi**; múltiplas sementes; reporte de mediana *e* melhor valor; *ablation* | Neves (2026); Fathollahi-Fard et al. (2020); Abdolhamidi & Lurkin (2026) |
| **Validação contra linha de base gulosa/manual**, reportando % de redução | Trautsamwieser & Hirsch (2011); Neves (2026) |
| **Dashboard** como camada de interpretação e de verificação visual de restrições | Neves (2026); Özsakallı (2023) |
| **Demanda não atendida** e desequilíbrio entre microáreas como saídas de primeira classe (subsídio ao dimensionamento de equipe) | Abdolhamidi & Lurkin (2026); Cattafi et al. (2015) |

### 9.3 Hipóteses decorrentes

- **H1.** Um plano gerado por ALNS reduz o tempo total de deslocamento dos ACS de uma microárea em
  pelo menos 15% frente a uma linha de base gulosa, e em 30–45% frente a um plano manual, se este
  estiver disponível.
- **H2.** A introdução de penalidade sobre o atraso desde a última visita reduz o número de usuários
  fora do intervalo máximo recomendado, a um custo marginal baixo de deslocamento na região inicial
  da curva de compromisso — padrão observado por Abdolhamidi & Lurkin (2026) para continuidade e
  estabilidade.
- **H3.** A garantia estrutural de "urgentes primeiro" com teto por agente não degrada
  significativamente o tempo total de percurso, conforme Neves (2026).
- **H4.** Sob demanda superior à capacidade útil, aumentar o peso da cobertura produz ganho marginal
  desprezível — o gargalo é o alinhamento entre capacidade e demanda (Abdolhamidi & Lurkin, 2026).

---

## 10. Referências

ABDOLHAMIDI, D.; LURKIN, V. **An Integrated Optimization Model for Home Healthcare Routing and
Scheduling with Synchronization, Break Scheduling, and Temporal Stability**. Preprint submetido a
*Operations Research, Data Analytics and Logistics*, jul. 2026. SSRN 7229446.

CATTAFI, M.; HERRERO, R.; GAVANELLI, M.; NONATO, M.; MALUCELLI, F. An application of constraint
solving for home health care. **AI Communications**, v. 28, n. 2, p. 215–237, 2015.
DOI 10.3233/AIC-140632.

FATHOLLAHI-FARD, A. M.; HAJIAGHAEI-KESHTELI, M.; MIRJALILI, S. A set of efficient heuristics for a
home healthcare problem. **Neural Computing and Applications**, v. 32, p. 6185–6205, 2020.
DOI 10.1007/s00521-019-04126-8.

NEVES, M. E. F. **A Metaheuristic Approach to Routing and Scheduling Hospital-at-Home Visits**.
Dissertação (Mestrado em Engenharia e Gestão Industrial / Business Engineering) — Louvain School of
Management e Instituto Superior Técnico, 2026.

ÖZSAKALLI, G. **Home Healthcare Scheduling and Routing Problems**. Tese (Doutorado em Business
Administration) — Graduate School, Yaşar University, Bornova/İzmir, nov. 2023.

RIAZI, S.; WIGSTRÖM, O.; BENGTSSON, K.; LENNARTSON, B. Decomposition and distributed algorithms for
home healthcare routing and scheduling problem. In: **IEEE Conference on Automation Science and
Engineering (CASE)**, 2017.

TRAUTSAMWIESER, A.; HIRSCH, P. Optimization of daily scheduling for home health care services.
**Journal of Applied Operational Research**, v. 3, n. 3, p. 124–136, 2011.

YU, T.; GUAN, Y.; ZHONG, X. Visiting nurses assignment and routing for decentralized telehealth
service networks. **Annals of Operations Research**, v. 341, p. 1191–1221, 2024.
DOI 10.1007/s10479-024-05883-z.

### Referências secundárias citadas via o corpus

Begur, Miller & Weaver (1997) · Bredström & Rönnqvist (2008) · Cheng & Rich (1998) · Cissé et al.
(2017) · Di Mascolo et al. (2021) · Eveborn et al. (2006, LAPS-CARE) · Fikar & Hirsch (2017) ·
Grieco et al. (2021) · Held & Karp (1970) · Kandakoglu et al. (2020) · Kovacs et al. (2014, 2015,
ConVRP) · Mankowska et al. (2014) · Rasmussen et al. (2012) · Ropke & Pisinger (2006, ALNS) ·
Solomon (1987) · Varas et al. (2024) · Bonomi et al. (2025) · Quintanilla et al. (2020).
