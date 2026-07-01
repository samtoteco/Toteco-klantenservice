"""
Promptlaag.

C1: de prompt is code. Hij staat op één plek, heeft een versienummer, en
elke analyse legt vast met welke promptversie hij gemaakt is (in de store).
Wijzig je de prompt → verhoog PROMPT_VERSIE.
"""
from analysis.taxonomy import ONDERWERPEN, SENTIMENTEN

PROMPT_VERSIE = "2026-07-01.1"


def bouw_prompt(transcript: str, klant_context: str = "") -> str:
    onderwerpen = "\n".join(f"- {o}" for o in ONDERWERPEN)
    sentimenten = " / ".join(SENTIMENTEN)

    return f"""Je bent een analist voor de klantenservice van Toteco (zonnepanelen, warmtepompen, thuisbatterijen).
Analyseer het onderstaande telefoongesprek en classificeer het.

Kies het onderwerp UITSLUITEND uit deze vaste lijst (kies er precies één, de best passende):
{onderwerpen}

Kies het sentiment uit: {sentimenten}
(bekeken vanuit de klant: hoe voelde het gesprek voor de klant?)

{klant_context}

Transcript:
\"\"\"
{transcript}
\"\"\"

Antwoord ALLEEN met geldige JSON, exact deze velden en niets erbuiten:
{{
  "onderwerp": "<één waarde uit de lijst hierboven>",
  "sentiment": "<positief|neutraal|negatief>",
  "samenvatting": "<1-2 zinnen, feitelijk>",
  "actiepunten": ["<eventuele vervolgactie>", "..."]
}}"""
