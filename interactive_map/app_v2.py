"""
app_v2.py – Seattle EV Station Explorer  (Version 2)
Run: streamlit run app_v2.py

Main map  : ZIP choropleth (avg_daily_flow) + EV station dots  → click a ZIP
Detail map: real Seattle road lines coloured by avg_daily_flow + EV station dots
Data      : all_variables.csv  +  seattle_streets.geojson  +  ev_station.csv
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go
import streamlit as st

# ── file paths ────────────────────────────────────────────────────────────────
EV_PATH      = "data/cleaned/ev_station.csv"
TRAFFIC_PATH = "data/cleaned/all_variables.csv"
DEMAND_PATH  = "data/cleaned/demand_gap.csv"
ZCTA_PATH    = "data/geo/zcta.json"
STREETS_PATH = "data/geo/seattle_streets.geojson"   # WGS84, Seattle-only, pre-built

st.set_page_config(page_title="Seattle EV Explorer", page_icon="⚡", layout="wide")

# ── ADT colour bins ───────────────────────────────────────────────────────────
ADT_BINS   = [0, 500, 3_800, 6_700, 12_000, float("inf")]
ADT_LABELS = ["< 500", "500 – 3.8K", "3.8K – 6.7K", "6.7K – 12K", "> 12K"]
ADT_COLORS = ["#93c5fd", "#3b82f6", "#1d4ed8", "#1e3a8a", "#172554"]
ADT_WIDTHS = [2.0, 3.0, 4.0, 5.0, 6.5]

# ─────────────────────────────────────────────────────────────────────────────
# Data functions
# ─────────────────────────────────────────────────────────────────────────────

def load_ev_stations() -> pd.DataFrame:
    """
    Load and filter EV charging station data for Washington state.
    
    Reads a CSV file containing EV charging station information, filters for
    Washington state locations, and performs data cleaning operations.
    
    Returns:
        pd.DataFrame: A cleaned dataframe containing WA state EV stations
    """
    cols = [
        "Station Name", "Latitude", "Longitude", "ZIP", "State",
        "EV Level2 EVSE Num", "EV DC Fast Count", "EV Network",
    ]
    df = pd.read_csv(EV_PATH, usecols=cols, low_memory=False)
    df = df[df["State"] == "WA"].dropna(subset=["Latitude", "Longitude"]).copy()
    df["ZIP"] = df["ZIP"].astype(str).str.zfill(5)
    df["EV Level2 EVSE Num"] = df["EV Level2 EVSE Num"].fillna(0)
    df["EV DC Fast Count"]   = df["EV DC Fast Count"].fillna(0)
    return df


def fix_missing_zips(ev_df: pd.DataFrame, zcta_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Correct invalid ZIP codes by spatially matching EV station coordinates to ZCTA boundaries.
    
    Args:
        ev_df: EV stations DataFrame with 'ZIP', 'Latitude', 'Longitude' columns
        zcta_gdf: GeoDataFrame of ZIP Code Tabulation Areas with 'ZIP_zcta' column
    
    Returns:
        pd.DataFrame: Copy of ev_df with corrected ZIP codes where possible
    """
    valid_zips   = set(zcta_gdf["ZIP_zcta"])
    missing_mask = ~ev_df["ZIP"].isin(valid_zips)
    if not missing_mask.any():
        return ev_df
    pts = gpd.GeoDataFrame(
        ev_df[missing_mask].copy(),
        geometry=gpd.points_from_xy(
            ev_df.loc[missing_mask, "Longitude"],
            ev_df.loc[missing_mask, "Latitude"],
        ),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(pts, zcta_gdf, how="left", predicate="within")
    remap  = joined["ZIP_zcta"].dropna()
    ev_df  = ev_df.copy()
    ev_df.loc[remap.index, "ZIP"] = remap.values
    return ev_df


def aggregate_ev_by_zip(ev_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate EV charging stations by ZIP code.
    
    Returns:
        pd.DataFrame: Counts of stations, Level 2 ports, and DC fast chargers per ZIP
    """
    return (
        ev_df.groupby("ZIP")
        .agg(
            station_count=("Station Name",       "count"),
            level2_spots =("EV Level2 EVSE Num", "sum"),
            dcfast_count =("EV DC Fast Count",   "sum"),
        )
        .reset_index()
    )

def aggregate_traffic_from_csv() -> pd.DataFrame:
    """
    Load and aggregate traffic data by ZIP code.
    
    Reads traffic flow data from CSV, cleans numeric columns, and aggregates
    by ZIP code, computing mean average daily traffic (ADT) and taking first
    values for demographic fields.
    
    Returns:
        pd.DataFrame: Aggregated data
    """
    df = pd.read_csv(TRAFFIC_PATH)
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5)
    # Clean income column (may contain "-" or "**")
    df["Median Household Income"] = pd.to_numeric(
        df["Median Household Income"], errors="coerce"
    )
    df["Total EV Registrations"] = pd.to_numeric(
        df["Total EV Registrations"], errors="coerce"
    )
    return (
        df.groupby("zip_code")
        .agg(
            mean_ADT       =("avg_daily_flow",          "mean"),
            population     =("Population Estimate",     "first"),
            city           =("city",                    "first"),
            med_income     =("Median Household Income", "first"),
            ev_registrations=("Total EV Registrations", "first"),
        )
        .reset_index()
        .rename(columns={"zip_code": "ZIP"})
    )

def load_zcta(path: str = ZCTA_PATH) -> gpd.GeoDataFrame:
    """
    Load ZIP Code Tabulation Area (ZCTA) boundaries and calculate areas.
    
    Reads ZCTA shapefile, standardizes ZIP codes, and computes area in square miles
    using Washington State North projection (EPSG:2285) for accuracy.
    
    Args:
        path: Path to ZCTA shapefile (default: ZCTA_PATH)
    
    Returns:
        gpd.GeoDataFrame: ZCTA data 
    """
    gdf = gpd.read_file(path)
    if gdf is None or gdf.empty:
        st.error(f"Error: The ZCTA file at {path} is empty or could not be read.")
        return gpd.GeoDataFrame()
    zip_col = "ZCTA5CE10" if "ZCTA5CE10" in gdf.columns else "GEOID10"
    gdf["ZIP_zcta"] = gdf[zip_col].astype(str).str.zfill(5)

    # Calculate area in sq miles
    # Project to WA North for accurate area calculation
    gdf_projected = gdf.to_crs(epsg = 2285)
    gdf["area_sq_mi"] = gdf_projected["geometry"].area / 27878400
    return gdf[["ZIP_zcta", "geometry", "area_sq_mi"]].set_crs("EPSG:4326", allow_override=True)

def build_master(ev_df, traffic_df) -> pd.DataFrame:
    """
    Merge traffic and EV station data by ZIP code.
    
    Left joins traffic data with EV station aggregates, filling missing
    station counts with zeros for ZIPs without charging stations.
    
    Args:
        ev_df: EV station data aggregated by ZIP
        traffic_df: Traffic and demographic data by ZIP
    
    Returns:
        pd.DataFrame: Combined dataset with traffic metrics and EV station counts
    """
    master = traffic_df.merge(ev_df, on="ZIP", how="left")
    master["station_count"] = master["station_count"].fillna(0)
    master["level2_spots"]  = master["level2_spots"].fillna(0)
    master["dcfast_count"]  = master["dcfast_count"].fillna(0)
    return master


def build_geojson(zcta_gdf: gpd.GeoDataFrame, zip_set: set) -> dict:
    """
    Convert ZCTA geometries to GeoJSON for a subset of ZIP codes.
    
    Args:
        zcta_gdf: GeoDataFrame of ZCTA boundaries
        zip_set: Set of ZIP codes to include
    
    Returns:
        dict: GeoJSON FeatureCollection with ZIP boundaries
    """
    subset = zcta_gdf[zcta_gdf["ZIP_zcta"].isin(zip_set)]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": row["ZIP_zcta"],
                "properties": {"ZIP": row["ZIP_zcta"]},
                "geometry": row["geometry"].__geo_interface__,
            }
            for _, row in subset.iterrows()
        ],
    }

# ─────────────────────────────────────────────────────────────────────────────
# Cached loaders
# ─────────────────────────────────────────────────────────────────────────────

def load_demand_gap() -> pd.DataFrame:
    """
    Load EV charging demand gap data by ZIP code.
    
    Returns:
        pd.DataFrame: ZIP codes with demand_gap values
    """
    df = pd.read_csv(DEMAND_PATH)
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5)
    return df[["zip_code", "demand_gap"]].rename(columns={"zip_code": "ZIP"})


@st.cache_data(show_spinner="Loading data…")
def load_all():
    """
    Load and merge all datasets: ZCTA boundaries, EV stations, traffic, and demand gap.
    
    Returns:
        tuple: (zcta_gdf, ev_df, scored) where scored is the master dataset with
               traffic, demographics, EV stations, population density, and demand gap
    """
    zcta_gdf  = load_zcta()
    if zcta_gdf is None or zcta_gdf.empty:
        st.error("Critical Error: ZCTA data is missing. Check your file paths.")
        st.stop()
    ev_raw = load_ev_stations()
    ev_df = fix_missing_zips(ev_raw, zcta_gdf)
    ev_by_zip = aggregate_ev_by_zip(ev_df)
    t_by_zip = aggregate_traffic_from_csv()
    scored = build_master(ev_by_zip, t_by_zip)
    scored = scored.merge(zcta_gdf[["ZIP_zcta", "area_sq_mi"]],
                          left_on="ZIP", right_on="ZIP_zcta", how="left")
    scored["pop_density"] = scored["population"] / scored["area_sq_mi"].replace(0, np.nan)
    demand_df = load_demand_gap()
    scored = scored.merge(demand_df, on="ZIP", how="left")
    return zcta_gdf, ev_df, scored


@st.cache_data(show_spinner="Loading road network…")
def load_streets_with_adt() -> gpd.GeoDataFrame:
    """
    Load Seattle street center lines (WGS84) and join avg_daily_flow
    from all_variables.csv by (ZIP, street_name).
    Returns GeoDataFrame with columns: ORD_STNAME_CONCAT, L_ZIP, R_ZIP,
    ARTERIAL_CODE, adt_l, adt_r, geometry.
    """
    streets = gpd.read_file(STREETS_PATH)
    streets["L_ZIP"] = streets["L_ZIP"].astype(str).str.zfill(5)
    streets["R_ZIP"] = streets["R_ZIP"].astype(str).str.zfill(5)

    # Build ADT lookup: (zip_code, street_name) → avg_daily_flow
    df = pd.read_csv(TRAFFIC_PATH)
    df["zip_code"]    = df["zip_code"].astype(str).str.zfill(5)
    df["street_name"] = df["STDY_TITLE_PART"].str.split(",").str[0].str.strip()
    agg = (
        df.groupby(["zip_code", "street_name"])["avg_daily_flow"]
        .mean()
        .reset_index()
    )

    # Join from the left side (L_ZIP)
    m_l = streets.merge(
        agg.rename(columns={"zip_code": "_zl", "street_name": "_sl", "avg_daily_flow": "adt_l"}),
        left_on=["L_ZIP", "ORD_STNAME_CONCAT"],
        right_on=["_zl", "_sl"],
        how="left",
    ).drop(columns=["_zl", "_sl"], errors="ignore")

    # Join from the right side (R_ZIP)
    m_r = streets.merge(
        agg.rename(columns={"zip_code": "_zr", "street_name": "_sr", "avg_daily_flow": "adt_r"}),
        left_on=["R_ZIP", "ORD_STNAME_CONCAT"],
        right_on=["_zr", "_sr"],
        how="left",
    ).drop(columns=["_zr", "_sr"], errors="ignore")

    streets = streets.copy()
    streets["adt_l"] = m_l["adt_l"].values
    streets["adt_r"] = m_r["adt_r"].values
    return streets


@st.cache_data(show_spinner=False)
def cached_geojson(_zcta_gdf, zip_tuple):
    """Build GeoJSON for a set of ZIP codes with caching."""
    return build_geojson(_zcta_gdf, set(zip_tuple))


@st.cache_data(show_spinner=False)
def cached_road_fig(zip_code, _streets_gdf, _zcta_gdf, _ev_df):
    """Build road map figure for a ZIP code with caching."""
    return build_road_map(zip_code, _streets_gdf, _zcta_gdf, _ev_df)


@st.cache_data(show_spinner=False)
def single_zip_geojson(_zcta_gdf, zip_code):
    """Return GeoJSON for a single ZIP code boundary."""
    if _zcta_gdf is None or _zcta_gdf.empty:
        return None
    gdf = _zcta_gdf.copy()
    gdf["ZIP_zcta"] = gdf["ZIP_zcta"].astype(str)
    zip_code = str(zip_code)
    row = _zcta_gdf[_zcta_gdf["ZIP_zcta"] == zip_code]
    if row.empty:
        return None
    r = row.iloc[0]
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "id": zip_code,
            "properties": {},
            "geometry": r["geometry"].__geo_interface__,
        }],
    }


@st.cache_data(show_spinner=False)
def zip_centroid(_zcta_gdf, zip_code):
    """Get the centroid coordinates for a ZIP code."""
    row = _zcta_gdf[_zcta_gdf["ZIP_zcta"] == zip_code]
    if row.empty:
        return {"lat": 47.61, "lon": -122.33}
    c = row.iloc[0]["geometry"].centroid
    return {"lat": c.y, "lon": c.x}

@st.cache_data(show_spinner=False)
def get_eval_map_base(_zcta_gdf, zip_tuple):
    """Generates static background of the evaluation map."""
    fig = go.Figure()
    fig.add_trace(go.Choroplethmapbox(
        geojson = build_geojson(_zcta_gdf, set(zip_tuple)),
        locations = list(zip_tuple),
        z = [0] * len(zip_tuple),
        colorscale = [[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
        marker_line_color = "#ccc", marker_line_width = 0.5,
        showscale = False, hoverinfo = "skip"
    ))
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _line_coords(geom):
    """Return (lons, lats) lists for a LineString, with a trailing None separator."""
    coords = list(geom.coords)
    lons = [c[0] for c in coords] + [None]
    lats = [c[1] for c in coords] + [None]
    return lons, lats


def _midpoint(geom):
    """Return (lon, lat) of the middle vertex of a LineString geometry."""
    coords = list(geom.coords)
    mid = coords[len(coords) // 2]
    return mid[0], mid[1]


def get_score_color(score):
    """Returns color based on score thresholds"""
    if score <= 20:
        return "#ef4444"  # Red
    if score <= 40:
        return "#facc15"  # Yellow
    return "#22c55e"  # Green

# ─────────────────────────────────────────────────────────────────────────────
# Main map: ZIP choropleth + EV station dots
# ─────────────────────────────────────────────────────────────────────────────
def build_main_map(ev_df, scored, geojson, selected_zip):
    """
    Builds the main choropleth map showing traffic flow by ZIP and EV stations.
    
    Returns:
        go.Figure: Plotly mapbox figure with traffic choropleth and station markers
    """
    zip_list = scored["ZIP"].tolist()
    sel_idx  = zip_list.index(selected_zip) if selected_zip in zip_list else None

    fig = go.Figure(go.Choroplethmapbox(
        geojson        = geojson,
        locations      = scored["ZIP"],
        z              = scored["mean_ADT"],
        colorscale     = "Oranges",
        zmin           = 0,
        zmax           = scored["mean_ADT"].quantile(0.95),
        marker_opacity = 0.55,
        marker_line_width  = 1.0,
        marker_line_color  = "#888",
        colorbar={
            "title": {"text": "Avg Daily<br>Flow", "font": {"size": 11}},
            "thickness": 12,
            "len": 0.45,
            "x": 1.01
        },
        hovertemplate = (
                        "<b>ZIP %{location}</b><br>"
                        "Avg daily flow: %{z:,.0f}<br>"
                        "<i>Click to explore</i><extra></extra>"),
        name           = "Traffic per ZIP",
        showlegend     = False,
        selectedpoints = [sel_idx] if sel_idx is not None else None,
    ))

    seattle_ev = ev_df[ev_df["ZIP"].isin(set(scored["ZIP"]))].copy()
    fig.add_trace(go.Scattermapbox(
        lat  = seattle_ev["Latitude"],
        lon  = seattle_ev["Longitude"],
        mode = "markers",
        marker = {"size": 6, "color": '#22c55e', "opacity": 0.75},
        text       = seattle_ev["Station Name"],
        customdata = seattle_ev[["ZIP", "EV Level2 EVSE Num",
                                 "EV DC Fast Count", "EV Network"]].values,
        hovertemplate = (
            "<b>%{text}</b><br>"
            "<br>"
            "ZIP:  <b>%{customdata[0]}</b><br>"
            "Level 2 ports:  <b>%{customdata[1]:.0f}</b><br>"
            "DC Fast ports:  <b>%{customdata[2]:.0f}</b><br>"
            "Network:  <b>%{customdata[3]}</b>"
            "<extra></extra>"
        ),
        name       = "EV Station",
        showlegend = True,
        hoverlabel = {"bgcolor": 'white', "bordercolor": '#22c55e', "font": {"size": 13}}
    ))

    fig.update_layout(
        mapbox_style  = "carto-positron",
        mapbox_zoom   = 10.5,
        mapbox_center = {"lat": 47.61, "lon": -122.33},
        margin        = {"l": 0, "r": 0, "t": 0, "b": 0},
        height        = 460,
        showlegend    = True,
        legend        = {"x":0.01, "y":0.99, "bgcolor":'rgba(255,255,255,0.90)',
                             "bordercolor":"#22c55e", "borderwidth":1.5,
                             "font": {"size": 13}},
        uirevision    = "main",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Detail map: real road lines coloured by avg_daily_flow
# ─────────────────────────────────────────────────────────────────────────────
def build_road_map(zip_code, streets_gdf, zcta_gdf, ev_df):  # pylint: disable=too-many-locals  # map-building requires many intermediate GeoDataFrame/trace variables
    """
    Draw Seattle road line segments for the selected ZIP, coloured by
    avg_daily_flow ADT bins.  Background roads (no data) shown in light gray.
    """
    center = zip_centroid(zcta_gdf, zip_code)
    zip_gj = single_zip_geojson(zcta_gdf, zip_code)

    zip_poly = zcta_gdf[zcta_gdf["ZIP_zcta"] == zip_code]
    fig = go.Figure()

    # ZIP boundary fill
    if zip_gj:
        fig.add_trace(go.Choroplethmapbox(
            geojson           = zip_gj,
            locations         = [zip_code],
            z                 = [1],
            colorscale        = [[0, "rgba(250,204,21,0.12)"],
                                  [1, "rgba(250,204,21,0.12)"]],
            marker_opacity    = 1,
            marker_line_width = 0,
            showscale         = False,
            hoverinfo         = "skip",
            name              = "ZIP boundary",
        ))

    if zip_poly.empty:
        fig.update_layout(mapbox_style="carto-positron", mapbox_zoom=13,
                          mapbox_center=center, margin={"l": 0, "r": 0, "t": 0, "b": 0}, height=400)
        return fig

    # Filter street segments that belong to this ZIP (either side)
    mask = (streets_gdf["L_ZIP"] == zip_code) | (streets_gdf["R_ZIP"] == zip_code)
    zip_streets = streets_gdf[mask].copy()

    if zip_streets.empty:
        st.caption("No road data for this ZIP.")
        fig.update_layout(mapbox_style="carto-positron", mapbox_zoom=13,
                          mapbox_center=center, margin={"l": 0, "r": 0, "t": 0, "b": 0}, height=400)
        return fig

    # Pick ADT: prefer the side that matches the selected ZIP
    def _pick_adt(row):
        if row["L_ZIP"] == zip_code and pd.notna(row["adt_l"]):
            return row["adt_l"]
        if row["R_ZIP"] == zip_code and pd.notna(row["adt_r"]):
            return row["adt_r"]
        # fallback: use whichever side has data
        if pd.notna(row["adt_l"]):
            return row["adt_l"]
        if pd.notna(row["adt_r"]):
            return row["adt_r"]
        return np.nan

    zip_streets["plot_adt"] = zip_streets.apply(_pick_adt, axis=1)

    # ── Coloured roads per ADT bin ───────────────────────────────────────────
    with_adt = zip_streets[zip_streets["plot_adt"].notna()]
    for i, (lo, hi) in enumerate(zip(ADT_BINS[:-1], ADT_BINS[1:])):
        subset = with_adt[(with_adt["plot_adt"] >= lo) & (with_adt["plot_adt"] < hi)]
        if subset.empty:
            continue

        # Collect all line coordinates (None-separated)
        lons_line, lats_line = [], []
        for geom in subset.geometry:
            lons, lats = _line_coords(geom)
            lons_line.extend(lons)
            lats_line.extend(lats)

        fig.add_trace(go.Scattermapbox(
            lat=lats_line, lon=lons_line, mode="lines",
            line={"width": ADT_WIDTHS[i], "color": ADT_COLORS[i]},
            name=f"ADT {ADT_LABELS[i]}",
            hoverinfo="skip", showlegend=True,
            legendgroup=f"adt_{i}",
        ))

        # Invisible midpoint markers for hover
        mid_lons = [_midpoint(geom)[0] for geom in subset.geometry]
        mid_lats = [_midpoint(geom)[1] for geom in subset.geometry]
        hover_texts = [
            f"<b>{row['ORD_STNAME_CONCAT']}</b><br>"
            f"ADT: <b>{row['plot_adt']:,.0f}</b> vehicles/day"
            for _, row in subset.iterrows()
        ]
        fig.add_trace(go.Scattermapbox(
            lat=mid_lats, lon=mid_lons, mode="markers",
            marker={"size":16, "color":ADT_COLORS[i], "opacity":0},
            text=hover_texts,
            hovertemplate="%{text}<extra></extra>",
            hoverlabel={"namelength": -1, "font": {"size": 12}, "bgcolor": 'white'},
            name=f"ADT {ADT_LABELS[i]}", showlegend=False,
            legendgroup=f"adt_{i}",
        ))

    # ── EV station dots ──────────────────────────────────────────────────────
    ev_zip = ev_df[ev_df["ZIP"] == zip_code]
    if not ev_zip.empty:
        fig.add_trace(go.Scattermapbox(
            lat  = ev_zip["Latitude"],
            lon  = ev_zip["Longitude"],
            mode = "markers",
            marker = {
                "size": 9,
                "color": "#22c55e",
                #"line": {
                    #"width": 1.5,
                    #"color": "white"
                #}
            },
            text       = ev_zip["Station Name"],
            customdata = ev_zip[["EV Level2 EVSE Num", "EV DC Fast Count", "EV Network"]].values,
            hovertemplate = (
                "<b>%{text}</b><br>"
                "<br>"
                "Level 2 ports:  <b>%{customdata[0]:.0f}</b><br>"
                "DC Fast ports:  <b>%{customdata[1]:.0f}</b><br>"
                "Network:  <b>%{customdata[2]}</b>"
                "<extra></extra>"
            ),
            name = "EV Station",
            hoverlabel = {"bgcolor": 'white', "bordercolor": '#22c55e', "font": dict(size=13)},
        ))

    fig.update_layout(
        mapbox_style  = "carto-positron",
        mapbox_zoom   = 13.0,
        mapbox_center = center,
        margin        = {"l": 0, "r": 0, "t": 0, "b": 0},
        height        = 400,
        legend        = {
            "title": {'text': 'ADT (vehicles/day)', 'font': {'size': 11}}, 
            "x": 0.01, "y": 0.99,
            "bgcolor" :"rgba(255,255,255,0.88)",
            "bordercolor": "#ddd", 
            "borderwidth": 1,
            "font": {"size": 11},
            "itemclick": False,
            "itemdoubleclick": False,}
        )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Map fragment
# ─────────────────────────────────────────────────────────────────────────────
@st.fragment
def map_fragment():  # pylint: disable=too-many-nested-blocks  # click-event handling requires nested if/for inside st.fragment
    """Streamlit fragment that renders the interactive overview map and handles ZIP click events."""
    zcta_gdf, ev_df, scored = load_all()
    valid_zips  = set(scored["ZIP"])
    overview_gj = cached_geojson(zcta_gdf, tuple(sorted(valid_zips)))
    chart_key   = f"main_map_{st.session_state.get('map_version', 0)}"

    _pre = st.session_state.get(chart_key)
    if _pre is not None:
        _pts = getattr(getattr(_pre, "selection", None), "points", None) or []
        if _pts:
            pt = _pts[0]
            ek = repr(pt)
            if ek != st.session_state.get("last_event_key"):
                st.session_state.last_event_key = ek
                raw = pt.get("location")
                if raw is None:
                    cd = pt.get("customdata")
                    if cd:
                        raw = cd[0]
                if raw:
                    new_zip = str(raw).zfill(5)
                    if new_zip in valid_zips:
                        if new_zip != st.session_state.get("selected_zip"):
                            st.session_state.selected_zip = new_zip
                            st.rerun(scope="app")

    sel = st.session_state.get("selected_zip")
    main_fig = build_main_map(ev_df, scored, overview_gj, sel)
    st.plotly_chart(
        main_fig,
        use_container_width = True,
        config    = {"scrollZoom": True},
        on_select = "rerun",
        key       = chart_key,
    )


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────
def main():  # pylint: disable=too-many-locals,too-many-statements  # Streamlit page layout requires many local variables and render calls in one function
    """Entry point: initialise session state, render page title, and build the two-tab layout."""
    zcta_gdf, ev_df, scored = load_all()
    streets_gdf = load_streets_with_adt()
    valid_zips  = set(scored["ZIP"])

    for key, default in [("selected_zip", None), ("map_version", 0),
                         ("last_event_key", None)]:
        if key not in st.session_state:
            st.session_state[key] = default

    sel = st.session_state.selected_zip

    st.title("⚡ Seattle EV Station Explorer")

    tab1, tab2 = st.tabs(["📍 Location", "⭐ Evaluation"])

    # ── Tab 1: Location ───────────────────────────────────────────────────────
    with tab1:
        st.info(
            "**How to use this map**  \n"
            "- The left map shows **average daily traffic flow** by ZIP code — "
            "darker orange = higher traffic.  \n"
            "- Green dots are **EV charging stations**. Hover over a dot to see "
            "station details.  \n"
            "- **Click any ZIP area or station** to load the road network map and "
            "charging stats on the right.",
            icon="ℹ️",
        )
        left_col, right_col = st.columns([1, 1], gap="medium")

        with left_col:
            zip_options = [None] + sorted(valid_zips)
            zip_select  = st.selectbox(
                "Enter ZIP code",
                options     = zip_options,
                index       = zip_options.index(sel) if sel in zip_options else 0,
                format_func = lambda z: "— Select ZIP —" if z is None else z,
                placeholder = "Type to search…",
            )
            if zip_select and zip_select != sel:
                st.session_state.selected_zip   = zip_select
                st.session_state.last_event_key = None
                st.rerun()
            elif zip_select is None and sel is not None:
                st.session_state.selected_zip   = None
                st.session_state.last_event_key = None
                st.session_state["map_version"] += 1
                st.rerun()
            map_fragment()

        with right_col:
            if sel:
                scored_row = scored[scored["ZIP"] == sel]
                ev_in_zip  = ev_df[ev_df["ZIP"] == sel]
                city_val   = scored_row["city"].iloc[0] if not scored_row.empty else "—"
                pop_val    = int(scored_row["population"].iloc[0]) if not scored_row.empty else None
                #demand_val = scored_row["demand_gap"].iloc[0] if not scored_row.empty else None

                hdr_col, btn_col = st.columns([5, 1])
                hdr_col.markdown(f"### {city_val} · ZIP {sel}")
                if btn_col.button("✕ Clear", use_container_width=True):
                    st.session_state.selected_zip   = None
                    st.session_state.last_event_key = None
                    st.session_state["map_version"] += 1
                    st.rerun()

                # Road map
                st.markdown(
                    "**Road traffic volume** (ADT – Average Daily Traffic)",
                    help=(
                        "ADT = avg_daily_flow aggregated from Seattle 2025–2026 traffic "
                         "study data. Road lines are coloured by measured traffic volume. "
                        "Gray lines have no traffic measurement data."
                    )
                )
                road_fig = cached_road_fig(sel, streets_gdf, zcta_gdf, ev_df)
                st.plotly_chart(road_fig, use_container_width=True,
                                config={"scrollZoom": True})

                # Stats — 3 cols × 2 rows
                c1, c2, c3 = st.columns(3)
                c1.metric("Population",    f"{pop_val:,}" if pop_val else "N/A")
                c2.metric("Stations",      len(ev_in_zip))
                c3.metric("Level2 Spots",  int(ev_in_zip["EV Level2 EVSE Num"].sum()),
                          help="Level 2 AC charging ports (240V). Typical charge time: 4–12 hrs.")

                c4, c5, _ = st.columns(3)
                c4.metric("DC Fast Spots", int(ev_in_zip["EV DC Fast Count"].sum()),
                          help="DC Fast Charging ports (50–350+ kW). Charge to ~80% in 20–45 min.")
                if not scored_row.empty:
                    c5.metric(
                        "Avg Daily Flow",
                        f"{scored_row['mean_ADT'].iloc[0]:,.0f}",
                        help=(
                            "Average of avg_daily_flow across all roads "
                            "measured in this ZIP."
                        )
                    )
                # Station table
                st.markdown(f"**Stations in ZIP {sel}**")
                if not ev_in_zip.empty:
                    disp = {
                        "Station Name":      "Station",
                        "EV Level2 EVSE Num":"Level2",
                        "EV DC Fast Count":  "DC Fast",
                        "EV Network":        "Network",
                    }
                    st.dataframe(
                        ev_in_zip[list(disp)].rename(columns=disp)
                            .sort_values("Level2", ascending=False)
                            .reset_index(drop=True),
                        use_container_width=True,
                        height=200,
                    )
                else:
                    st.info("No stations in this ZIP.")

            else:
                st.markdown("### Click a ZIP to explore")
                st.markdown(
                    "Select any ZIP code on the map to see road traffic, population, "
                    "and charging station details."
                    )
                st.divider()
                seattle_ev = ev_df[ev_df["ZIP"].isin(valid_zips)]
                st.markdown("**City-wide summary**")
                r1c1, r1c2 = st.columns(2)
                r1c1.metric("ZIPs with data",     len(valid_zips))
                r1c2.metric("Total EV Stations",   len(seattle_ev))
                r2c1, r2c2 = st.columns(2)
                r2c1.metric("Total Level2 Spots",  int(seattle_ev["EV Level2 EVSE Num"].sum()),
                            help="Level 2 AC charging ports (240V). Typical charge time: 4–12 hrs.")
                r2c2.metric("Total DC Fast Spots", int(seattle_ev["EV DC Fast Count"].sum()),
                            help= (
                            "DC Fast Charging ports (50–350+ kW). "
                            "Charge to ~80% in 20–45 min."
                            )
                )
        st.caption("Data sources: Traffic flow and demographics "
                   " from Seattle 2025–2026 traffic study. "
                   "Road network from Seattle Open Data (Street Network Database). "
                   "EV station data from AFDC (Alternative Fuels Data Center).")

    # ── Tab 2: Evaluation ─────────────────────────────────────────────────────
    with tab2:
        st.markdown("### Evaluate EV Charging Station Placement")
        st.info(
            "Rate the quality of existing EV station placements based on traffic, "
            "population, and demand.",
            icon="⭐",
        )

        eval_left, eval_right = st.columns([1, 1], gap="medium")

        with eval_left:
            st.markdown("**Scoring Weights**")
            w_traffic = st.slider("Traffic (Avg Daily Flow)", 0, 10, 5)
            # w_pop     = st.slider("Population",               0, 10, 5)
            w_dens    = st.slider("Population Density",       0, 10, 5)
            w_demand  = st.slider("Demand Gap",               0, 10, 5)
            st.divider()
        t_w = w_traffic + w_dens + w_demand or 1
        adt_n = (
            (scored["mean_ADT"] - scored["mean_ADT"].min())
            / (scored["mean_ADT"].max() - scored["mean_ADT"].min() + 1e-9)
        )
        dens_n = (
            (scored["pop_density"] - scored["pop_density"].min())
            / (scored["pop_density"].max() - scored["pop_density"].min() + 1e-9)
        )
        dem_n = (
            (scored["demand_gap"] - scored["demand_gap"].min())
            / (scored["demand_gap"].max() - scored["demand_gap"].min() + 1e-9)
        )
        # temp_scored["Zip_Score"]=
            # (w_traffic * adt_n + w_dens * dens_n + w_demand * dem_n)/t_w * 100
        # zip_scores((((w_traffic * adt_n + w_dens * dens_n + w_demand * dem_n) / t_w * 100)))

        # Calculate scores & create lookup for stations
        calc_scores = (
            ((w_traffic * adt_n + w_dens * dens_n + w_demand * dem_n) / t_w * 100).round(1)
        )
        score_lookup = dict(zip(scored["ZIP"], calc_scores))

        with eval_left:
            # 2. Map scores to stations based on ZIP
            station_scores =  ev_df["ZIP"].map(score_lookup).fillna(0)
            station_colors = [get_score_color(s) for s in station_scores]
            # Build map using cached background
            base_fig = get_eval_map_base(zcta_gdf, tuple(sorted(valid_zips)))
            eval_fig = go.Figure(base_fig)

            eval_fig.add_trace(go.Scattermapbox(
                lat = ev_df["Latitude"],
                lon = ev_df["Longitude"],
                mode = "markers",
                marker = {"size": 8, "color": station_colors, "opacity": 0.8},
                text = ev_df["Station Name"],
                customdata = station_scores,
                hovertemplate = "<b>%{text}</b><br>ZIP Score: %{customdata}<extra></extra>"
            ))
            eval_fig.update_layout(
                mapbox_style = "carto-positron",
                mapbox_zoom = 10,
                mapbox_center = {"lat": 47.61, "lon": -122.33},
                margin = {"l": 0, "r": 0, "t": 0, "b": 0}, height=500,
                uirevision = "eval_map"
            )
            st.plotly_chart(eval_fig, use_container_width=True)
            # Simple Legend
            st.caption("Red: 0-20 (Low Quality/High Demand) |"
                       " Yellow: 21-40 | Green: 41+ (High Quality/Balanced)")

        with eval_right:
            st.markdown("**Station Scores by ZIP**")
            # Placeholder scoring table
            eval_df = scored[["ZIP", "city", "mean_ADT", "population",
                              "pop_density", "demand_gap", "station_count"]].copy()
            # total_w = w_traffic + w_pop + w_demand or 1
            eval_df["Score"] = eval_df["ZIP"].map(score_lookup)
            eval_df = eval_df.rename(columns={
            "city": "City", 
            "mean_ADT": "Avg Daily Flow", 
            "population":"Population",
            "pop_density": "Density (sq/mi)", 
            "station_count": "Stations"
            })
            cols = ["ZIP", "City", "Avg Daily Flow",
                    "Population", "Density (sq/mi)", "Stations", "Score"]
            st.dataframe(
                eval_df[cols].sort_values("Score", ascending=False).reset_index(drop=True),
                use_container_width=True, height=560
            )
if __name__ == "__main__":
    main()
