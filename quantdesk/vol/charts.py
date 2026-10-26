"""Local HTML charts for SP5 (no Python plotting dependency): plotly.js from a pinned CDN build, data inlined."""

import json

PLOTLY = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"


def _page(title: str, body: str) -> str:
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
            f"<script src='{PLOTLY}'></script><style>body{{font-family:Arial,sans-serif;margin:16px}}"
            f".chart{{width:100%;height:560px}}</style></head><body><h2>{title}</h2>{body}</body></html>")


def surface_page(title: str, points: list[dict], note: str) -> str:
    """`points`: log_moneyness, dte (sessions to expiry), iv_pct, expiry, strike."""
    by_expiry: dict = {}
    for p in points:
        by_expiry.setdefault(p["expiry"], []).append(p)
    smiles = [{"x": [q["strike"] for q in sorted(v, key=lambda q: q["strike"])],
               "y": [q["iv_pct"] for q in sorted(v, key=lambda q: q["strike"])],
               "mode": "lines+markers", "name": f"expiry {e}"} for e, v in sorted(by_expiry.items())[:4]]
    scatter = [{"type": "scatter3d", "mode": "markers",
                "x": [p["log_moneyness"] for p in points], "y": [p["dte"] for p in points],
                "z": [p["iv_pct"] for p in points],
                "text": [f"{p['expiry']} {p['strike']:.0f}" for p in points],
                "marker": {"size": 3, "color": [p["iv_pct"] for p in points], "colorscale": "Viridis"}}]
    layout3d = {"scene": {"xaxis": {"title": "ln(strike / forward)"}, "yaxis": {"title": "sessions to expiry"},
                          "zaxis": {"title": "implied vol % (annualised)"}}, "margin": {"l": 0, "r": 0, "t": 0, "b": 0}}
    layout2d = {"xaxis": {"title": "strike"}, "yaxis": {"title": "implied vol %"},
                "legend": {"orientation": "h", "y": 1.12}, "margin": {"l": 50, "r": 10, "t": 40, "b": 40}}
    body = (f"<p>{note}</p><div id='s3' class='chart'></div><h3>Smile by expiry (IV against strike)</h3>"
            "<div id='sm' class='chart'></div><script>"
            f"Plotly.newPlot('s3', {json.dumps(scatter)}, {json.dumps(layout3d)});"
            f"Plotly.newPlot('sm', {json.dumps(smiles)}, {json.dumps(layout2d)});"
            "</script>")
    return _page(title, body)


def vrp_page(title: str, days: list[str], implied: list[float], realised: list[float], note: str) -> str:
    traces = [{"x": days, "y": implied, "name": "priced by the market (implied, 20-day avg)", "mode": "lines"},
              {"x": days, "y": realised, "name": "what happened (realised, 20-day avg)", "mode": "lines"}]
    layout = {"yaxis": {"title": "daily move, % of the index"}, "xaxis": {"title": "date", "type": "date"},
              "legend": {"orientation": "h", "y": 1.12}, "margin": {"l": 50, "r": 10, "t": 40, "b": 40}}
    body = (f"<p>{note}</p><div id='v' class='chart'></div><script>"
            f"Plotly.newPlot('v', {json.dumps(traces)}, {json.dumps(layout)});</script>")
    return _page(title, body)
