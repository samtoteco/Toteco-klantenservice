"""
Datalaag.

Enige plek waar we naar de database schrijven/lezen. De rest van de app
kent de opslag niet; die roept alleen deze functies aan.

Bron van waarheid: deze store bezit ALLEEN afgeleide/operationele data
(gespreks-callid's die binnenkwamen + de AI-analyse). Voys blijft eigenaar
van transcript/opname, Sollit van klantdata.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config


def _now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn():
    con = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    """Maakt de tabellen aan als ze nog niet bestaan."""
    with _conn() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS calls (
                callid        TEXT PRIMARY KEY,
                callerid      TEXT,
                did           TEXT,
                received_at   TEXT NOT NULL,
                -- pending | analyzed | failed | no_transcript
                status        TEXT NOT NULL DEFAULT 'pending',
                pogingen      INTEGER NOT NULL DEFAULT 0,
                updated_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analyses (
                callid          TEXT PRIMARY KEY,
                onderwerp       TEXT,
                sentiment       TEXT,
                samenvatting    TEXT,
                actiepunten     TEXT,          -- JSON-array als tekst
                klant_gevonden  INTEGER,       -- 0/1
                prompt_versie   TEXT,
                model           TEXT,
                created_at      TEXT NOT NULL,
                FOREIGN KEY (callid) REFERENCES calls(callid)
            );
            """
        )


# ── calls ──────────────────────────────────────────────────────

def registreer_call(callid, callerid, did):
    """Legt een binnengekomen gesprek vast (idempotent op callid)."""
    with _conn() as con:
        con.execute(
            """INSERT INTO calls (callid, callerid, did, received_at, status, updated_at)
               VALUES (?, ?, ?, ?, 'pending', ?)
               ON CONFLICT(callid) DO NOTHING""",
            (callid, callerid, did, _now(), _now()),
        )


def pending_calls(limit=50):
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM calls WHERE status = 'pending' ORDER BY received_at LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def zet_call_status(callid, status, pogingen=None):
    with _conn() as con:
        if pogingen is None:
            con.execute(
                "UPDATE calls SET status=?, updated_at=? WHERE callid=?",
                (status, _now(), callid),
            )
        else:
            con.execute(
                "UPDATE calls SET status=?, pogingen=?, updated_at=? WHERE callid=?",
                (status, pogingen, _now(), callid),
            )


# ── analyses ───────────────────────────────────────────────────

def bewaar_analyse(callid, analyse, klant_gevonden, prompt_versie, model):
    with _conn() as con:
        con.execute(
            """INSERT OR REPLACE INTO analyses
               (callid, onderwerp, sentiment, samenvatting, actiepunten,
                klant_gevonden, prompt_versie, model, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                callid,
                analyse["onderwerp"],
                analyse["sentiment"],
                analyse.get("samenvatting", ""),
                json.dumps(analyse.get("actiepunten", []), ensure_ascii=False),
                1 if klant_gevonden else 0,
                prompt_versie,
                model,
                _now(),
            ),
        )


# ── rapportage-aggregatie ──────────────────────────────────────

def aggregatie_onderwerpen():
    """Telt geanalyseerde gesprekken per onderwerp en per sentiment."""
    with _conn() as con:
        per_onderwerp = con.execute(
            "SELECT onderwerp, COUNT(*) n FROM analyses GROUP BY onderwerp ORDER BY n DESC"
        ).fetchall()
        per_sentiment = con.execute(
            "SELECT sentiment, COUNT(*) n FROM analyses GROUP BY sentiment"
        ).fetchall()
        totaal = con.execute("SELECT COUNT(*) n FROM analyses").fetchone()["n"]
    return {
        "totaal_geanalyseerd": totaal,
        "per_onderwerp": [dict(r) for r in per_onderwerp],
        "per_sentiment": [dict(r) for r in per_sentiment],
    }


def aggregatie_bereikbaarheid():
    """Telt alle binnengekomen gesprekken per status (bereikbaarheidsmeting)."""
    with _conn() as con:
        per_status = con.execute(
            "SELECT status, COUNT(*) n FROM calls GROUP BY status"
        ).fetchall()
        totaal = con.execute("SELECT COUNT(*) n FROM calls").fetchone()["n"]
    return {
        "totaal_gesprekken": totaal,
        "per_status": [dict(r) for r in per_status],
    }
