"""
Sollit-koppeling (CRM).

Bron van waarheid voor klantdata. Wij lezen alleen.
Zoeken op telefoonnummer is bevestigd mogelijk (person/search).
"""
import requests

import config


def zoek_klant(zoekterm: str):
    """
    Zoekt een klant op (telefoonnummer, e-mail of naam).
    Geeft de eerste treffer als dict, of None.
    """
    if not zoekterm:
        return None
    try:
        r = requests.get(
            f"{config.SOLLIT_BASE}/person/search/",
            headers={"API-KEY": config.SOLLIT_API_KEY},
            params={"search": zoekterm},
            timeout=8,
        )
        data = r.json()
    except (requests.RequestException, ValueError):
        return None

    # Sollit kan een lijst of een dict-wrapper teruggeven
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("data", data.get("results", data.get("persons", [])))
    else:
        items = []

    return items[0] if items else None


def klant_context(klant) -> str:
    """Maakt een korte contextregel voor de prompt. Leeg als geen klant."""
    if not klant:
        return ""
    naam = f"{klant.get('first_name','')} {klant.get('last_name','')}".strip()
    return (
        "Klantinfo uit Sollit:\n"
        f"- Naam: {naam}\n"
        f"- Status: {klant.get('request_status','')}\n"
        f"- Type: {klant.get('request_type_name','')}\n"
        f"- Accountmanager: {klant.get('current_user_name','')}\n"
    )
