"""Operator decision 2026-09-30: every default language is English and the product shows no Chinese.

Scans product code, UI tests' inputs and the contract fixtures for CJK characters.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]")


def _files():
    yield from sorted((ROOT / "fixtures").glob("*.json"))
    yield from sorted((ROOT / "backend" / "app").rglob("*.py"))
    yield from sorted((ROOT / "backend" / "app" / "data").glob("*.json"))
    yield ROOT / "frontend" / "index.html"
    for p in sorted((ROOT / "frontend" / "src").rglob("*")):
        if p.suffix in {".js", ".jsx", ".css"}:
            yield p


def test_no_chinese_in_product_code_or_fixtures():
    hits = []
    for path in _files():
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if CJK.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{n}")
    assert hits == []


def test_mei_and_fixture_language_default_to_english():
    import json

    assert json.loads((ROOT / "fixtures" / "timeline.json").read_text())["language"] == "en"
    assert json.loads((ROOT / "backend" / "app" / "data" / "mei.json").read_text())["language"] == "en"
