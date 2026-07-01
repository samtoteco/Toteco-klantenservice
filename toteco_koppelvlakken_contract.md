# Toteco Klantenservice & Rapportage — Koppelvlakkencontract

**Versie:** 0.1 (werkdocument) · **Datum:** 1 juli 2026
**Doel:** één referentie voor alle externe koppelingen, om tegen te bouwen.

> Legenda status: ✅ bevestigd · ⚠️ open / te bevestigen door Toteco · 🔒 beveiligingspunt

---

## Overzicht: bron van waarheid (SSOT)

| Data | Eigenaar (bron van waarheid) | Rol van onze store |
|---|---|---|
| E-mail | Microsoft Graph (Outlook) | leest, later verstuurt |
| Klantgegevens | Sollit | leest |
| Telefonie: gesprekken, transcript, opname | Voys | leest |
| Onderwerp + sentiment (afgeleid) | — (door onze AI-laag geproduceerd) | eigenaar van de afgeleide analyse |
| Afhandelstatus + auditspoor | onze database | eigenaar |

De eigen database bevat **alleen afgeleide en operationele data** (analyse, status, audit) — nooit een kopie die als waarheid voor e-mail, klant of telefonie geldt.

---

## 1. Microsoft Graph (Outlook) — ✅ in gebruik

- **Auth:** OAuth2 client-credentials (app-only). Token via
  `POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`, scope `https://graph.microsoft.com/.default`.
- **In gebruik:**
  - `GET /users/{mailbox}/mailFolders/inbox/messages` — inbox lezen
  - `PATCH /users/{mailbox}/messages/{id}` — markeren als gelezen
- **Later (realtime-tool):** `POST /users/{mailbox}/sendMail` — vereist app-permissie **Mail.Send** met admin-consent. ⚠️ Toteco-beheerder moet dit verlenen.
- 🔒 Token per request opnieuw ophalen is nu de praktijk → in Fase 1 cachen + retry/backoff.

---

## 2. Sollit (CRM) — deels ✅ / deels ⚠️

- **Klant zoeken:** `GET {SOLLIT_BASE}/person/search/`, header `API-KEY`, param `search`.
  - ✅ Zoeken op naam/e-mail werkt (huidige app).
  - ⚠️ **Zoeken op telefoonnummer** — nog te bevestigen. Dit is nodig omdat bij een gesprek het bellernummer (`{callerid}`) de enige sleutel naar de klant is.
- **Sales-data (v2):** Quote-API `GET /quote/` en Products-API (`x-api-key`).
  - ✅ Scope verleend door Sollit (401 opgelost).
  - Velden voor rapportage: `actualCostNoVat`, `totalPurchasePrice`, `quote_signed_at`, `request_client_status_id`, `account_manager`.
  - ⚠️ **Marge-berekening:** `actualCostNoVat` is expliciet excl. btw; de btw-basis van `totalPurchasePrice` staat niet vast. Vóór margeberekening eerst afstemmen (voorkomt fout cijfer).
- **Let op:** twee verschillende auth-mechanismen — `API-KEY` (person) vs. `x-api-key` (products). Dat zijn twee koppelvlakken.

---

## 3. Voys (telefonie) — grotendeels ✅

Basis: `https://api.eu-production.holodeck.voys.nl/transcription-storage`
Client: `clients/{client_uuid}/...` — ⚠️ **`client_uuid` van Toteco** invullen (vaste waarde uit Voys-account).
Auth: **Bearer-token** (Authorization-header). 🔒 Vereist **admin**-rechten + toegang tot callrecordings → strikt server-side, nooit in frontend.

### 3a. Belplan-webhook (inkomend event) — ✅
- Ingesteld in Voys onder *Beheer → Belplannen → belplanstap → webhook*.
- Voys roept jouw **URL-template** aan met variabelen:
  - `{callid}` — ID van de inkomende oproep (**= sleutel voor transcript/samenvatting**)
  - `{callerid}` — nummer van de beller (**= sleutel voor Sollit-lookup**)
  - `{did}` — gebeld Toteco-nummer
  - `{callername}` — naam beller (indien beschikbaar)
- **Voys verwacht een respons** in `application/x-www-form-urlencoded` met verplichte `status` = `ACK` | `NAK` | `ERR`. Backend antwoordt `status=ACK`.
- ⏱️ **Timing:** dit event vuurt bij gespreksstart/routering — het **transcript bestaat op dat moment nog niet**. Gebruik het event om `callid` vast te leggen; transcript later ophalen.
- ⚠️ Bevestigen bij eerste testcall: `{callid}` == het `call_id`-formaat van de transcript-API (`ua0-grq-…`).
- 🔒 URL is publiek bereikbaar → geheim `token` in de URL, server-side valideren. Alleen HTTPS.

### 3b. Transcript ophalen — ✅
- `GET .../clients/{client_uuid}/calls/{call_id}/transcriptions`
- Respons 200: transcripttekst met sprekerlabels (`Participant 1: …`).
- Fouten: 401 / 403 / 404 / 500. **404 = (waarschijnlijk) nog niet klaar** → retry met backoff.

### 3c. Samenvatting ophalen — ✅ (alternatief voor 3b)
- `GET .../clients/{client_uuid}/calls/{call_id}/summaries`
- Respons 200: `{ "summary": "…" }` (alleen tekst; geen categorie/sentiment).
- **Keuze gemaakt:** we gebruiken **3b (transcript) door eigen AI-laag**, niet de kant-en-klare samenvatting — nodig voor consistente onderwerp-indeling + sentiment.

### 3d. Samenvatting bijwerken — bestaat, niet gebruikt
- `PUT .../calls/{call_id}/summaries`

### ⚠️ Openstaand voor Voys
- Bestaat een apart event/webhook voor **"transcript gereed"**? Zo niet → pollen met backoff na gespreksstart (aanname, gelabeld).
- Historie: er is (nog) **geen endpoint dat gesprekken over een periode lijst met `call_id`**. De CSV-export bevat wél metadata maar **geen `call_id`**. Gevolg: inhoudelijke analyse (onderwerp/sentiment) is **vanaf-nu-vooruit** via de webhook; geen terugblik over oude gesprekken tenzij een export mét `call_id` beschikbaar komt.

---

## 4. Anthropic Claude (AI-analyselaag) — ontwerp

- **Rol:** transcript (+ klantcontext) → onderwerp + sentiment. Bezit geen bron van waarheid.
- **Determinisme (C2):** vaste, vooraf vastgelegde **onderwerpen-taxonomie** (geen vrije labels), lage temperatuur voor reproduceerbare classificatie.
- **Validatielaag (C5):** elke output gecontroleerd op geldige categorie + geldige sentimentwaarde vóór opslag. Ruwe LLM-output gaat nooit ongevalideerd het rapport in.
- **Schaal (A5/B5):** ~140 inkomende gesprekken/dag (steekproef 1 juli). Over maanden = duizenden transcripten → batchverwerking + kosteninschatting nodig.

---

## Datastroom (vanaf-nu-model)

1. Gesprek start → **belplan-webhook** → backend legt `callid`, `callerid`, tijdstip vast (`status=ACK` terug).
2. Na gesprekseinde (retry/backoff) → **transcript** ophalen via `callid`.
3. **Sollit-lookup** op `callerid` → klantcontext.
4. **Claude** → onderwerp + sentiment → **validatielaag**.
5. Opslag in **analytische store** → voedt rapportage (aggregatie) én later de realtime scherm-pop.

De belplan-webhook lost hiermee twee problemen tegelijk op: de call_id-voorraad voor rapportage én de realtime-trigger voor de scherm-pop. Eén fundament, twee sporen.

---

## Openstaande punten (eigenaar: Toteco)

1. ⚠️ Sollit: kan `/person/search/` op **telefoonnummer** matchen?
2. ⚠️ Voys: **`client_uuid`** van Toteco.
3. ⚠️ Voys: bestaat een **"transcript gereed"-event**, of pollen we?
4. ⚠️ Voys: bij eerste testcall bevestigen dat `{callid}` == transcript-`call_id`.
5. ⚠️ Backend-URL + geheim `token` invullen in de webhook-URL-template zodra Fase 1 live staat.
6. ⚠️ (v2) Graph **Mail.Send** admin-consent voor versturen.

---

## Beveiliging & compliance (samengevat)

- 🔒 Alle tokens/keys server-side (Flask). Nooit in frontend/PWA.
- 🔒 Webhook-URL: HTTPS + geheim token, server-side gevalideerd.
- 🔒 Transcripten + gekoppelde klantdata = gevoelige PII → bewaartermijn vastleggen, rolgebaseerde toegang (Blok 4).
- 🔒 De `cors-proxy` uit de Voys cURL-voorbeelden is voor browser-testen, **niet** voor productie.
