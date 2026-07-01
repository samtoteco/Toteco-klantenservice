"""
AI-aanroep. Roept Claude aan en parseert de JSON. Doet GEEN validatie —
dat is de taak van validation.py (bewust gescheiden).
"""
import json

import anthropic

import config
from analysis.prompt import bouw_prompt, PROMPT_VERSIE


def analyseer_transcript(transcript: str, klant_context: str = ""):
    """Geeft (ruwe_dict, prompt_versie, model) terug. Kan exceptions gooien."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.ANALYSIS_MODEL,
        max_tokens=800,
        temperature=config.ANALYSIS_TEMPERATURE,
        messages=[{"role": "user", "content": bouw_prompt(transcript, klant_context)}],
    )
    text = msg.content[0].text.strip()
    # Robuust tegen ```json ... ``` fences
    text = text.replace("```json", "").replace("```", "").strip()
    ruw = json.loads(text)
    return ruw, PROMPT_VERSIE, config.ANALYSIS_MODEL
