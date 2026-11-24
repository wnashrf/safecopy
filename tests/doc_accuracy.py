"""Measure detect() on the fictional demo PDFs against demo/docs/truth.json.
Run: .venv/Scripts/python -m demo.make_docs && .venv/Scripts/python -m tests.doc_accuracy

A value counts as found when every non-space character of it is inside some finding (any type: for
redaction, covered is what matters). Wrong hits are findings that touch no expected value.
"""
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf

from demo.make_docs import GAP_TYPES, OUT
from engine.detect import detect


def measure(pdf, expected):
    text = "".join(page.get_text() for page in pymupdf.open(pdf))
    findings = detect(text)
    covered = [False] * len(text)
    for f in findings:
        covered[f["start"]:f["end"]] = [True] * (f["end"] - f["start"])
    results, truth_spans = [], []
    for kind, value in expected:
        rx = r"\s+".join(map(re.escape, value.split()))  # value may wrap onto the next line
        occ = [m.span() for m in re.finditer(rx, text)]
        truth_spans += occ
        if not occ:
            results.append((kind, value, "not in extracted text"))
        for s, e in occ:
            chars = [covered[i] for i in range(s, e) if not text[i].isspace()]
            res = "found" if all(chars) else "partial" if any(chars) else "missed"
            results.append((kind, value, res))
    wrong = [f for f in findings if not any(f["start"] < e and f["end"] > s for s, e in truth_spans)]
    return results, wrong


def main():
    truth = json.loads((OUT / "truth.json").read_text(encoding="utf-8"))
    per_type, misses, wrongs = {}, [], []
    for name, expected in truth.items():
        results, wrong = measure(OUT / name, expected)
        c = Counter(r for k, _, r in results if k not in GAP_TYPES)
        n = sum(c.values())
        print(f"{name:26} found {c['found']:2}/{n}  partial {c['partial']}  missed {c['missed']}  wrong hits {len(wrong)}")
        for kind, value, res in results:
            per_type.setdefault(kind, Counter())[res] += 1
            if res != "found":
                misses.append((name, kind, value, res))
        wrongs += [(name, f["type"], f["text"]) for f in wrong]
    print("\nby type (occurrences):")
    for kind, c in sorted(per_type.items()):
        tag = "  <- not detected yet (known gap)" if kind in GAP_TYPES else ""
        print(f"  {kind:16} found {c['found']:2}/{sum(c.values()):2}  partial {c['partial']}  missed {c['missed']}{tag}")
    print("\nnot fully found:")
    for m in misses:
        print(f"  {m[0]:26} {m[1]:15} {m[2]!r:42} {m[3]}")
    print("\nwrong hits (flagged, not personal data in the answer key):")
    for w in wrongs:
        print(f"  {w[0]:26} {w[1]:15} {w[2]!r}")


if __name__ == "__main__":
    main()
