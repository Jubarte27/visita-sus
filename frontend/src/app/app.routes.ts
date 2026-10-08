import { Routes } from '@angular/router';

import { InicioPage } from './pages/inicio/inicio.page';
import { MicroareaPage } from './pages/microarea/microarea.page';
import { PainelEquipePage } from './pages/painel-equipe/painel-equipe.page';
import { PlanoPage } from './pages/plano/plano.page';
import { RelatorioPage } from './pages/relatorio/relatorio.page';

// telas do Apêndice F de docs/passos-implementacao.md
export const routes: Routes = [
  { path: '', component: InicioPage, title: 'visita-sus' },
  { path: 'equipes/:id', component: PainelEquipePage, title: 'Painel da equipe · visita-sus' },
  { path: 'equipes/:id/relatorio', component: RelatorioPage, title: 'Relatório da equipe · visita-sus' },
  { path: 'microareas/:id', component: MicroareaPage, title: 'Microárea · visita-sus' },
  { path: 'planos/:id', component: PlanoPage, title: 'Plano do ACS · visita-sus' },
  { path: '**', redirectTo: '' },
];
