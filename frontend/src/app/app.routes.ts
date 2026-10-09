import { Routes } from '@angular/router';

// telas do Apêndice F de docs/passos-implementacao.md; cada uma carregada sob demanda (o Leaflet só vem com o mapa)
export const routes: Routes = [
  { path: '', loadComponent: () => import('./pages/inicio/inicio.page').then((m) => m.InicioPage), title: 'visita-sus' },
  {
    path: 'equipes/:id',
    loadComponent: () => import('./pages/painel-equipe/painel-equipe.page').then((m) => m.PainelEquipePage),
    title: 'Painel da equipe · visita-sus',
  },
  {
    path: 'equipes/:id/relatorio',
    loadComponent: () => import('./pages/relatorio/relatorio.page').then((m) => m.RelatorioPage),
    title: 'Relatório da equipe · visita-sus',
  },
  {
    path: 'microareas/:id',
    loadComponent: () => import('./pages/microarea/microarea.page').then((m) => m.MicroareaPage),
    title: 'Microárea · visita-sus',
  },
  {
    path: 'planos/:id',
    loadComponent: () => import('./pages/plano/plano.page').then((m) => m.PlanoPage),
    title: 'Plano do ACS · visita-sus',
  },
  { path: '**', redirectTo: '' },
];
