import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Equipe, Metodo, Params, PlanejarEquipeResposta, Relatorio } from '../models';

@Injectable({ providedIn: 'root' })
export class EquipeService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/equipes`;

  listar(): Observable<Equipe[]> {
    return this.http.get<Equipe[]>(`${this.url}/`);
  }

  obter(id: number): Observable<Equipe> {
    return this.http.get<Equipe>(`${this.url}/${id}/`);
  }

  planejar(id: number, data: string, metodo: Metodo, params: Params = {}): Observable<PlanejarEquipeResposta> {
    return this.http.post<PlanejarEquipeResposta>(`${this.url}/${id}/planejar/`, { data, metodo, params });
  }

  relatorio(id: number, data: string): Observable<Relatorio> {
    return this.http.get<Relatorio>(`${this.url}/${id}/relatorio/`, { params: new HttpParams().set('data', data) });
  }

  relatorioCsvUrl(id: number, data: string): string {
    return `${this.url}/${id}/relatorio.csv?data=${encodeURIComponent(data)}`;
  }
}
