"""
Servicelaag: de verwerkingspijplijn.

Verbindt de lagen zonder dat de losse lagen elkaar kennen:
  transcript ophalen → klant opzoeken → analyseren → valideren → opslaan.

Wordt aangeroepen door een trigger (nu: /api/process-pending endpoint).
Later kan hier een echte queue/worker onder (Blok 3, schaal).
"""
import json

import voys
import sollit
import analyzer
import validation
import store


def verwerk_call(call: dict) -> dict:
    """Verwerkt één pending call-record. Geeft een resultstatus terug."""
    callid = call["callid"]
    pogingen = call.get("pogingen", 0) + 1

    # 1. Transcript ophalen (met retry/backoff bij 404 = nog niet klaar)
    transcript, tstatus = voys.haal_transcript(callid)
    if tstatus == "niet_klaar":
        # Blijft pending; volgende ronde opnieuw proberen.
        store.zet_call_status(callid, "pending", pogingen)
        return {"callid": callid, "resultaat": "transcript_nog_niet_klaar"}
    if tstatus == "fout" or not transcript:
        store.zet_call_status(callid, "no_transcript", pogingen)
        return {"callid": callid, "resultaat": "transcript_fout"}

    # 2. Klant opzoeken op bellernummer (Sollit)
    klant = sollit.zoek_klant(call.get("callerid", ""))
    context = sollit.klant_context(klant)

    # 3. Analyseren (Claude)
    try:
        ruw, prompt_versie, model = analyzer.analyseer_transcript(transcript, context)
    except Exception as e:  # noqa: BLE001 - we willen elke AI-fout netjes afvangen
        store.zet_call_status(callid, "failed", pogingen)
        return {"callid": callid, "resultaat": "ai_fout", "detail": str(e)}

    # 4. Valideren (ruwe output mag niet ongecontroleerd door)
    try:
        schoon = validation.valideer_analyse(ruw)
    except validation.ValidatieFout as e:
        store.zet_call_status(callid, "failed", pogingen)
        return {"callid": callid, "resultaat": "validatie_fout", "detail": str(e)}

    # 5. Opslaan + markeren
    store.bewaar_analyse(callid, schoon, klant_gevonden=bool(klant),
                         prompt_versie=prompt_versie, model=model)
    store.zet_call_status(callid, "analyzed", pogingen)
    return {"callid": callid, "resultaat": "analyzed", "onderwerp": schoon["onderwerp"],
            "sentiment": schoon["sentiment"]}


def verwerk_pending(limit=25):
    resultaten = [verwerk_call(c) for c in store.pending_calls(limit)]
    return {"verwerkt": len(resultaten), "details": resultaten}
