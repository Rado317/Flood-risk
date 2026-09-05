"""Service géographique — quartiers d'Antananarivo et risque par zone.

Utilise deux APIs publiques gratuites, sans clé, en remplacement du
raster de hazard (.tif) que le projet n'a pas :
- Overpass API (OSM) pour les limites de quartiers/fokontany.
- Open-Elevation pour l'altitude, utilisée comme proxy de vulnérabilité
  (zones basses = risque surclassé). C'est une approximation à documenter
  comme choix méthodologique dans le mémoire, pas une donnée de hazard.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger("flood-risk-api.geo")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"

# Cache mémoire simple : les limites de quartiers ne changent pas d'un
# appel à l'autre, inutile de re-solliciter Overpass à chaque prédiction.
_quartiers_cache: Optional[list[dict]] = None


def _compute_centroid(members: list[dict]) -> Optional[tuple[float, float]]:
    coords = []
    for m in members:
        if "geometry" in m:
            coords.extend((pt["lat"], pt["lon"]) for pt in m["geometry"])
        elif "lat" in m:
            coords.append((m["lat"], m["lon"]))
    if not coords:
        return None
    lat = sum(c[0] for c in coords) / len(coords)
    lon = sum(c[1] for c in coords) / len(coords)
    return lat, lon


async def get_quartiers_antananarivo() -> list[dict]:
    """Récupère (et met en cache) les quartiers via Overpass API.

    admin_level=9 correspond en général aux fokontany à Madagascar dans
    OSM — vérifie sur overpass-turbo.eu que ça matche ta zone, sinon
    ajuste ce niveau (8 ou 10 selon la couverture locale).
    """
    global _quartiers_cache
    if _quartiers_cache is not None:
        return _quartiers_cache

    query = """
    [out:json][timeout:25];
    area["name"="Antananarivo"]->.searchArea;
    relation["boundary"="administrative"]["admin_level"="9"](area.searchArea);
    out body geom;
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(OVERPASS_URL, data={"data": query})
            r.raise_for_status()
            elements = r.json()["elements"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Overpass indisponible : %s", exc)
        return []

    quartiers = []
    for el in elements:
        name = el.get("tags", {}).get("name", "Quartier inconnu")
        centroid = _compute_centroid(el.get("members", []))
        if centroid:
            quartiers.append({"name": name, "lat": centroid[0], "lon": centroid[1]})

    _quartiers_cache = quartiers
    return quartiers


async def get_elevations(points: list[tuple[float, float]]) -> list[Optional[float]]:
    """Interroge Open-Elevation (gratuite, sans clé) pour une liste de (lat, lon)."""
    if not points:
        return []
    locations = [{"latitude": lat, "longitude": lon} for lat, lon in points]
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(ELEVATION_URL, json={"locations": locations})
            r.raise_for_status()
            return [res["elevation"] for res in r.json()["results"]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Elevation indisponible : %s", exc)
        return [None] * len(points)