"""Plain-language explanation of one Check; AI rewords only, template fallback.
interfaces.explain_check delegates here."""

import os

import anthropic

from app.models import Check, ExplainResponse

SYSTEM = (
    "You explain a pay or visa-hours check to a worker in plain language. "
    "Use only the facts provided; never invent numbers. "
    "Say the pay 'may' be wrong; never say the employer broke the law. "
    "Reply in the requested language, under 120 words, then list the next steps."
)


def template(check: Check) -> str:
    return f"{check.title}\n" + "\n".join(f"• {step}" for step in check.next_steps)


def _fallback(check: Check) -> ExplainResponse:
    return ExplainResponse(text=template(check), source="template")


def explain(check: Check, language: str) -> ExplainResponse:
    """Explain ONE check. The AI only rewords its numbers; it computes nothing."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _fallback(check)
    try:
        client = anthropic.Anthropic()
        response = client.beta.messages.create(
            model="claude-opus-5-5",
            max_tokens=2000,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            messages=[{"role": "user",
                       "content": f"Language: {language}\nCheck:\n{check.model_dump_json()}"}],
        )
    except anthropic.AuthenticationError:
        return _fallback(check)
    except (anthropic.APIStatusError, anthropic.APIConnectionError):
        return _fallback(check)
    if response.stop_reason == "refusal":
        return _fallback(check)
    text = "".join(b.text for b in response.content if b.type == "text")
    if not text.strip():
        return _fallback(check)
    return ExplainResponse(text=text, source="ai")
