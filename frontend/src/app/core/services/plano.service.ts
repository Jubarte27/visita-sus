import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Comparacao, Metodo, Params, Plano, PlanoResumo } from '../models';

@Injectable({ providedIn: 'root' })
export class PlanoService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/planos`;

  listar(filtros: { agente?: number; microarea?: number; equipe?: number; data?: string } = {}): Observable<PlanoResumo[]> {
    let params = new HttpParams();
    for (const [k, v] of Object.entries(filtros)) {
      if (v !== undefined && v !== null) params = params.set(k, String(v));
    }
    return this.http.get<PlanoResumo[]>(`${this.url}/`, { params });
  }

  obter(id: number): Observable<Plano> {
    return this.http.get<Plano>(`${this.url}/${id}/`);
  }

  planejar(agente: number, data: string, metodo: Metodo, params: Params = {}): Observable<Plano> {
    return this.http.post<Plano>(`${this.url}/`, { agente, data, metodo, params });
  }

  apagar(id: number): Observable<void> {
    return this.http.delete<void>(`${this.url}/${id}/`);
  }

  comparar(id: number, opcoes: { tempo_milp?: number; n?: number | null; seed?: number } = {}): Observable<Comparacao> {
    return this.http.post<Comparacao>(`${this.url}/${id}/comparar/`, opcoes);
  }

  csvUrl(id: number): string {
    return `${this.url}/${id}/itinerario.csv`;
  }

  gpxUrl(id: number): string {
    return `${this.url}/${id}/itinerario.gpx`;
  }
}
