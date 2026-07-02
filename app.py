"""
Presentatie-/API-laag (Flask).

Endpoints:
  GET  /                      – healthcheck
  GET  /api/health            – status van de configuratie
  GET/POST /api/voys-webhook  – ontvangt callid/callerid van Voys, antwoordt ACK
  POST /api/process-pending   – verwerkt openstaande gesprekken (Fase 1: handmatige trigger)
  GET  /api/report/onderwerpen – geaggregeerd rapport (onderwerp + sentiment)
  GET  /test                  – simpele testpagina met knoppen (TIJDELIJK, geen auth)

Belangrijk: deze laag bevat GEEN businesslogica. Hij valideert de request,
roept de servicelaag aan en formatteert het antwoord.
"""
from flask import Flask, request, jsonify, Response

import config
import store
import pipeline

app = Flask(__name__)
store.init_db()


def _urlencoded(status: str) -> Response:
    """Voys verwacht application/x-www-form-urlencoded met verplichte status."""
    return Response(f"status={status}", mimetype="application/x-www-form-urlencoded")


@app.route("/")
def index():
    return "Toteco backend actief", 200


@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "webhook_token_ingesteld": bool(config.WEBHOOK_TOKEN),
        "voys_token_ingesteld": bool(config.VOYS_BEARER_TOKEN),
        "sollit_key_ingesteld": bool(config.SOLLIT_API_KEY),
        "anthropic_key_ingesteld": bool(config.ANTHROPIC_API_KEY),
        "client_uuid": config.VOYS_CLIENT_UUID,
        "model": config.ANALYSIS_MODEL,
    })


@app.route("/api/voys-webhook", methods=["GET", "POST"])
def voys_webhook():
    """
    Door Voys aangeroepen bij een belplanstap. Variabelen komen binnen als
    query- of form-parameters: callid, callerid, did, token.
    We leggen het gesprek vast en antwoorden ACK. Bij een fout: ERR.
    """
    bron = request.values  # combineert args + form

    # 1. Geheim token valideren (bescherming tegen nep-events)
    if not config.WEBHOOK_TOKEN or bron.get("token") != config.WEBHOOK_TOKEN:
        return _urlencoded("NAK")

    callid = bron.get("callid")
    if not callid:
        return _urlencoded("ERR")

    try:
        store.registreer_call(
            callid=callid,
            callerid=bron.get("callerid", ""),
            did=bron.get("did", ""),
        )
    except Exception:  # noqa: BLE001
        return _urlencoded("ERR")

    return _urlencoded("ACK")


@app.route("/api/process-pending", methods=["POST"])
def process_pending():
    """Verwerkt openstaande gesprekken. Later te vervangen door een worker/cron."""
    limit = int(request.args.get("limit", 25))
    return jsonify(pipeline.verwerk_pending(limit))


@app.route("/api/report/onderwerpen")
def report_onderwerpen():
    return jsonify(store.aggregatie_onderwerpen())


@app.route("/api/report/bereikbaarheid")
def report_bereikbaarheid():
    return jsonify(store.aggregatie_bereikbaarheid())


# TIJDELIJKE testpagina — geen authenticatie. In de beveiligingsfase (Blok 4)
# achter login zetten of verwijderen. Handig om zonder tools te testen.
_TEST_HTML = """<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Toteco backend — test</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;color:#1a2b4a}
  h1{font-size:20px} p{color:#555}
  button{font-size:15px;padding:10px 16px;margin:6px 8px 6px 0;border:0;border-radius:8px;
         background:#1a2b4a;color:#fff;cursor:pointer}
  button.secondary{background:#e8edf5;color:#1a2b4a}
  pre{background:#f4f6fa;padding:16px;border-radius:8px;overflow:auto;white-space:pre-wrap;
      word-break:break-word;font-size:13px}
  .rij{margin:12px 0}
  .stat{display:inline-block;background:#f4f6fa;border-radius:8px;padding:8px 12px;margin:4px 6px 4px 0}
  .neg{color:#c0392b} .pos{color:#1e8449} .neu{color:#555}
</style></head>
<body>
<h1>Toteco backend — test</h1>
<p>Gebruik dit tijdelijke paginaatje om zonder extra tools te testen. Bel eerst binnen
(optie 2, gesprek opnemen), hang op, en klik dan hieronder.</p>

<div class="rij">
  <button onclick="verwerk()">1. Verwerk openstaande gesprekken</button>
  <button class="secondary" onclick="rapport()">2. Ververs rapport</button>
</div>

<div id="samenvatting"></div>
<h3>Details</h3>
<pre id="uit">Nog niets opgehaald.</pre>

<script>
var STATUS_LABEL = {
  "analyzed": "geanalyseerd (opgenomen gesprek)",
  "no_transcript": "binnengekomen, niet opgenomen",
  "pending": "wacht nog op verwerking / transcript",
  "failed": "technische fout"
};
async function verwerk(){
  toon("Bezig met verwerken...");
  try{
    const r = await fetch("/api/process-pending", {method:"POST"});
    const d = await r.json();
    toon(JSON.stringify(d, null, 2));
    rapport();
  }catch(e){ toon("Fout: " + e); }
}
async function rapport(){
  try{
    const [ro, rb] = await Promise.all([
      fetch("/api/report/onderwerpen").then(x=>x.json()),
      fetch("/api/report/bereikbaarheid").then(x=>x.json())
    ]);
    toonSamenvatting(ro, rb);
    toon(JSON.stringify({onderwerpen: ro, bereikbaarheid: rb}, null, 2));
  }catch(e){ toon("Fout: " + e); }
}
function toon(t){ document.getElementById("uit").textContent = t; }
function toonSamenvatting(o, b){
  var h = "<h3>Bereikbaarheid</h3>";
  h += "<p><strong>Totaal binnengekomen: " + (b.totaal_gesprekken||0) + "</strong></p><div class='rij'>";
  (b.per_status||[]).forEach(function(s){
    h += "<span class='stat'>" + (STATUS_LABEL[s.status]||s.status) + ": <strong>" + s.n + "</strong></span>";
  });
  h += "</div><h3>Inhoud (opgenomen gesprekken)</h3>";
  h += "<p><strong>Totaal geanalyseerd: " + (o.totaal_geanalyseerd||0) + "</strong></p><div class='rij'>";
  (o.per_onderwerp||[]).forEach(function(x){
    h += "<span class='stat'>" + x.onderwerp + ": <strong>" + x.n + "</strong></span>";
  });
  h += "</div><div class='rij'>";
  (o.per_sentiment||[]).forEach(function(s){
    var cls = s.sentiment==="negatief"?"neg":(s.sentiment==="positief"?"pos":"neu");
    h += "<span class='stat "+cls+"'>" + s.sentiment + ": <strong>" + s.n + "</strong></span>";
  });
  h += "</div>";
  document.getElementById("samenvatting").innerHTML = h;
}
rapport();
</script>
</body></html>"""


@app.route("/test")
def test_pagina():
    return Response(_TEST_HTML, mimetype="text/html")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
    try:
        store.registreer_call(
            callid=callid,
            callerid=bron.get("callerid", ""),
            did=bron.get("did", ""),
        )
    except Exception:  # noqa: BLE001
        return _urlencoded("ERR")

    return _urlencoded("ACK")


@app.route("/api/process-pending", methods=["POST"])
def process_pending():
    """Verwerkt openstaande gesprekken. Later te vervangen door een worker/cron."""
    limit = int(request.args.get("limit", 25))
    return jsonify(pipeline.verwerk_pending(limit))


@app.route("/api/report/onderwerpen")
def report_onderwerpen():
    return jsonify(store.aggregatie_onderwerpen())


# TIJDELIJKE testpagina — geen authenticatie. In de beveiligingsfase (Blok 4)
# achter login zetten of verwijderen. Handig om zonder tools te testen.
_TEST_HTML = """<!doctype html>
<html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Toteco backend — test</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;color:#1a2b4a}
  h1{font-size:20px} p{color:#555}
  button{font-size:15px;padding:10px 16px;margin:6px 8px 6px 0;border:0;border-radius:8px;
         background:#1a2b4a;color:#fff;cursor:pointer}
  button.secondary{background:#e8edf5;color:#1a2b4a}
  pre{background:#f4f6fa;padding:16px;border-radius:8px;overflow:auto;white-space:pre-wrap;
      word-break:break-word;font-size:13px}
  .rij{margin:12px 0}
  .stat{display:inline-block;background:#f4f6fa;border-radius:8px;padding:8px 12px;margin:4px 6px 4px 0}
  .neg{color:#c0392b} .pos{color:#1e8449} .neu{color:#555}
</style></head>
<body>
<h1>Toteco backend — test</h1>
<p>Gebruik dit tijdelijke paginaatje om zonder extra tools te testen. Bel eerst binnen
(optie 2, gesprek opnemen), hang op, en klik dan hieronder.</p>

<div class="rij">
  <button onclick="verwerk()">1. Verwerk openstaande gesprekken</button>
  <button class="secondary" onclick="rapport()">2. Ververs rapport</button>
</div>

<div id="samenvatting"></div>
<h3>Details</h3>
<pre id="uit">Nog niets opgehaald.</pre>

<script>
async function verwerk(){
  toon("Bezig met verwerken...");
  try{
    const r = await fetch("/api/process-pending", {method:"POST"});
    const d = await r.json();
    toon(JSON.stringify(d, null, 2));
    rapport();
  }catch(e){ toon("Fout: " + e); }
}
async function rapport(){
  try{
    const r = await fetch("/api/report/onderwerpen");
    const d = await r.json();
    toonSamenvatting(d);
    toon(JSON.stringify(d, null, 2));
  }catch(e){ toon("Fout: " + e); }
}
function toon(t){ document.getElementById("uit").textContent = t; }
function toonSamenvatting(d){
  let h = "<p><strong>Totaal geanalyseerd: " + (d.totaal_geanalyseerd||0) + "</strong></p>";
  h += "<div class='rij'>";
  (d.per_onderwerp||[]).forEach(function(o){
    h += "<span class='stat'>" + o.onderwerp + ": <strong>" + o.n + "</strong></span>";
  });
  h += "</div><div class='rij'>";
  (d.per_sentiment||[]).forEach(function(s){
    var cls = s.sentiment==="negatief"?"neg":(s.sentiment==="positief"?"pos":"neu");
    h += "<span class='stat "+cls+"'>" + s.sentiment + ": <strong>" + s.n + "</strong></span>";
  });
  h += "</div>";
  document.getElementById("samenvatting").innerHTML = h;
}
rapport();
</script>
</body></html>"""


@app.route("/test")
def test_pagina():
    return Response(_TEST_HTML, mimetype="text/html")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
