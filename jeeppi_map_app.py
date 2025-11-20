#!/usr/bin/env python3
import os
import sys
import threading
import http.server
import socketserver
import subprocess
import signal
import time

from PySide6.QtCore import QUrl, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

# ---------- Paths ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "ui")
PROXIES_DIR = os.path.join(BASE_DIR, "proxies")

MAP_HTML_URL = "http://127.0.0.1:5004/map.html"


# ---------- Simple static file server (serves UI_DIR on 5004) ----------

class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # keep stdout fairly clean
        pass


def start_static_server():
    os.chdir(UI_DIR)
    handler = QuietHTTPRequestHandler
    httpd = socketserver.TCPServer(("127.0.0.1", 5004), handler)
    print(f"[JeePi] Static server serving {UI_DIR} on http://127.0.0.1:5004")

    def serve():
        with httpd:
            httpd.serve_forever()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    return httpd


# ---------- Proxy helpers (geocode / osrm) ----------

def start_proxy(name, script_name, port):
    """
    Start a Flask proxy (geocode_proxy.py, osrm_proxy.py)
    in the proxies directory using the same Python interpreter.
    """
    script_path = os.path.join(PROXIES_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"[JeePi][WARN] {name} script not found at {script_path}")
        return None

    cmd = [sys.executable, script_path]

    env = os.environ.copy()

    # Make sure Flask doesn't auto-reload and double-bind the port
    env["FLASK_ENV"] = "production"

    print(f"[JeePi] Starting {name} on port {port}...")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=PROXIES_DIR,
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        return proc
    except Exception as e:
        print(f"[JeePi][ERROR] Failed to start {name}: {e}")
        return None


# ---------- Qt WebEngine GPS map app ----------

class JeepPiWindow(QWebEngineView):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("JeepPI – GPS Map")

        # GPS related
        self.gps_timer = QTimer(self)
        self.gps_timer.timeout.connect(self.update_gps)
        self.gps_timer.start(1000)  # 1s

        # cache last GPS for sanity checks
        self.last_lat = None
        self.last_lon = None

        # Load map HTML from local static server
        print(f"[JeePi] Loading HTML from: {MAP_HTML_URL}")
        self.load(QUrl(MAP_HTML_URL))

        # gpsd connection lazy
        self._gps_connected = False
        self.gpsd = None

    def ensure_gps_connected(self):
        if self._gps_connected:
            return

        try:
            import gpsd

            gpsd.connect()
            self.gpsd = gpsd
            self._gps_connected = True
            print("[JeePi] Connected to gpsd")
        except Exception as e:
            # Only print once to avoid spam
            print(f"[JeePi][WARN] Could not connect to gpsd yet: {e}")
            self._gps_connected = False

    def update_gps(self):
        """
        Called every second. Pulls data from gpsd and forwards location + speed
        into the JS functions defined in map.html:
          - window.setCurrentLocation(lat, lon)
          - window.setSpeedMph(mph)
        """
        try:
            self.ensure_gps_connected()
            if not self._gps_connected or self.gpsd is None:
                return

            packet = self.gpsd.get_current()
            if not packet:
                return

            lat = getattr(packet, "lat", None)
            lon = getattr(packet, "lon", None)
            speed = getattr(packet, "speed", None)  # m/s if available

            # sanity: sometimes 0,0 if no fix
            if (
                lat is None
                or lon is None
                or not isinstance(lat, (float, int))
                or not isinstance(lon, (float, int))
            ):
                return

            # guard against bogus 0,0 positions
            if abs(lat) < 0.0001 and abs(lon) < 0.0001:
                return

            # mph from m/s
            mph = 0.0
            if isinstance(speed, (float, int)):
                mph = float(speed) * 2.23693629

            # send into JS
            js_loc = f"window.setCurrentLocation({lat:.7f}, {lon:.7f});"
            js_spd = f"window.setSpeedMph({mph:.2f});"

            self.page().runJavaScript(js_loc)
            self.page().runJavaScript(js_spd)

            self.last_lat, self.last_lon = lat, lon

        except Exception as e:
            # Don't crash the UI if gpsd is flaky
            print(f"[JeePi][GPS][WARN] {e}")


# ---------- Main entry ----------

def main():
    # Start static server and proxies
    static_server = start_static_server()

    geocode_proc = start_proxy("Geocode Proxy", "geocode_proxy.py", 5002)
    osrm_proc = start_proxy("OSRM Routing Proxy", "osrm_proxy.py", 5003)

    # Qt application
    app = QApplication(sys.argv)

    window = JeepPiWindow()
    window.resize(1280, 720)
    window.show()

    # Clean shutdown handler
    def shutdown():
        print("\n[JeePi] Shutting down...")

        for proc, label in [
            (geocode_proc, "Geocode Proxy"),
            (osrm_proc, "OSRM Proxy"),
        ]:
            if proc and proc.poll() is None:
                print(f"[JeePi] Terminating {label}...")
                try:
                    proc.terminate()
                except Exception:
                    pass

        # give them a moment
        time.sleep(0.5)
        for proc in [geocode_proc, osrm_proc]:
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass

    # Hook Ctrl+C in the terminal
    def sigint_handler(sig, frame):
        shutdown()
        app.quit()

    signal.signal(signal.SIGINT, sigint_handler)

    # Run the Qt event loop
    exit_code = app.exec()

    # Extra cleanup on normal exit
    shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
