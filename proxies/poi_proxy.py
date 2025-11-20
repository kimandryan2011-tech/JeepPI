#!/usr/bin/env python3
import time
import math
import logging
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("poi_proxy")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

_last_query_time = 0.0

@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return resp

def build_query(name, lat, lon, radius_m):
    # Simple: look for anything with name matching around the point
    # You can refine to amenity/shop later.
    q = f"""
[out:json][timeout:10];
(
  node["name"~"{name}", i](around:{radius_m},{lat},{lon});
  way["name"~"{name}", i](around:{radius_m},{lat},{lon});
  relation["name"~"{name}", i](around:{radius_m},{lat},{lon});
);
out center 20;
"""
    return q

@app.route("/poi")
def poi_search():
    global _last_query_time

    q = (request.args.get("q") or "").strip()
    lat = request.args.get("lat", "").strip()
    lon = request.args.get("lon", "").strip()
    radius_km = float(request.args.get("radius_km", "25"))

    if not q or not lat or not lon:
        return jsonify([])

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except ValueError:
        return jsonify([])

    radius_m = int(radius_km * 1000)
    logger.info("POI query %r lat=%s lon=%s radius=%dm", q, lat, lon, radius_m)

    # simple local rate limiting: 1 Overpass request every 10s max
    now = time.time()
    if now - _last_query_time < 10:
        logger.info("Skipping Overpass (rate limit)")
        return jsonify([])

    query = build_query(q, lat_f, lon_f, radius_m)

    try:
        r = requests.post(
            OVERPASS_URL,
            data=query.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
            timeout=15,
        )
        if r.status_code == 429:
            logger.error("Overpass 429 Too Many Requests")
            return jsonify([])
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.error("Overpass request failed: %s", exc)
        return jsonify([])

    _last_query_time = now

    elements = data.get("elements", [])
    results = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        if "lat" in el and "lon" in el:
            lat_c = el["lat"]
            lon_c = el["lon"]
        else:
            center = el.get("center")
            if not center:
                continue
            lat_c = center.get("lat")
            lon_c = center.get("lon")
        if lat_c is None or lon_c is None:
            continue

        results.append(
            {
                "name": name,
                "display_name": name,
                "lat": lat_c,
                "lon": lon_c,
            }
        )

    logger.info("POI -> %d results", len(results))
    return jsonify(results)

if __name__ == "__main__":
    logger.info("POI proxy (Overpass) listening on http://127.0.0.1:5005/poi")
    app.run(host="127.0.0.1", port=5005)
