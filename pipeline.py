"""
Servicelaag: de verwerkingspijplijn.

Verbindt de lagen zonder dat de losse lagen elkaar kennen:
  transcript ophalen -> klant opzoeken -> analyseren -> valideren -> opslaan.

Non-blocking: er wordt NIET binnen het verzoek gewacht. Is een transcript nog
niet klaar (404), dan blijft het gesprek 'pending' en probeert een volgende
run het opnieuw. Na een maximum aantal pogingen concluderen we 'geen opname'
(binnengekomen, niet opgenomen) -- dat is een geldige, meetbare uitkomst.
"""
import config
import voys
import sollit
import analyzer
import validation
import store


def verwerk_call(call: dict) -> dict:
    callid = call["callid"]
    pogingen = call.get("pogingen", 0) + 1

    # 1. Eén poging: transcript ophalen
    transcript, tstatus = voys.haal_transcript(callid)

    if tstatus == "niet_klaar":
        if pogingen >= config.TRANSCRIPT_MAX_POGINGEN:
            # Definitief geen transcript: binnengekomen, niet opgenomen.
            store.zet_call_status(callid, "no_transcript", pogingen)
            return {"callid": callid, "resultaat": "geen_opname"}
        # Nog kans op een transcript: pending laten, later opnieuw.
        store.zet_call_status(callid, "pending", pogingen)
        return {"callid": callid, "resultaat": "transcript_nog_niet_klaar",
                "poging": pogingen}

    if tstatus == "fout" or not transcript:
        store.zet_call_status(callid, "failed", pogingen)
        return {"callid": callid, "resultaat": "transcript_fout"}

    # 2. Klant opzoeken op bellernummer (Sollit)
    klant = sollit.zoek_klant(call.get("callerid", ""))
    context = sollit.klant_context(klant)

    # 3. Analyseren (Claude)
    try:
        ruw, prompt_versie, model = analyzer.analyseer_transcript(transcript, context)
    except Exception as e:  # noqa: BLE001
        store.zet_call_status(callid, "failed", pogingen)
        return {"callid": callid, "resultaat": "ai_fout", "detail": str(e)}

    # 4. Valideren
    try:
        schoon = validation.valideer_analyse(ruw)
    except validation.ValidatieFout as e:
        store.zet_call_status(callid, "failed", pogingen)
        return {"callid": callid, "resultaat": "validatie_fout", "detail": str(e)}

    # 5. Opslaan + markeren
    store.bewaar_analyse(callid, schoon, klant_gevonden=bool(klant),
                         prompt_versie=prompt_versie, model=model)
    store.zet_call_status(callid, "analyzed", pogingen)
    return {"callid": callid, "resultaat": "analyzed",
            "onderwerp": schoon["onderwerp"], "sentiment": schoon["sentiment"]}


def verwerk_pending(limit=25):
    resultaten = [verwerk_call(c) for c in store.pending_calls(limit)]
    return {"verwerkt": len(resultaten), "details": resultaten}
