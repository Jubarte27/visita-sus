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
import { ROTULO_MOTIVO_NAO_ATENDIDA, ROTULO_MOTIVO_VISITA, ROTULO_RISCO, rotuloRisco } from '../../core/plano-utils';
import {
  CORES_W, agruparPorPonto, comprimentoM, corDoPeso, htmlIntervalo, htmlRisco, nomeCondicao, popupDoPonto,
  raioDoPonto, setasDaRota,
} from './map-utils';

function chips(urgente: boolean, grave: boolean): string {
  return (urgente ? '<span class="chip-mini urgente">urgente</span>' : '') + (grave ? '<span class="chip-mini">grave</span>' : '');
}

function iconeMaterial(nome: string, titulo: string): string {
  return `<span class="material-icons" aria-label="${titulo}" title="${titulo}">${nome}</span>`;
}

const OSM_ATRIB = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

/**
 * Mapa Leaflet reutilizável.
 *
 * Território: microárea (polígono), malha a pé, domicílios agrupados por ponto de acesso (cor = peso clínico w,
 * borda grossa = urgente, popup com os atributos) e UBS.
 * Plano (opcional): rota pela malha com setas no sentido do percurso, paradas numeradas na ordem do roteiro e
 * visitas não atendidas (×). Com `esmaecerDomicilios`, os domicílios viram fundo ("demais domicílios").
 * `destacar(chave)` realça uma parada (usado pela lista e pela linha do tempo).
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
  /** Início da jornada, para mostrar as janelas de atendimento em horário real. */
  readonly horaInicio = input('08:00:00');

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
  private destacado?: L.Marker;
  private enquadrado = false;
  /** Limites da microárea, para reenquadrar quando o contêiner muda de tamanho (antes de o usuário mexer). */
  private limites?: L.LatLngBounds;
  private usuarioMexeu = false;
  private observador?: ResizeObserver;

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
          this.limites = camada.getBounds();
          mapa.fitBounds(this.limites, { padding: [20, 20] });
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
      const horaInicio = this.horaInicio();
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
          .bindTooltip(`${g.domicilios.length} domicílio(s) · ${rotuloRisco(g.wMax)}${g.urgente ? ' · urgente' : ''}`)
          .bindPopup(popupDoPonto(g, horaInicio), { maxWidth: 360 })
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
        L.geoJSON(rota, { style: { color: '#2a78d6', weight: 4, opacity: 0.75 }, interactive: false }).addTo(
          this.camadas.rota,
        );
        // setas no sentido do percurso, umas 25 ao longo da rota (no mínimo a cada 80 m)
        const passo = Math.max(80, comprimentoM(rota.coordinates) / 25);
        for (const s of setasDaRota(rota.coordinates, passo)) {
          const icone = L.divIcon({
            className: '',
            html: `<div class="seta-rota" style="transform:rotate(${s.angulo.toFixed(0)}deg)">➤</div>`,
            iconSize: [12, 12],
            iconAnchor: [6, 6],
          });
          L.marker([s.lat, s.lon], { icon: icone, interactive: false, keyboard: false }).addTo(this.camadas.rota);
        }
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
            `<div class="popup-ponto"><div class="dom-card">` +
              `<div class="t"><b>${p.ordem}ª visita · ${nomeCondicao(p.condicao)}</b>${htmlRisco(p.w)}` +
              `${chips(p.urgente, p.grave)}<span class="cod">#${p.codigo}</span></div>` +
              `<div>${htmlIntervalo(p.dias_sem_visita, p.P)}</div>` +
              `<div class="m">${iconeMaterial('schedule', 'atendimento')}${p.inicio}–${p.fim}` +
              `${iconeMaterial('directions_walk', 'caminhada desde a parada anterior')}${p.caminhada_min.toFixed(0)} min` +
              `${iconeMaterial('flag', 'motivo')}${ROTULO_MOTIVO_VISITA[p.motivo]}</div></div></div>`,
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
            `<div class="popup-ponto"><div class="dom-card">` +
              `<div class="t"><b>× ${nomeCondicao(n.condicao)}</b>${htmlRisco(n.w)}${chips(n.urgente, n.grave)}` +
              `<span class="cod">#${n.codigo}</span></div>` +
              `<div>${htmlIntervalo(n.dias_sem_visita, n.P)}</div>` +
              `<div class="m">${iconeMaterial('block', 'por que ficou de fora')}ficou de fora: ` +
              `${ROTULO_MOTIVO_NAO_ATENDIDA[n.motivo]}</div></div></div>`,
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

  /** Realça a parada `parada-<ordem>` (ou tira o realce, com null). */
  destacar(chave: string | null): void {
    this.destacado?.getElement()?.classList.remove('destacada');
    const m = chave ? this.marcadores.get(chave) : undefined;
    this.destacado = m instanceof L.Marker ? m : undefined;
    this.destacado?.getElement()?.classList.add('destacada');
  }

  ngOnDestroy(): void {
    this.observador?.disconnect();
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
        { collapsed: window.innerWidth < 700 },
      )
      .addTo(mapa);
    this.legenda().addTo(mapa);
    mapa.on('dragstart', () => (this.usuarioMexeu = true));
    mapa.getContainer().addEventListener('wheel', () => (this.usuarioMexeu = true), { passive: true });
    // o layout da página pode mudar a altura do mapa depois de ele nascer (ex.: no celular, a lista acima cresce)
    this.observador = new ResizeObserver(() => {
      mapa.invalidateSize();
      if (this.limites && !this.usuarioMexeu) mapa.fitBounds(this.limites, { padding: [20, 20] });
    });
    this.observador.observe(this.el().nativeElement);
    this.mapa.set(mapa);
  }

  private legenda(): L.Control {
    const controle = new L.Control({ position: 'bottomleft' });
    controle.onAdd = () => {
      const div = L.DomUtil.create('div', 'legenda-mapa');
      L.DomEvent.disableClickPropagation(div);
      const cores = Object.entries(CORES_W)
        .map(([w, cor]) => `<li><span class="cor" style="background:${cor}"></span>${ROTULO_RISCO[Number(w)]}</li>`)
        .join('');
      const plano = this.esmaecerDomicilios()
        ? `<li><span class="simbolo parada-mini">1</span>parada, na ordem do roteiro</li>
           <li><span class="simbolo">×</span>visita que ficou de fora</li>
           <li><span class="simbolo seta-mini">➤</span>sentido do percurso</li>`
        : `<li><span class="simbolo">◯</span>círculo maior = mais domicílios no ponto</li>`;
      div.innerHTML = `<details ${window.innerWidth > 700 ? 'open' : ''}><summary>Legenda</summary>
        <ul><li class="sub">cor = risco do domicílio</li>${cores}${plano}
        <li><span class="simbolo borda">◯</span>borda grossa = urgente</li></ul></details>`;
      return div;
    };
    return controle;
  }
}
