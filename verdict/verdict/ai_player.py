from __future__ import annotations

import anthropic

_CLIENT = None


def _client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic()
    return _CLIENT


def ai_argue(case: dict, history: list[dict], role: str) -> str:
    opponent = "defense" if role == "prosecution" else "prosecution"
    prior = "\n".join(
        f"[{h['role'].upper()}]: {h['argument']}" for h in history
    ) or "No arguments yet — you go first."

    prompt = f"""You are playing the {role.upper()} in a courtroom argument game called VERDICT.
Your goal: push the guilty probability {"above 85%" if role == "prosecution" else "below 15%"}.

CASE: {case['title']}
CHARGE: {case['charge']}
DEFENDANT: {case['defendant']}

FACTS:
{chr(10).join(f'- {f}' for f in case['facts'])}

EVIDENCE:
{chr(10).join(f'- {e}' for e in case['evidence'])}

PRIOR ARGUMENTS:
{prior}

Your role: {role.upper()}
Make your argument. Be specific, reference evidence directly, be sharp and persuasive.
3-5 sentences. No preamble like "As the prosecution..." — just argue."""

    response = _client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
