JeePi v3 – Raspberry Pi In-Vehicle Navigation System

JeePi v3 is a fully local, Raspberry-Pi-based navigation system designed for off-road and on-road use.
It provides:

Live GPS tracking (via gpsd)

MapTiler tiles (local or online)

Local OSRM routing (proxy wrapper)

Local geocoding proxy (MapTiler Geocoding API)

Turn-by-turn navigation

Follow-vehicle mode

On-screen keyboard toggle (Matchbox Keyboard)

Clean touchscreen UI optimized for Jeep dashboards

The entire system runs locally on the Pi using a Qt WebEngine wrapper around a high-performance HTML/JS Leaflet interface.

🚙 Features
Navigation UI

High-contrast, Jeep-style touchscreen interface

Smooth panning and zooming

Dynamic turn-by-turn panel

Compact “Next Turn” banner

Tap map to dismiss search results

Large FAB buttons for use while driving

GPS Integration

Auto-connects to gpsd

Injects GPS position + speed into the UI every second

“Follow vehicle” mode snaps map to your position

Search / Geocoding

Local proxy for MapTiler Geocoding API

Automatically sorts search results by distance

Works offline with cached tiles

POI fallback (via Overpass API – optional)

Routing

Local OSRM proxy wrapper

Polyline route display

Full step list with icons + ETA

Tappable "New Route" button to clear

Keyboard Toggle

One-touch on-screen keyboard (using matchbox-keyboard)

Easy text entry on touchscreens

Toggle integrated via Qt WebChannel
