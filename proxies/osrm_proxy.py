#!/usr/bin/env python3
import sys
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Online OSRM demo server
OSRM_URL = (
    "https://router.project-osrm.org/route/v1/driving/"
    "{start_lon},{start_lat};{end_lon},{end_lat}"
    "?overview=full&geometries=geojson&steps=true"
)


@app.route("/route", methods=["GET", "OPTIONS"])
def route():
    # CORS preflight
    if request.method == "OPTIONS":
        return ("", 204)

    start = request.args.get("start", "")
    end = request.args.get("end", "")

    try:
        start_lon, start_lat = [float(x) for x in start.split(",")]
        end_lon, end_lat = [float(x) for x in end.split(",")]
    except Exception as e:
        print("Bad start/end params:", start, end, e, file=sys.stderr, flush=True)
        return jsonify({"code": "Invalid", "message": "Bad start/end"}), 400

    url = OSRM_URL.format(
        start_lon=start_lon,
        start_lat=start_lat,
        end_lon=end_lon,
        end_lat=end_lat,
    )

    try:
        r = requests.get(url, timeout=10)
    except requests.RequestException as e:
        print("OSRM request error:", e, file=sys.stderr, flush=True)
        return jsonify({"code": "Error", "message": "Upstream error"}), 502

    if r.status_code != 200:
        print(
            "OSRM upstream HTTP error:",
            r.status_code,
            r.text[:200],
            file=sys.stderr,
            flush=True,
        )
        return jsonify({"code": "Error", "message": "Upstream status"}), 502

    try:
        data = r.json()
    except ValueError as e:
        print("OSRM JSON parse error:", e, file=sys.stderr, flush=True)
        return jsonify({"code": "Error", "message": "Bad JSON"}), 502

    print(
        f"[OSRM] start={start} end={end} code={data.get('code')}",
        file=sys.stderr,
        flush=True,
    )
    return jsonify(data)


@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


if __name__ == "__main__":
    print("OSRM proxy listening on http://127.0.0.1:5003/route")
    app.run(host="127.0.0.1", port=5003, debug=True)
