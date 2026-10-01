import json
import types
from pathlib import Path

import anthropic
import httpx2 as httpx  # the installed anthropic SDK builds on httpx2
import pytest

from app import explain
from app.models import Check, ExplainResponse

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def load_checks():
    data = json.loads((FIXTURES / "checks.json").read_text(encoding="utf-8"))
    return [Check.model_validate(c) for c in data["checks"]]


CHECKS = load_checks()
R1 = next(c for c in CHECKS if c.rule == "R1")


def fake_response(text="Plain words.", stop_reason="end_turn"):
    blocks = [types.SimpleNamespace(type="thinking", thinking="x"),
              types.SimpleNamespace(type="text", text=text)]
    return types.SimpleNamespace(stop_reason=stop_reason, content=blocks)


class FakeClient:
    """Stands in for anthropic.Anthropic(); records the request."""

    def __init__(self, result):
        self.result = result
        self.kwargs = None
        self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


def install(monkeypatch, result):
    client = FakeClient(result)
    monkeypatch.setattr(explain.anthropic, "Anthropic", lambda *a, **k: client)
    return client


def status_error(cls, code):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx.Response(code, request=req)
    return cls("boom", response=resp, body=None)


def test_template_exact_for_r1():
    expected = (
        "Pay may be below the minimum rate\n"
        "• Check your award rate with the Fair Work Ombudsman Pay Calculator.\n"
        "• Keep your rosters, clock-in records and payslips.\n"
        "• A union or community legal centre can help for free.\n"
        "• Asking about your pay cannot get your visa cancelled by your employer."
    )
    assert explain.template(R1) == expected


@pytest.mark.parametrize("value", [None, ""])
def test_no_api_key_returns_template_without_client(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ANTHROPIC_API_KEY", value)

    def boom(*a, **k):
        raise AssertionError("client must not be constructed without a key")

    monkeypatch.setattr(explain.anthropic, "Anthropic", boom)
    result = explain.explain(R1, "zh-Hant")
    assert isinstance(result, ExplainResponse)
    assert result.source == "template"
    assert result.text == explain.template(R1)


def test_success_returns_ai_text(monkeypatch, with_key):
    client = install(monkeypatch, fake_response("Your pay may be low."))
    result = explain.explain(R1, "en")
    assert isinstance(result, ExplainResponse)
    assert result.source == "ai"
    assert result.text == "Your pay may be low."
    kw = client.kwargs
    assert kw["model"] == "claude-opus-5-5"
    assert kw["max_tokens"] == 2000
    assert kw["output_config"] == {"effort": "low"}
    assert kw["betas"] == ["server-side-fallback-2026-07-01"]
    assert kw["fallbacks"] == "default"
    assert kw["system"] == explain.SYSTEM
    assert kw["messages"][0]["content"].startswith("Language: en\nCheck:\n")


@pytest.mark.parametrize("exc", [
    anthropic.AuthenticationError("bad", response=httpx.Response(
        401, request=httpx.Request("POST", "https://x")), body=None),
    status_error(anthropic.APIStatusError, 500),
    anthropic.APIConnectionError(request=httpx.Request("POST", "https://x")),
    anthropic.APITimeoutError(request=httpx.Request("POST", "https://x")),
])
def test_api_errors_give_template(monkeypatch, with_key, exc):
    install(monkeypatch, exc)
    result = explain.explain(R1, "en")
    assert result.source == "template"
    assert result.text == explain.template(R1)


def test_refusal_gives_template(monkeypatch, with_key):
    install(monkeypatch, fake_response("partial", stop_reason="refusal"))
    result = explain.explain(R1, "en")
    assert result.source == "template"
    assert result.text == explain.template(R1)


@pytest.mark.parametrize("text", ["", ])
def test_empty_text_gives_template(monkeypatch, with_key, text):
    install(monkeypatch, fake_response(text))
    result = explain.explain(R1, "en")
    assert result.source == "template"
    assert result.text == explain.template(R1)


def test_unexpected_exception_propagates(monkeypatch, with_key):
    install(monkeypatch, ValueError("unexpected"))
    with pytest.raises(ValueError):
        explain.explain(R1, "en")


def test_payload_contains_only_selected_check(monkeypatch, with_key):
    client = install(monkeypatch, fake_response())
    explain.explain(R1, "en")
    content = client.kwargs["messages"][0]["content"]
    assert R1.check_id in content
    for other in CHECKS:
        if other.check_id != R1.check_id:
            assert other.check_id not in content
    payload = json.loads(content.split("Check:\n", 1)[1])
    # exactly the Check's own fields, nothing from the worker
    assert payload == json.loads(R1.model_dump_json())
    assert set(payload) == set(Check.model_fields)
    for key in ("visa", "shifts", "bank", "income", "sources", "worker_id", "display_name"):
        assert key not in payload
