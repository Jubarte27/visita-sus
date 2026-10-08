# visita-sus · frontend

Angular 21 (LTS) + Angular Material + Leaflet. Telas descritas no Apêndice F de
[docs/passos-implementacao.md](../docs/passos-implementacao.md).

```sh
npx npm@11 install     # o npm 9 do Ubuntu falha neste projeto (bug "edgesOut"); o npm 11 via npx resolve
npx ng serve           # http://localhost:4200 ; /api é encaminhado ao Django em localhost:8000 (proxy.conf.json)
npx ng build           # saída em dist/frontend
npx ng test --watch=false
```

Estrutura:

- `src/app/core/`: tipos da API (`models.ts`), serviços HTTP (`services/`), a equipe/data escolhidas na barra superior (`selecao.service.ts`) e funções do plano (`plano-utils.ts`: selos das regras, rótulos, horários).
- `src/app/shared/map/`: `MapComponent` (Leaflet: território + rota, paradas numeradas e não atendidas de um plano) e funções puras do mapa (`map-utils.ts`).
- `src/app/shared/jornada/`: barra de jornada (retorno × T × Tmax).
- `src/app/shared/barras/`: gráfico de barras horizontais (uma série, valor na ponta, linha de referência, tooltip) usado no relatório.
- `src/app/pages/`: início (equipes), microárea (mapa), painel da equipe, plano do ACS e relatório.
