#!/usr/bin/env python3
import os
import math
import logging
from flask import Flask, request, jsonify, make_response
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("geocode_proxy")

MAPTILER_KEY = os.environ.get("MAPTILER_API_KEY", "APIKEY")
UPSTREAM_URL = "https://api.maptiler.com/geocoding/{query}.json"

def haversine_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return resp

@app.route("/geocode")
def geocode():
    q = request.args.get("q", "").strip()
    lat = request.args.get("lat", "").strip()
    lon = request.args.get("lon", "").strip()

    if not q:
        return jsonify([])

    params = {
        "key": MAPTILER_KEY,
        "limit": 5,
    }

    bbox = None
    if lat and lon:
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            dlat = 0.75
            dlon = 0.75
            south = lat_f - dlat
            north = lat_f + dlat
            west = lon_f - dlon
            east = lon_f + dlon
            bbox = f"{west},{south},{east},{north}"
            params["country"] = "US"
            params["bbox"] = bbox
        except ValueError:
            pass

    url = UPSTREAM_URL.format(query=requests.utils.quote(q))
    logger.info(
        "Geocode upstream%s: %s params=%s",
        " (bbox)" if bbox else "",
        url,
        params,
    )
    r = requests.get(url, params=params, timeout=5)
    r.raise_for_status()
    raw = r.json()

    feats = raw.get("features", [])
    results = []
    for f in feats:
        geom = f.get("geometry") or {}
        coords = geom.get("coordinates") or [None, None]
        lon_f, lat_f = coords[0], coords[1]
        if lon_f is None or lat_f is None:
            continue

        props = f.get("properties") or {}
        label = props.get("label") or f.get("place_name") or f.get("text") or q

        entry = {
            "name": label,
            "display_name": label,
            "lat": lat_f,
            "lon": lon_f,
        }

        if lat and lon:
            try:
                entry["_distance"] = haversine_meters(float(lat), float(lon), lat_f, lon_f)
            except Exception:
                entry["_distance"] = None

        results.append(entry)

    if lat and lon:
        results.sort(
            key=lambda e: e.get("_distance", float("inf"))
            if e.get("_distance") is not None else float("inf")
        )

    for e in results:
        e.pop("_distance", None)

    logger.info(
        "[Geocode] q=%r lat=%r lon=%r -> %d results%s",
        q, lat, lon, len(results),
        " (bbox)" if bbox else "",
    )

    resp = make_response(jsonify(results))
    return resp

if __name__ == "__main__":
    logger.info("Geocode proxy (MapTiler) listening on http://127.0.0.1:5002/geocode")
    app.run(host="127.0.0.1", port=5002)
