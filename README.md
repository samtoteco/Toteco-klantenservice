# Toteco Backend — Fase 1 (fundament)

Schone, gelaagde Flask-backend voor de klantenservice-rapportage (en later de realtime scherm-pop).
Dit is **Fase 1: het fundament** — het deel dat niet op openstaande antwoorden hoeft te wachten.

## Wat er nu in zit

- **Voys-webhookontvanger** (`/api/voys-webhook`): vangt `callid` + `callerid` op bij elk gesprek en antwoordt Voys met `status=ACK`. Dit lost meteen de call_id-voorraad op (vanaf nu).
- **Verwerkingspijplijn**: transcript ophalen → klant opzoeken in Sollit (op bellernummer) → Claude classificeert onderwerp + sentiment → validatie → opslag.
- **Vaste onderwerpen-taxonomie** + **validatielaag**: ruwe AI-output gaat nooit ongecontroleerd het rapport in.
- **Beheerde, geversioneerde prompt** (prompt = code).
- **Graph token-caching** (fundament voor e-mail later).
- **Rapportage-aggregatie** (`/api/report/onderwerpen`): telt per onderwerp en sentiment.

## Gelaagde structuur

```
config.py              # env + constants (geheimen uit env)
store.py               # datalaag (SQLite) — enige plek die de DB kent
integrations/
  voys.py              # transcript/samenvatting ophalen (+ retry/backoff)
  sollit.py            # klant zoeken (telefoon/e-mail/naam)
  graph.py             # Outlook-token met caching
analysis/
  taxonomy.py          # vaste onderwerpen + sentimentwaarden
  prompt.py            # beheerde, geversioneerde prompt
  analyzer.py          # Claude-aanroep (deterministisch)
  validation.py        # controleert output vóór opslag
services/
  pipeline.py          # verbindt de lagen
app.py                 # Flask API-laag (routes, geen businesslogica)
```

## Lokaal draaien

```bash
pip install -r requirements.txt
cp .env.example .env        # en vul de waarden in
export $(grep -v '^#' .env | xargs)   # of gebruik een .env-loader
python app.py               # draait op http://localhost:8080
```

Check de configuratie: `GET /api/health`.

## Environment variables

| Variabele | Nodig | Toelichting |
|---|---|---|
| `ANTHROPIC_API_KEY` | ja | Claude-analyse |
| `SOLLIT_API_KEY` | ja | klant zoeken |
| `VOYS_BEARER_TOKEN` | ja | transcript ophalen (admin-token) |
| `WEBHOOK_TOKEN` | ja | zelf verzonnen geheim; ook in de Voys-webhook-URL |
| `VOYS_CLIENT_UUID` | default gezet | Toteco's client_uuid |
| `MICROSOFT_*` | later | Outlook (fase e-mail) |

## Deploy op Railway

1. Push deze map naar een Git-repo en koppel die aan een Railway-project.
2. Zet de env-variabelen onder **Variables** (nooit in de code).
3. Railway start met `gunicorn app:app` (zie `railway.toml` / `Procfile`).
4. Na deploy krijg je een publiek adres, bijv. `https://<project>.up.railway.app`.

## Voys-webhook koppelen (na deploy)

Vul in het Voys-scherm "Voeg webhook toe" de URL-template in:

```
https://<project>.up.railway.app/api/voys-webhook?callid={callid}&callerid={callerid}&did={did}&token=<WEBHOOK_TOKEN>
```

Plaats de webhook daarna op een stap in het **inkomende belplan** van Toteco, zodat hij bij elk klantenservicegesprek vuurt.

## Verwerking draaien (Fase 1: handmatig)

De webhook slaat gesprekken op als `pending`. Verwerk ze met:

```bash
curl -X POST https://<project>.up.railway.app/api/process-pending
```

In een latere fase komt hier een cron/worker onder (Blok 3, schaal). Voor nu is dit een bewuste handmatige/geplande trigger.

## Aannames & openstaande punten

- **AANNAME — transcript-timing:** er is nog niet bevestigd of Voys een "transcript gereed"-event stuurt. Tot die tijd pollen we het transcript-endpoint met backoff; een `404` = nog niet klaar. Zodra er een event blijkt, is `voys.py` het enige bestand dat wijzigt.
- **Bevestigen bij eerste testcall:** dat `{callid}` uit de webhook exact het `call_id`-formaat is dat de transcript-API verwacht.
- **Historie:** dit model werkt vanaf-nu-vooruit. Terugkijken over oude gesprekken kan alleen met een export/endpoint dat `call_id`'s bevat (nog niet beschikbaar).

## Volgende fases

- **Fase 2 — security:** login/SSO (Entra ID), rollen, auditlog. Transcripten zijn gevoelige PII.
- **Fase 3 — rapportage-UI / PWA:** het rapport zelf (grafieken, periode-selectie), plus de realtime scherm-pop op hetzelfde webhook-fundament.
- **Later:** Sollit Quote/Products (omzet/marge/conversie), async worker, eventueel RAG.
