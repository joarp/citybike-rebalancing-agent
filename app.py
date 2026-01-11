import json
from pathlib import Path
import gradio as gr
from bike_agent.agent.orchestrator import orchestrator

PALMA_CENTER = {"lat": 39.5696, "lon": 2.6502}
STATIC_DIR = Path(__file__).resolve().parent / "static"


def make_iframe_leaflet_html(center: dict) -> str:
    leaflet_css_url = f"/gradio_api/file={STATIC_DIR / 'leaflet.css'}"
    leaflet_js_url = f"/gradio_api/file={STATIC_DIR / 'leaflet.js'}"

    iframe_doc = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="{leaflet_css_url}">
  <style>
    html, body, #map {{
      width: 100%;
      height: 100%;
      margin: 0;
      padding: 0;
    }}
  </style>
</head>
<body>
  <div id="map"></div>

  <script src="{leaflet_js_url}"></script>
  <script>
    (function() {{
      const center = [{center["lat"]}, {center["lon"]}];

      if (!window.L) {{
        document.body.innerHTML = "<div style=\\"padding:12px;font-family:sans-serif;\\">Leaflet failed to load.</div>";
        return;
      }}

      const map = L.map("map").setView(center, 13);

      L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
      }}).addTo(map);

      let marker = L.circleMarker(center, {{ radius: 8 }}).addTo(map);

      map.on("click", function(e) {{
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;
        marker.setLatLng([lat, lon]);
        
        // Store in parent window
        window.parent.latestMapCoords = JSON.stringify({{ lat: lat, lon: lon }});
        console.log("Stored coords in parent:", lat, lon);
      }});
    }})();
  </script>
</body>
</html>
"""

    import html
    escaped_doc = html.escape(iframe_doc, quote=False)
    
    return f"""
<div style="width: 100%; height: 520px; border-radius: 12px; overflow: hidden;">
  <iframe id="map-iframe"
    style="width: 100%; height: 100%; border: 0;"
    srcdoc='{escaped_doc}'
  ></iframe>
</div>
"""


def poll_for_coords(current_coords):
    """This function is called by timer, but JS does the real work"""
    # The JS will return the new coords, this just passes them through
    return current_coords


def run_agent(user_request: str, coords_json: str):
    try:
        coords = json.loads(coords_json) if coords_json else None
        if not coords or "lat" not in coords or "lon" not in coords:
            return "Please click on the map to set coordinates."
    except json.JSONDecodeError:
        return "Invalid coordinates JSON. Please click on the map again."

    task_payload = {
        "user_request": user_request,
        "start_coordinates": coords,
    }
    result = orchestrator(task_payload)
  
    return result


# JavaScript that polls for coordinate updates
# It takes the current coords as input and returns updated coords if available
poll_js = """
(current_coords) => {
    if (window.latestMapCoords) {
        const coords = window.latestMapCoords;
        window.latestMapCoords = null;
        console.log("Polling found coords:", coords);
        return coords;
    }
    return current_coords;
}
"""


with gr.Blocks(title="Citybike Rebalancing Agent") as app:
    gr.Markdown("## Citybike Rebalancing Agent — Palma\nClick on the map to set your start coordinates.")

    with gr.Row():
        with gr.Column(scale=2):
            map_html = gr.HTML(make_iframe_leaflet_html(PALMA_CENTER))

            coords_box = gr.Textbox(
                label="Clicked Coordinates (JSON)",
                value=json.dumps(PALMA_CENTER),
                lines=2,
                elem_id="coords",
            )
            
            # Timer to poll for coordinate updates every 500ms
            timer = gr.Timer(0.5)
            timer.tick(
                fn=poll_for_coords, 
                inputs=coords_box,  # Pass current coords as input
                outputs=coords_box,  # Update with new coords
                js=poll_js
            )

        with gr.Column(scale=1):
            user_request = gr.Textbox(
                label="Task request",
                value="Give me my route for the coming hour.",
                lines=4,
            )
            run_btn = gr.Button("Generate route")
            output = gr.Textbox(label="Output", lines=22)

    run_btn.click(run_agent, inputs=[user_request, coords_box], outputs=[output])

if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0", 
        server_port=7860, 
        allowed_paths=[str(STATIC_DIR)]
    )