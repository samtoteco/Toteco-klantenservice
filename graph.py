"""
Microsoft Graph (Outlook) koppeling.

Bron van waarheid voor e-mail. In Fase 1 alleen token-caching als fundament
(de bestaande app haalde het token bij ELK request opnieuw op — dat schaalt niet).
E-mailcontext en verzenden komen in latere fases.
"""
import time

import requests

import config

_token_cache = {"token": None, "verloopt_op": 0}


def get_token():
    """Cachet het app-only token tot kort voor verloop."""
    if _token_cache["token"] and time.time() < _token_cache["verloopt_op"] - 60:
        return _token_cache["token"]

    url = f"https://login.microsoftonline.com/{config.MICROSOFT_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": config.MICROSOFT_CLIENT_ID,
        "client_secret": config.MICROSOFT_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    }
    r = requests.post(url, data=data, timeout=10)
    r.raise_for_status()
    body = r.json()
    _token_cache["token"] = body["access_token"]
    _token_cache["verloopt_op"] = time.time() + int(body.get("expires_in", 3600))
    return _token_cache["token"]
