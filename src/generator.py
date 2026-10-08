"""
Gerador de instâncias sintéticas (módulo M1 da proposta).

A partir da coordenada de uma UBS, monta a microárea de um ACS e seus domicílios:
  1. microárea: setor censitário (IBGE) que contém a UBS + setores vizinhos, até atingir a população-alvo;
  2. domicílios: quantidade do Censo 2022, distribuída pelas edificações residenciais do OSM;
  3. malha a pé do OSM, com cada domicílio e a UBS inseridos como nós (a aresta da rua é dividida
     em frente à edificação, então casas da mesma quadra ficam em pontos distintos);
  4. atributos sintéticos de cada visita: condição, peso clínico, intervalo máximo, dias desde a
     última visita, duração, janela de horário e urgência;
  5. candidatas do dia: urgentes + as de maior penalidade.

Tutorial:
  1. Ambiente e dados (uma vez; a malha de setores do IBGE com os dados do Censo tem ~57 MB):
       python -m venv .venv && .venv/bin/pip install -r requirements.txt
       ./fetch.sh
  2. Gerar uma instância a partir da coordenada lat,lon de uma UBS (use "=" por causa do sinal negativo).
     Ruas e edificações vêm do OpenStreetMap via Overpass (online), o que pode levar alguns minutos:
       .venv/bin/python src/generator.py --ubs=-30.0431944,-51.1563369 --name bomjesus
     Opções: --populacao (padrão 750; ex. 2000 para uma área maior), --seed, --urgencia, --atraso, --candidatas.
  3. Ver no mapa (servido por http, pois o servidor de tiles bloqueia páginas abertas como arquivo):
       .venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory data/instances
       abrir http://127.0.0.1:8000/bomjesus/mapa.html
  4. Rodar o solver sobre as candidatas do dia:
       .venv/bin/python src/solver.py data/instances/bomjesus/candidatas.gpkg data/instances/bomjesus/graph.graphml
     (para tempo em minutos, use weight="travel_time" e orçamento = jornada em min, ex. 360)

Saída em data/instances/<nome>/:
  graph.graphml     malha a pé (arestas com length em m e travel_time em min)
  instance.gpkg     camadas visits (linha 0 = UBS) e microarea
  candidatas.gpkg   UBS + candidatas do dia (entrada do solver)
  meta.json         resumo e parâmetros
  mapa.html         mapa interativo
Nas visitas, profit = penalidade e cost = duração (min), compatíveis com src/solver.py.
"""

import argparse
import json
from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
from shapely import STRtree
from shapely.geometry import LineString, Point
from shapely.ops import substring

ROOT = Path(__file__).resolve().parent.parent
SETORES_PATH = ROOT / "data" / "RS_setores_CD2022_agregados.gpkg"
OUT_DIR = ROOT / "data" / "instances"
ox.settings.cache_folder = str(ROOT / "data" / "osmnx_cache")
OVERPASS_URLS = ["https://overpass-api.de/api", "https://maps.mail.ru/osm/tools/overpass/api"]

# ==========================================
# Parâmetros (ilustrativos, não clínicos)
# ==========================================
ACS = {"jornada_min": 360, "jornada_max_min": 420, "velocidade_m_min": 75.0, "teto_graves": 3}

# condição principal do domicílio: probabilidade, peso clínico w, intervalo máximo P (dias), duração s (min)
CONDICOES = {
    "nenhuma":              {"prob": 0.45, "w": 1, "P": 60, "s": 10},
    "hipertensao_diabetes": {"prob": 0.22, "w": 2, "P": 30, "s": 15},
    "idoso":                {"prob": 0.15, "w": 2, "P": 30, "s": 15},
    "crianca_menor_2":      {"prob": 0.06, "w": 3, "P": 30, "s": 20},
    "gestante":             {"prob": 0.05, "w": 3, "P": 30, "s": 25},
    "acamado":              {"prob": 0.05, "w": 4, "P": 15, "s": 30},
    "tuberculose":          {"prob": 0.02, "w": 5, "P": 7,  "s": 20},
}
GRAVES = {"acamado", "tuberculose"}

STREET_TYPES = {
    "residential", "living_street", "unclassified", "tertiary", "secondary", "primary",
    "tertiary_link", "secondary_link", "primary_link", "pedestrian", "service", "road",
}
NON_RESIDENTIAL_BUILDINGS = {
    "university", "school", "college", "kindergarten", "hospital", "commercial", "retail",
    "industrial", "warehouse", "office", "public", "civic", "government", "church", "chapel",
    "religious", "construction", "ruins", "transportation", "garage", "garages", "parking",
    "shed", "roof", "kiosk", "service", "sports_hall", "supermarket", "hotel",
}
AREA_POR_DOMICILIO_M2 = 80  # capacidade de uma edificação = área × pavimentos / 80 (mínimo 1)


def overpass(fn, *args, **kwargs):
    """Consulta o Overpass (via osmnx); se o servidor principal recusar, tenta o espelho."""
    for url in OVERPASS_URLS:
        ox.settings.overpass_url = url
        try:
            return fn(*args, **kwargs)
        except ox._errors.InsufficientResponseError:
            raise
        except Exception as e:
            print(f"Overpass falhou em {url} ({type(e).__name__})")
    raise RuntimeError("Overpass indisponível; tente novamente mais tarde")


# ==========================================
# 1. Microárea
# ==========================================
def build_microarea(ubs, populacao, crs):
    """Setor que contém a UBS + vizinhos (os mais próximos da UBS primeiro) até atingir `populacao`."""
    setores = gpd.read_file(SETORES_PATH).to_crs(crs)
    dist = setores.distance(ubs)
    first = dist.idxmin()
    setores = setores[setores["CD_MUN"] == setores.loc[first, "CD_MUN"]]
    chosen = [first]
    while setores.loc[chosen, "v0001"].sum() < populacao:
        area = setores.loc[chosen].union_all().buffer(1)
        vizinhos = setores[setores.intersects(area) & ~setores.index.isin(chosen)]
        if vizinhos.empty:
            break
        chosen.append(dist[vizinhos.index].idxmin())
    return setores.loc[chosen]


# ==========================================
# 2. Domicílios
# ==========================================
def residential_buildings(polygon, crs):
    polygon_ll = gpd.GeoSeries([polygon], crs=crs).to_crs(4326).iloc[0]
    b = overpass(ox.features_from_polygon, polygon_ll, {"building": True})
    b = b[b.geom_type.isin(["Polygon", "MultiPolygon"])].to_crs(crs)
    b = b[b.representative_point().within(polygon)]
    b = b[~b["building"].astype(str).isin(NON_RESIDENTIAL_BUILDINGS) & (b.area >= 20)]
    if "amenity" in b.columns:
        b = b[b["amenity"].isna()]
    levels = b["building:levels"] if "building:levels" in b.columns else pd.Series(np.nan, index=b.index)
    levels = pd.to_numeric(levels, errors="coerce").fillna(1).clip(1, 40)
    slots = np.maximum(1, (b.area * levels // AREA_POR_DOMICILIO_M2)).astype(int)
    return b.reset_index()[["building", "geometry"]].assign(vagas=slots.to_numpy())


def allocate_households(buildings, n, rng):
    """
    Distribui n domicílios entre as edificações. Se as vagas bastam, sorteia n vagas (casas ficam com 1);
    senão preenche todas e distribui o excedente proporcionalmente às vagas (prédios sem pavimentos no OSM).
    """
    slots = buildings["vagas"].to_numpy()
    if slots.sum() >= n:
        owner = np.repeat(np.arange(len(slots)), slots)
        return np.bincount(owner[rng.choice(len(owner), size=n, replace=False)], minlength=len(slots))
    return slots + rng.multinomial(n - slots.sum(), slots / slots.sum())


# ==========================================
# 3. Malha a pé com os domicílios como nós
# ==========================================
def _edge_line(G, u, v, data):
    if "geometry" in data:
        return data["geometry"]
    return LineString([(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])])


def _is_street(data):
    h = data.get("highway")
    return bool((set(h) if isinstance(h, list) else {h}) & STREET_TYPES)


def insert_access_nodes(G, points, merge_tol=1.0, street_max_m=50):
    """
    Liga cada ponto (no CRS projetado de G) à rua mais próxima (ou, a mais de `street_max_m`, a qualquer
    caminho a pé), dividindo a aresta no pé da perpendicular. Modifica G; devolve um nó por ponto.
    Pontos a menos de `merge_tol` m entre si (ou da ponta da aresta) compartilham o nó.
    """
    edges = [(u, v, k, _edge_line(G, u, v, d), _is_street(d)) for u, v, k, d in G.edges(keys=True, data=True) if u < v]
    streets = [e for e in edges if e[4]]
    tree_all, tree_st = STRtree([e[3] for e in edges]), STRtree([e[3] for e in streets])

    # posição de cada ponto ao longo da aresta escolhida
    by_edge, assigned = {}, []
    for p in points:
        j, dist = tree_st.query_nearest(p, return_distance=True, all_matches=False)
        u, v, k, line, _ = streets[j[0]] if dist[0] <= street_max_m else edges[tree_all.query_nearest(p, all_matches=False)[0]]
        pos = line.project(p)
        if pos < merge_tol:
            assigned.append(u)
        elif pos > line.length - merge_tol:
            assigned.append(v)
        else:
            by_edge.setdefault((u, v, k), []).append(pos)
            assigned.append((u, v, k, pos))

    # divide cada aresta (e sua reversa) nas posições
    next_id = max(G.nodes) + 1
    node_at = {}
    for (u, v, k), positions in by_edge.items():
        data = dict(G.edges[u, v, k])
        line = _edge_line(G, u, v, data)
        cuts = []
        for pos in sorted(positions):
            if cuts and pos - cuts[-1][0] < merge_tol:
                node_at[(u, v, k, pos)] = cuts[-1][1]
                continue
            pt = line.interpolate(pos)
            G.add_node(next_id, x=pt.x, y=pt.y, street_count=2)
            cuts.append((pos, next_id))
            node_at[(u, v, k, pos)] = next_id
            next_id += 1
        rev = next(((k2, dict(d2)) for k2, d2 in (G.get_edge_data(v, u) or {}).items()
                    if abs(d2["length"] - data["length"]) < 0.5), None)
        G.remove_edge(u, v, k)
        if rev:
            G.remove_edge(v, u, rev[0])
        chain = [(0.0, u)] + cuts + [(line.length, v)]
        for (a_pos, a), (b_pos, b) in zip(chain, chain[1:]):
            seg = substring(line, a_pos, b_pos)
            G.add_edge(a, b, **{**data, "geometry": seg, "length": seg.length})
            if rev:
                G.add_edge(b, a, **{**rev[1], "geometry": seg.reverse(), "length": seg.length})
    return [a if not isinstance(a, tuple) else node_at[a] for a in assigned]


# ==========================================
# 4. Atributos sintéticos
# ==========================================
def household_attributes(n, mean_residents, rng, p_urgencia, atraso_max):
    nomes = list(CONDICOES)
    probs = np.array([CONDICOES[c]["prob"] for c in nomes])
    cond = rng.choice(nomes, size=n, p=probs / probs.sum())
    df = pd.DataFrame({
        "condicao": cond,
        "n_moradores": 1 + rng.poisson(max(mean_residents - 1, 0), size=n),
        "w": [CONDICOES[c]["w"] for c in cond],
        "P": [CONDICOES[c]["P"] for c in cond],
        "s": [CONDICOES[c]["s"] for c in cond],
    })
    df["d"] = (rng.random(n) * atraso_max * df["P"]).astype(int)  # dias desde a última visita
    df["grave"] = df["condicao"].isin(GRAVES)
    df["urgente"] = (df["condicao"] != "nenhuma") & (rng.random(n) < p_urgencia)
    # 15% só recebem num turno: manhã [0, T/2] ou tarde [T/2, T] (minutos desde o início da jornada)
    meio, T = ACS["jornada_min"] // 2, ACS["jornada_min"]
    turno = rng.choice(["livre", "manha", "tarde"], size=n, p=[0.85, 0.075, 0.075])
    df["tw_start"] = np.where(turno == "tarde", meio, 0)
    df["tw_end"] = np.select([turno == "manha", turno == "tarde"], [meio, T], ACS["jornada_max_min"])
    df["penalidade"] = df["w"] * (df["d"] + 1) / df["P"]  # termo da função objetivo (§6.4)
    df["atrasado"] = df["d"] + 1 > df["P"]
    return df


# ==========================================
# Pipeline
# ==========================================
def generate(ubs_latlon, name, populacao=750, seed=0, p_urgencia=0.02, atraso_max=1.5, n_candidatas=40, buffer_m=200):
    rng = np.random.default_rng(seed)
    ubs_ll = Point(ubs_latlon[1], ubs_latlon[0])
    crs = gpd.GeoSeries([ubs_ll], crs=4326).estimate_utm_crs()
    ubs = gpd.GeoSeries([ubs_ll], crs=4326).to_crs(crs).iloc[0]

    setores = build_microarea(ubs, populacao, crs)
    microarea = setores.union_all()
    n_dom = int(setores["v0007"].sum())

    area_ll = gpd.GeoSeries([microarea.union(ubs).convex_hull.buffer(buffer_m)], crs=crs).to_crs(4326).iloc[0]
    G = overpass(ox.graph_from_polygon, area_ll, network_type="walk", truncate_by_edge=True)
    G = ox.project_graph(G, to_crs=crs)

    buildings = residential_buildings(microarea, crs)
    if buildings.empty:
        raise RuntimeError("nenhuma edificação residencial mapeada no OSM nesta microárea")
    counts = allocate_households(buildings, n_dom, rng)
    occupied = buildings[counts > 0].assign(n_dom=counts[counts > 0])

    nodes = insert_access_nodes(G, [ubs] + list(occupied.representative_point()))
    for _, _, data in G.edges(data=True):
        data["travel_time"] = data["length"] / ACS["velocidade_m_min"]

    hh = pd.DataFrame({"node": np.repeat(nodes[1:], occupied["n_dom"]), "edificacao": np.repeat(occupied.index, occupied["n_dom"])})
    mean_res = setores["v0001"].sum() / max(n_dom, 1)
    hh = pd.concat([hh, household_attributes(len(hh), mean_res, rng, p_urgencia, atraso_max)], axis=1)
    hh.insert(0, "tipo", "domicilio")
    depot = {"tipo": "ubs", "node": nodes[0], "edificacao": -1, "condicao": "", "n_moradores": 0, "w": 0, "P": 0,
             "s": 0, "d": 0, "grave": False, "urgente": False, "tw_start": 0, "tw_end": ACS["jornada_max_min"],
             "penalidade": 0.0, "atrasado": False}
    visits = pd.concat([pd.DataFrame([depot]), hh], ignore_index=True)
    visits["profit"], visits["cost"] = visits["penalidade"], visits["s"]  # compatibilidade com src/solver.py

    # candidatas do dia: todas as urgentes + as de maior penalidade
    dom = visits.index[visits["tipo"] == "domicilio"]
    top = visits.loc[dom].sort_values("penalidade", ascending=False).index[:n_candidatas]
    visits["candidata"] = visits.index.isin(top) | visits["urgente"]
    visits = gpd.GeoDataFrame(visits, geometry=[Point(G.nodes[n]["x"], G.nodes[n]["y"]) for n in visits["node"]], crs=crs)

    # saída
    out = OUT_DIR / name
    out.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(ox.project_graph(G, to_latlong=True), out / "graph.graphml")
    for f in ["instance.gpkg", "candidatas.gpkg"]:
        (out / f).unlink(missing_ok=True)
    v_ll = visits.to_crs(4326)
    v_ll.to_file(out / "instance.gpkg", layer="visits")
    setores[["CD_SETOR", "NM_BAIRRO", "v0001", "v0007", "geometry"]].to_crs(4326).to_file(out / "instance.gpkg", layer="microarea")
    v_ll[(v_ll["tipo"] == "ubs") | v_ll["candidata"]].reset_index(drop=True).to_file(out / "candidatas.gpkg", layer="visits")

    d = visits[visits["tipo"] == "domicilio"]
    meta = {
        "nome": name, "seed": seed,
        "ubs": {"lat": ubs_latlon[0], "lon": ubs_latlon[1]},
        "microarea": {
            "setores": setores["CD_SETOR"].tolist(),
            "bairros": sorted(setores["NM_BAIRRO"].dropna().unique().tolist()),
            "moradores_censo": int(setores["v0001"].sum()),
            "domicilios_censo": n_dom,
            "area_km2": round(microarea.area / 1e6, 3),
        },
        "gerado": {
            "domicilios": len(d),
            "pontos_de_acesso": int(d["node"].nunique()),
            "edificacoes_ocupadas": len(occupied),
            "urgentes": int(d["urgente"].sum()),
            "graves": int(d["grave"].sum()),
            "atrasados": int(d["atrasado"].sum()),
            "com_janela": int((d["tw_end"] - d["tw_start"] < ACS["jornada_max_min"]).sum()),
            "candidatas_do_dia": int(d["candidata"].sum()),
            "soma_duracao_min": int(d["s"].sum()),
        },
        "grafo": {"nos": G.number_of_nodes(), "arestas": G.number_of_edges()},
        "acs": ACS,
        "parametros": {"populacao_alvo": populacao, "p_urgencia": p_urgencia, "atraso_max": atraso_max,
                       "n_candidatas": n_candidatas, "condicoes": CONDICOES},
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    save_map(G, v_ll, setores.to_crs(4326), meta, out / "mapa.html")
    return out, meta


# ==========================================
# Mapa interativo
# ==========================================
CORES_W = {1: "#4daf4a", 2: "#ffcc00", 3: "#ff7f00", 4: "#e41a1c", 5: "#7b0000"}


def save_map(G, visits, setores, meta, path):
    _, edges = ox.graph_to_gdfs(ox.project_graph(G, to_latlong=True))
    c = setores.union_all().centroid
    m = folium.Map([c.y, c.x], zoom_start=17, tiles=None, max_zoom=19)
    osm = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    folium.TileLayer("https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png", name="OSM Humanitarian",
                     attr=f"{osm}, tiles HOT / OSM France", max_zoom=19).add_to(m)
    folium.TileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", name="OSM padrão", attr=osm, max_zoom=19).add_to(m)
    folium.GeoJson(edges[["geometry"]], name="malha a pé", style_function=lambda f: {"color": "#888", "weight": 1}).add_to(m)
    folium.GeoJson(setores, name="setores (microárea)", tooltip=folium.GeoJsonTooltip(["CD_SETOR", "v0001", "v0007"], aliases=["setor", "moradores", "domicílios"]),
                   style_function=lambda f: {"color": "#d7191c", "weight": 2, "fill": False, "dashArray": "6"}).add_to(m)

    layers = {True: folium.FeatureGroup(name="candidatas do dia").add_to(m),
              False: folium.FeatureGroup(name="demais domicílios").add_to(m)}
    dom = visits[visits["tipo"] == "domicilio"]
    for (node, cand), grp in dom.groupby(["node", "candidata"]):
        g = grp.geometry.iloc[0]
        rows = "".join(
            f"<tr><td>{i}</td><td>{r.condicao}</td><td>{r.w}</td><td>{r.P}</td><td>{r.d}</td><td>{r.s}</td>"
            f"<td>{'manhã' if r.tw_end == ACS['jornada_min'] // 2 else 'tarde' if r.tw_start > 0 else '-'}</td>"
            f"<td>{'<b style=color:red>SIM</b>' if r.urgente else ''}</td><td>{r.penalidade:.2f}</td></tr>"
            for i, r in grp.iterrows())
        html = ("<table border=1 style='font-size:11px;border-collapse:collapse'><tr><th>id</th><th>condição</th><th>w</th>"
                f"<th>P</th><th>d</th><th>s</th><th>janela</th><th>urg.</th><th>pen.</th></tr>{rows}</table>")
        w = int(grp["w"].max())
        folium.CircleMarker(
            [g.y, g.x], radius=(6 if cand else 3) + min(len(grp), 10) ** 0.7, color="black",
            weight=3 if grp["urgente"].any() else (1 if cand else 0.3), fill=True, fill_color=CORES_W[w],
            fill_opacity=0.9 if cand else 0.35, popup=folium.Popup(html, max_width=600),
            tooltip=f"{len(grp)} domicílio(s) · w máx {w}{' · URGENTE' if grp['urgente'].any() else ''}",
        ).add_to(layers[cand])
    u = visits.geometry.iloc[0]
    folium.Marker([u.y, u.x], tooltip="UBS", icon=folium.Icon(color="red", icon="plus")).add_to(m)

    mi, ge = meta["microarea"], meta["gerado"]
    cores = "".join(f"<span style='background:{c};display:inline-block;width:11px;height:11px;border:1px solid #333'></span> {k} "
                    for k, c in CORES_W.items())
    legenda = f"""<div style="position:fixed;bottom:20px;left:20px;z-index:9999;background:white;padding:10px;
        border:1px solid #999;font-size:12px;max-width:340px"><b>{meta['nome']}</b> · {', '.join(mi['bairros'])}<br>
        {len(mi['setores'])} setor(es), {mi['area_km2']} km², {mi['moradores_censo']} moradores (Censo 2022)<br>
        {ge['domicilios']} domicílios em {ge['pontos_de_acesso']} pontos de acesso<br>
        atrasados {ge['atrasados']} · graves {ge['graves']} · urgentes {ge['urgentes']} · com janela {ge['com_janela']}<br>
        <b>{ge['candidatas_do_dia']} candidatas do dia</b> (cor forte); demais em transparência<br>
        cor = peso clínico w: {cores}<br>tamanho = nº de domicílios no ponto · borda grossa = urgente</div>"""
    m.get_root().html.add_child(folium.Element(legenda))
    folium.LayerControl().add_to(m)
    m.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ubs", required=True, help="lat,lon da UBS (use --ubs=-30.04,-51.15)")
    ap.add_argument("--name", required=True)
    ap.add_argument("--populacao", type=int, default=750, help="população-alvo da microárea (padrão 750)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--urgencia", type=float, default=0.02, help="prob. de urgência por domicílio com condição")
    ap.add_argument("--atraso", type=float, default=1.5, help="d ~ U(0, atraso × P)")
    ap.add_argument("--candidatas", type=int, default=40, help="nº de candidatas do dia além das urgentes")
    args = ap.parse_args()
    lat, lon = (float(x) for x in args.ubs.split(","))
    out, meta = generate((lat, lon), args.name, args.populacao, args.seed, args.urgencia, args.atraso, args.candidatas)
    print(json.dumps({k: meta[k] for k in ["microarea", "gerado", "grafo"]}, indent=2, ensure_ascii=False))
    print(f"instância salva em {out}")


if __name__ == "__main__":
    main()
