"""
Presentatie-/API-laag (Flask).

Endpoints:
  GET  /                      – healthcheck
  GET  /api/health            – status van de configuratie
  GET/POST /api/voys-webhook  – ontvangt callid/callerid van Voys, antwoordt ACK
  POST /api/process-pending   – verwerkt openstaande gesprekken (Fase 1: handmatige trigger)
  GET  /api/report/onderwerpen – geaggregeerd rapport (onderwerp + sentiment)

Belangrijk: deze laag bevat GEEN businesslogica. Hij valideert de request,
roept de servicelaag aan en formatteert het antwoord.
"""
from flask import Flask, request, jsonify, Response

import config
import store
from services import pipeline

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


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
