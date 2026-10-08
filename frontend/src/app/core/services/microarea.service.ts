import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Agente, Domicilios, Malha, Microarea } from '../models';

@Injectable({ providedIn: 'root' })
export class MicroareaService {
  private readonly http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/microareas`;

  obter(id: number): Observable<Microarea> {
    return this.http.get<Microarea>(`${this.url}/${id}/`);
  }

  domicilios(id: number, data: string): Observable<Domicilios> {
    return this.http.get<Domicilios>(`${this.url}/${id}/domicilios/`, { params: new HttpParams().set('data', data) });
  }

  malha(id: number): Observable<Malha> {
    return this.http.get<Malha>(`${this.url}/${id}/malha/`);
  }

  atualizarAgente(id: number, mudancas: Partial<Agente>): Observable<Agente> {
    return this.http.patch<Agente>(`${environment.apiUrl}/agentes/${id}/`, mudancas);
  }
}
