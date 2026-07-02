"""
Voys-koppeling (transcript_storage API).

Bron van waarheid voor telefonie. Wij lezen alleen.
Auth: Bearer-token (admin-rechten). Strikt server-side.

BELANGRIJK: deze functies doen één poging en wachten NIET binnen het verzoek.
Het "opnieuw proberen" (voor als een transcript nog niet klaar is) gebeurt
buiten het verzoek, doordat /api/process-pending later nogmaals draait.
Zo kan een webverzoek nooit blijven hangen op time.sleep.
"""
import requests

import config


def _headers():
    return {"Authorization": f"Bearer {config.VOYS_BEARER_TOKEN}"}


def _url(call_id, resource):
    return (f"{config.VOYS_BASE}/clients/{config.VOYS_CLIENT_UUID}"
            f"/calls/{call_id}/{resource}")


def haal_transcript(call_id):
    """
    Eén poging om het transcript op te halen. Geeft (tekst | None, status).
    status: 'ok' | 'niet_klaar' (404, mogelijk later wel) | 'fout' (401/403/500/netwerk)
    """
    try:
        r = requests.get(_url(call_id, "transcriptions"),
                         headers=_headers(), timeout=15)
    except requests.RequestException:
        return None, "fout"

    if r.status_code == 200:
        return r.text, "ok"
    if r.status_code == 404:
        return None, "niet_klaar"
    return None, "fout"


def haal_samenvatting(call_id):
    """Kant-en-klare Voys-samenvatting (alternatief; niet gebruikt in v1)."""
    try:
        r = requests.get(_url(call_id, "summaries"), headers=_headers(), timeout=15)
        if r.status_code == 200:
            return r.json().get("summary", ""), "ok"
        if r.status_code == 404:
            return None, "niet_klaar"
        return None, "fout"
    except requests.RequestException:
        return None, "fout"
