"""
Configuratielaag.

Alle geheimen komen uit environment variables (Railway → Variables).
Niet-geheime identifiers (zoals client_uuid) hebben een default maar zijn
overschrijfbaar via env.
"""
import os


# ── Geheimen (verplicht in productie, uit env) ─────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SOLLIT_API_KEY    = os.environ.get("SOLLIT_API_KEY", "")
VOYS_BEARER_TOKEN = os.environ.get("VOYS_BEARER_TOKEN", "")

# Geheim token dat wij zelf verzinnen en in de Voys-webhook-URL zetten.
# Alleen requests met dit token worden geaccepteerd.
WEBHOOK_TOKEN = os.environ.get("WEBHOOK_TOKEN", "")

# Microsoft Graph (Outlook) – voor e-mailcontext / latere verzendfunctie
MICROSOFT_CLIENT_ID     = os.environ.get("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET", "")
MICROSOFT_TENANT_ID     = os.environ.get("MICROSOFT_TENANT_ID", "")

# ── Identifiers / endpoints ────────────────────────────────────
# client_uuid van Toteco (Voys). Geen geheim, wel overschrijfbaar.
VOYS_CLIENT_UUID = os.environ.get(
    "VOYS_CLIENT_UUID", "92740e29-dc8b-4bd4-ab78-0b8b231d7527"
)
VOYS_BASE  = os.environ.get(
    "VOYS_BASE", "https://api.eu-production.holodeck.voys.nl/transcription-storage"
)
SOLLIT_BASE = os.environ.get("SOLLIT_BASE", "https://app.sollit.nl/api")
GRAPH_BASE  = "https://graph.microsoft.com/v1.0"

# ── AI-laag ────────────────────────────────────────────────────
# Model configureerbaar. Haiku is kostenefficiënt voor classificatie op schaal.
ANALYSIS_MODEL = os.environ.get("ANALYSIS_MODEL", "claude-haiku-4-5-20251001")
# Lage temperatuur = zo deterministisch mogelijke classificatie.
ANALYSIS_TEMPERATURE = float(os.environ.get("ANALYSIS_TEMPERATURE", "0"))

# ── Transcript-ophaal (AANNAME: pollen met backoff) ────────────
# Er is nog niet bevestigd of Voys een "transcript gereed"-event stuurt.
# Tot die tijd pollen we het transcript-endpoint met oplopende wachttijd.
TRANSCRIPT_MAX_POGINGEN = int(os.environ.get("TRANSCRIPT_MAX_POGINGEN", "5"))
TRANSCRIPT_BACKOFF_START_S = int(os.environ.get("TRANSCRIPT_BACKOFF_START_S", "30"))

# ── Opslag ─────────────────────────────────────────────────────
# SQLite voor Fase 1 (geen infra nodig, direct testbaar).
# Productie/schaal → Postgres (zie README, Blok 3).
DB_PATH = os.environ.get("DB_PATH", "toteco.db")
