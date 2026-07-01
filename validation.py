"""
Validatielaag (C5).

Ruwe LLM-output gaat NOOIT ongecontroleerd de rapportage in. Deze laag
controleert structuur én toegestane waarden. Faalt de check, dan wordt het
gesprek als 'failed' gemarkeerd i.p.v. met rommel in de cijfers te belanden.
"""
from taxonomy import ONDERWERPEN, SENTIMENTEN


class ValidatieFout(Exception):
    pass


def valideer_analyse(data) -> dict:
    """Geeft een schone dict terug, of gooit ValidatieFout."""
    if not isinstance(data, dict):
        raise ValidatieFout("output is geen JSON-object")

    # Verplichte velden aanwezig?
    for veld in ("onderwerp", "sentiment"):
        if veld not in data or not isinstance(data[veld], str):
            raise ValidatieFout(f"veld '{veld}' ontbreekt of is geen tekst")

    # Waarden binnen de vaste taxonomie?
    if data["onderwerp"] not in ONDERWERPEN:
        raise ValidatieFout(f"onderwerp '{data['onderwerp']}' niet in taxonomie")
    if data["sentiment"] not in SENTIMENTEN:
        raise ValidatieFout(f"sentiment '{data['sentiment']}' niet toegestaan")

    # Optionele velden normaliseren
    samenvatting = data.get("samenvatting", "")
    if not isinstance(samenvatting, str):
        samenvatting = str(samenvatting)

    actiepunten = data.get("actiepunten", [])
    if not isinstance(actiepunten, list):
        actiepunten = [str(actiepunten)]
    actiepunten = [str(a) for a in actiepunten if str(a).strip()]

    return {
        "onderwerp": data["onderwerp"],
        "sentiment": data["sentiment"],
        "samenvatting": samenvatting.strip(),
        "actiepunten": actiepunten,
    }
