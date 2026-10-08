import {
  Component,
  ElementRef,
  OnDestroy,
  afterNextRender,
  effect,
  input,
  signal,
  viewChild,
} from '@angular/core';
import type { LineString, MultiPolygon, Polygon } from 'geojson';
import * as L from 'leaflet';

import { Domicilios, ItemRoteiro, Malha, NaoAtendida, Ubs } from '../../core/models';
import { ROTULO_MOTIVO_NAO_ATENDIDA, ROTULO_MOTIVO_VISITA } from '../../core/plano-utils';
import { CORES_W, agruparPorPonto, corDoPeso, nomeCondicao, popupDoPonto, raioDoPonto } from './map-utils';

const OSM_ATRIB = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

/**
 * Mapa Leaflet reutilizável.
 *
 * Território: microárea (polígono), malha a pé, domicílios agrupados por ponto de acesso (cor = peso clínico w,
 * borda grossa = urgente, popup com os atributos) e UBS.
 * Plano (opcional): rota pela malha, paradas numeradas na ordem do roteiro e visitas não atendidas (×).
 * Com `esmaecerDomicilios`, os domicílios viram fundo ("demais domicílios").
 */
@Component({
  selector: 'app-map',
  template: '<div #el class="mapa"></div>',
  styles: `
    :host { display: block; height: 100%; min-height: 300px; }
    .mapa { height: 100%; width: 100%; }
  `,
})
export class MapComponent implements OnDestroy {
  readonly poligono = input<Polygon | MultiPolygon | null>(null);
  readonly domicilios = input<Domicilios | null>(null);
  readonly ubs = input<Ubs | null>(null);
  readonly malha = input<Malha | null>(null);
  readonly rota = input<LineString | null>(null);
  readonly paradas = input<ItemRoteiro[] | null>(null);
  readonly naoAtendidas = input<NaoAtendida[] | null>(null);
  readonly esmaecerDomicilios = input(false);
  /** Rota de outro método, sobreposta tracejada (comparação de métodos). */
  readonly rotaComparada = input<LineString | null>(null);

  private readonly el = viewChild.required<ElementRef<HTMLDivElement>>('el');
  /** Instância do Leaflet, disponível depois da primeira renderização. */
  readonly mapa = signal<L.Map | null>(null);

  private readonly camadas = {
    poligono: L.layerGroup(),
    malha: L.layerGroup(),
    domicilios: L.layerGroup(),
    rota: L.layerGroup(),
    rotaComparada: L.layerGroup(),
    naoAtendidas: L.layerGroup(),
    paradas: L.layerGroup(),
    ubs: L.layerGroup(),
  };
  private controle?: L.Control.Layers;
  private readonly noControle = new Set<L.LayerGroup>();
  private readonly marcadores = new Map<string, L.Marker | L.CircleMarker>();
  private enquadrado = false;

  constructor() {
    afterNextRender(() => this.criarMapa());

    effect(() => {
      const mapa = this.mapa();
      const geo = this.poligono();
      if (!mapa) return;
      this.camadas.poligono.clearLayers();
      if (geo) {
        const camada = L.geoJSON(geo, {
          style: { color: '#d7191c', weight: 2, fill: false, dashArray: '6' },
          interactive: false,
        }).addTo(this.camadas.poligono);
        if (!this.enquadrado) {
          mapa.fitBounds(camada.getBounds(), { padding: [20, 20] });
          this.enquadrado = true;
        }
      }
    });

    effect(() => {
      const mapa = this.mapa();
      const malha = this.malha();
      if (!mapa) return;
      this.camadas.malha.clearLayers();
      if (malha) {
        L.geoJSON(malha, { style: { color: '#888', weight: 1 }, interactive: false }).addTo(this.camadas.malha);
      }
    });

    effect(() => {
      const mapa = this.mapa();
      const fc = this.domicilios();
      const fundo = this.esmaecerDomicilios();
      if (!mapa) return;
      this.camadas.domicilios.clearLayers();
      for (const g of agruparPorPonto(fc?.features ?? [])) {
        L.circleMarker([g.lat, g.lon], {
          radius: fundo ? 3 : raioDoPonto(g.domicilios.length),
          color: '#000',
          weight: fundo ? 0.5 : g.urgente ? 3 : 1,
          opacity: fundo ? 0.4 : 1,
          fillColor: corDoPeso(g.wMax),
          fillOpacity: fundo ? 0.3 : 0.85,
        })
          .bindTooltip(`${g.domicilios.length} domicílio(s) · w máx ${g.wMax}${g.urgente ? ' · URGENTE' : ''}`)
          .bindPopup(popupDoPonto(g), { maxWidth: 600 })
          .addTo(this.camadas.domicilios);
      }
    });

    effect(() => {
      const mapa = this.mapa();
      const rota = this.rota();
      if (!mapa) return;
      this.camadas.rota.clearLayers();
      if (rota) {
        this.registrar(this.camadas.rota, 'rota');
        L.geoJSON(rota, { style: { color: '#1565c0', weight: 4, opacity: 0.75 }, interactive: false }).addTo(
          this.camadas.rota,
        );
      }
    });

    effect(() => {
      const mapa = this.mapa();
      const rota = this.rotaComparada();
      if (!mapa) return;
      this.camadas.rotaComparada.clearLayers();
      if (rota) {
        this.registrar(this.camadas.rotaComparada, 'rota comparada');
        L.geoJSON(rota, { style: { color: '#eb6834', weight: 4, opacity: 0.9, dashArray: '8 6' }, interactive: false })
          .addTo(this.camadas.rotaComparada);
      }
    });

    effect(() => {
      const mapa = this.mapa();
      const paradas = this.paradas();
      if (!mapa) return;
      this.camadas.paradas.clearLayers();
      this.limparMarcadores('parada-');
      if (!paradas) return;
      this.registrar(this.camadas.paradas, 'paradas do roteiro');
      for (const p of paradas) {
        const icone = L.divIcon({
          className: '',
          html: `<div class="parada${p.urgente ? ' urgente' : ''}" style="background:${corDoPeso(p.w)}">${p.ordem}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        const marcador = L.marker([p.lat, p.lon], { icon: icone, zIndexOffset: 500 + p.ordem })
          .bindTooltip(`${p.ordem} · ${nomeCondicao(p.condicao)} · ${p.chegada}`)
          .bindPopup(
            `<b>${p.ordem}ª visita · domicílio ${p.codigo}</b><br>${nomeCondicao(p.condicao)} · ` +
              `${ROTULO_MOTIVO_VISITA[p.motivo]}${p.grave ? ' · grave' : ''}<br>` +
              `chegada ${p.chegada}, atendimento ${p.inicio}–${p.fim}<br>` +
              `w=${p.w} · ${p.dias_sem_visita}/${p.P} dias · caminhada ${p.caminhada_min.toFixed(1)} min`,
          )
          .addTo(this.camadas.paradas);
        this.marcadores.set(`parada-${p.ordem}`, marcador);
      }
    });

    effect(() => {
      const mapa = this.mapa();
      const fora = this.naoAtendidas();
      if (!mapa) return;
      this.camadas.naoAtendidas.clearLayers();
      this.limparMarcadores('fora-');
      if (!fora) return;
      this.registrar(this.camadas.naoAtendidas, 'não atendidas');
      for (const n of fora) {
        const icone = L.divIcon({
          className: '',
          html: `<div class="nao-atendida" style="color:${corDoPeso(n.w)}">×</div>`,
          iconSize: [18, 18],
          iconAnchor: [9, 9],
        });
        const marcador = L.marker([n.lat, n.lon], { icon: icone })
          .bindTooltip(`${nomeCondicao(n.condicao)} · ${ROTULO_MOTIVO_NAO_ATENDIDA[n.motivo]}`)
          .bindPopup(
            `<b>não atendida · domicílio ${n.codigo}</b><br>${nomeCondicao(n.condicao)}` +
              `${n.urgente ? ' · <b>urgente</b>' : ''}${n.grave ? ' · grave' : ''}<br>` +
              `motivo: ${ROTULO_MOTIVO_NAO_ATENDIDA[n.motivo]}<br>` +
              `penalidade ${n.penalidade.toFixed(2)} · ${n.dias_sem_visita} dias sem visita` +
              `${n.atraso_dias ? ` (${n.atraso_dias} além do intervalo)` : ''}`,
          )
          .addTo(this.camadas.naoAtendidas);
        this.marcadores.set(`fora-${n.domicilio}`, marcador);
      }
    });

    effect(() => {
      const mapa = this.mapa();
      const ubs = this.ubs();
      if (!mapa) return;
      this.camadas.ubs.clearLayers();
      if (ubs) {
        const icone = L.divIcon({ className: 'ubs-icon', html: '+', iconSize: [28, 28] });
        L.marker([ubs.lat, ubs.lon], { icon: icone, zIndexOffset: 2000 })
          .bindTooltip(ubs.nome)
          .addTo(this.camadas.ubs);
        if (!this.enquadrado && !this.poligono()) mapa.setView([ubs.lat, ubs.lon], 16);
      }
    });
  }

  /** Centraliza o mapa num ponto (usado pelas listas laterais). */
  focar(lat: number, lon: number, zoom = 18): void {
    this.mapa()?.setView([lat, lon], zoom);
  }

  /** Centraliza e abre o popup de um marcador do plano: `parada-<ordem>` ou `fora-<domicílio>`. */
  abrir(chave: string): void {
    const m = this.marcadores.get(chave);
    const mapa = this.mapa();
    if (!m || !mapa) return;
    const grupo = chave.startsWith('parada-') ? this.camadas.paradas : this.camadas.naoAtendidas;
    if (!mapa.hasLayer(grupo)) grupo.addTo(mapa);
    mapa.setView(m.getLatLng(), Math.max(mapa.getZoom(), 18));
    m.openPopup();
  }

  ngOnDestroy(): void {
    this.mapa()?.remove();
  }

  private registrar(grupo: L.LayerGroup, nome: string): void {
    if (this.noControle.has(grupo) || !this.controle) return;
    this.controle.addOverlay(grupo, nome);
    this.noControle.add(grupo);
  }

  private limparMarcadores(prefixo: string): void {
    for (const k of [...this.marcadores.keys()]) if (k.startsWith(prefixo)) this.marcadores.delete(k);
  }

  private criarMapa(): void {
    const mapa = L.map(this.el().nativeElement, { maxZoom: 19, zoomControl: true }).setView([-15.8, -47.9], 4);
    const padrao = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: OSM_ATRIB,
      maxZoom: 19,
    }).addTo(mapa);
    const humanitario = L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', {
      attribution: `${OSM_ATRIB}, tiles HOT / OSM France`,
      maxZoom: 19,
    });
    const c = this.camadas;
    for (const camada of [c.poligono, c.domicilios, c.rota, c.rotaComparada, c.naoAtendidas, c.paradas, c.ubs]) {
      camada.addTo(mapa);
    }
    this.controle = L.control
      .layers(
        { 'OSM padrão': padrao, 'OSM humanitário': humanitario },
        {
          microárea: c.poligono,
          'malha a pé': c.malha,
          [this.esmaecerDomicilios() ? 'demais domicílios' : 'domicílios']: c.domicilios,
          UBS: c.ubs,
        },
        { collapsed: false },
      )
      .addTo(mapa);
    this.legenda().addTo(mapa);
    this.mapa.set(mapa);
  }

  private legenda(): L.Control {
    const controle = new L.Control({ position: 'bottomleft' });
    controle.onAdd = () => {
      const div = L.DomUtil.create('div', 'legenda-mapa');
      const cores = Object.entries(CORES_W)
        .map(([w, cor]) => `<span class="cor" style="background:${cor}"></span>${w}`)
        .join('');
      div.innerHTML = `peso clínico w:${cores}<br>tamanho = nº de domicílios no ponto · borda grossa = urgente`;
      return div;
    };
    return controle;
  }
}
