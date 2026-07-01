"""
Voys-koppeling (transcript_storage API).

Bron van waarheid voor telefonie. Wij lezen alleen.
Auth: Bearer-token (admin-rechten). Strikt server-side.
"""
import time

import requests

import config


def _headers():
    return {"Authorization": f"Bearer {config.VOYS_BEARER_TOKEN}"}


def _url(call_id, resource):
    return (f"{config.VOYS_BASE}/clients/{config.VOYS_CLIENT_UUID}"
            f"/calls/{call_id}/{resource}")


def haal_transcript(call_id, met_retry=True):
    """
    Haalt het transcript op. Geeft (transcript_tekst | None, status).
    status: 'ok' | 'niet_klaar' | 'fout'

    AANNAME: 404 == transcript nog niet gereed. Zolang er geen
    'transcript gereed'-event bevestigd is, pollen we met backoff.
    """
    pogingen = config.TRANSCRIPT_MAX_POGINGEN if met_retry else 1
    wacht = config.TRANSCRIPT_BACKOFF_START_S

    for poging in range(pogingen):
        try:
            r = requests.get(_url(call_id, "transcriptions"),
                             headers=_headers(), timeout=15)
        except requests.RequestException:
            return None, "fout"

        if r.status_code == 200:
            return r.text, "ok"
        if r.status_code == 404:
            # nog niet klaar → wachten en opnieuw (behalve laatste poging)
            if met_retry and poging < pogingen - 1:
                time.sleep(wacht)
                wacht *= 2
                continue
            return None, "niet_klaar"
        # 401/403/500 → geen zin om te blijven proberen
        return None, "fout"

    return None, "niet_klaar"


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
