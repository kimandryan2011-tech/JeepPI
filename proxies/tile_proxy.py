#!/usr/bin/env python3
import sys
import requests
from flask import Flask, Response, make_response

app = Flask(__name__)

OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"


@app.route("/tiles/<int:z>/<int:x>/<int:y>.png")
def tiles(z, x, y):
    url = OSM_URL.format(z=z, x=x, y=y)

    try:
        r = requests.get(url, timeout=10)
    except Exception as e:
        print("Tile fetch error:", e, file=sys.stderr, flush=True)
        return make_response("Tile error", 500)

    if r.status_code != 200:
        print("Tile upstream error:", r.status_code, file=sys.stderr, flush=True)
        return make_response("Upstream error", 500)

    resp = make_response(r.content)
    resp.headers["Content-Type"] = "image/png"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


if __name__ == "__main__":
    print("Tile proxy running on http://127.0.0.1:5000/tiles/{z}/{x}/{y}.png")
    app.run(host="127.0.0.1", port=5000, debug=True)
