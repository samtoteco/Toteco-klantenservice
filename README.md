# Toteco Backend — Fase 1 (platte structuur)

Schone Flask-backend voor de klantenservice-rapportage (en later de realtime scherm-pop).
**Deze versie heeft alle bestanden op de hoofdmap** — geen submappen — zodat een gewone
upload naar GitHub/Railway direct werkt.

> Als je een eerdere versie met mappen (`integrations/`, `analysis/`, `services/`) hebt
> geüpload en de deploy faalde met `ModuleNotFoundError: No module named 'services'`,
> is dit de fix: vervang de repo-inhoud door de bestanden uit deze map.

## Uploaden — belangrijk

Upload **alle losse bestanden uit deze map** naar de hoofdmap van je repo:

```
app.py  config.py  store.py
voys.py  sollit.py  graph.py
taxonomy.py  prompt.py  analyzer.py  validation.py
pipeline.py
requirements.txt  Procfile  railway.toml  .env.example  README.md
```

Ze horen allemaal op hetzelfde niveau te staan (de "root"). Geen mappen nodig.

## Wat elk bestand doet (scheiding van verantwoordelijkheden blijft)

- `config.py` — env + constants (geheimen uit env)
- `store.py` — datalaag (SQLite); enige plek die de database kent
- `voys.py` / `sollit.py` / `graph.py` — externe koppelingen
- `taxonomy.py` — vaste onderwerpen + sentimentwaarden
- `prompt.py` — beheerde, geversioneerde prompt
- `analyzer.py` — Claude-aanroep (deterministisch)
- `validation.py` — controleert AI-output vóór opslag
- `pipeline.py` — verbindt de stappen
- `app.py` — Flask API-laag (routes, geen businesslogica)

## Endpoints

- `GET /` en `GET /api/health` — status
- `GET/POST /api/voys-webhook` — ontvangt callid/callerid, antwoordt `status=ACK`
- `POST /api/process-pending` — verwerkt openstaande gesprekken (Fase 1: handmatig)
- `GET /api/report/onderwerpen` — geaggregeerd rapport (onderwerp + sentiment)

## Environment variables (in Railway → Variables, nooit in code)

| Variabele | Nodig | Toelichting |
|---|---|---|
| `ANTHROPIC_API_KEY` | ja | Claude-analyse (Anthropic Console) |
| `SOLLIT_API_KEY` | ja | klant zoeken |
| `VOYS_BEARER_TOKEN` | ja | transcript ophalen (opnieuw genereren na lek) |
| `WEBHOOK_TOKEN` | ja | zelf verzonnen geheim; ook in de Voys-webhook-URL |
| `VOYS_CLIENT_UUID` | default gezet | Toteco's client_uuid |
| `MICROSOFT_*` | later | Outlook (fase e-mail) |

## Deploy op Railway

1. Vervang de inhoud van je repo door de bestanden hierboven (allemaal op de root).
2. Railway bouwt automatisch opnieuw (leest `railway.toml` / `Procfile`).
3. Zet de variabelen onder **Variables**.
4. **Settings → Networking → Generate Domain** voor een publiek adres.
5. Controleer op `https://<jouw-adres>/api/health` — alles `true` = klaar.

## Voys-webhook koppelen (ná deploy)

URL-template in het Voys-scherm:

```
https://<jouw-adres>/api/voys-webhook?callid={callid}&callerid={callerid}&did={did}&token=<WEBHOOK_TOKEN>
```

Plaats de webhook op een stap in het **inkomende belplan** van Toteco.

## Aannames & openstaande punten

- **AANNAME — transcript-timing:** geen bevestigd "transcript gereed"-event; we pollen met backoff (`404` = nog niet klaar). Bij een echt event wijzigt alleen `voys.py`.
- **Bevestigen bij eerste testcall** dat `{callid}` == het transcript-`call_id`-formaat.
- **Historie:** dit werkt vanaf-nu-vooruit; geen terugblik zonder een bron met oude `call_id`'s.

## Volgende fases

- **Fase 2 — security:** login/SSO, rollen, auditlog (transcripten = gevoelige PII).
- **Fase 3 — rapportage-UI / PWA** + realtime scherm-pop op hetzelfde webhook-fundament.
- **Later:** Sollit Quote/Products (omzet/marge/conversie), async worker, eventueel RAG.
