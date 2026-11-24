"""detect(text) -> findings. Local only: Presidio + spaCy + Malaysian rules."""
import re

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import EmailRecognizer, SpacyRecognizer

from engine.recognizers import INSTITUTION, NOT_NAME, PLACES, malaysian_recognizers, words

MIN_SCORE = 0.3  # bank/passport without context words (0.1) stay below this

# Only our recognizers + spaCy names/places + email. Presidio's US/UK ones are left out (e.g. UK_NHS on MY phones).
_registry = RecognizerRegistry(supported_languages=["en"])
_registry.add_recognizer(SpacyRecognizer(supported_entities=["PERSON", "LOCATION"]))
_registry.add_recognizer(EmailRecognizer())
for r in malaysian_recognizers():
    _registry.add_recognizer(r)

analyzer = AnalyzerEngine(registry=_registry, supported_languages=["en"])


def _clean_model_person(text, f):
    """spaCy's English model tags Malay labels and common words as names. Trim them off the ends;
    drop the span if it is an institution, relabel it if it is a place, drop it if nothing is left."""
    toks = [m for m in re.finditer(r"\S+", text[f["start"]:f["end"]])]

    def junk(m):
        w = m.group().strip(".,:;()'’")
        return not w or not w[0].isupper() or w.lower() in NOT_NAME

    while toks and junk(toks[0]):
        toks.pop(0)
    while toks and junk(toks[-1]):
        toks.pop()
    if not toks:
        return None
    f["end"] = f["start"] + toks[-1].end()
    f["start"] += toks[0].start()
    ws = set(words(text[f["start"]:f["end"]]))
    before = words(text[:f["start"]])[-1:]  # "Dewan Seri Perdana", "Hospital Sultanah Aminah": named after someone
    if (ws | set(before)) & INSTITUTION:
        return None
    if ws & PLACES:  # "Sungai Buloh", "Johor Bahru"
        f["type"] = "LOCATION"
    return f


def _merge_same_type(text, findings):
    """Join same-type findings that overlap or touch with only spaces between (e.g. "Datin Rosnah" + "Abdul Latif")."""
    # spaCy LOCATION and our MY_ADDRESS count as one kind, so "47000 Sungai Buloh" stays whole (postcode included).
    def kind(f):
        return "MY_ADDRESS" if f["type"] == "LOCATION" else f["type"]

    out = []
    for f in sorted(findings, key=lambda f: (kind(f), f["start"])):
        p = out[-1] if out else None
        if p and kind(p) == kind(f) and (f["start"] <= p["end"] or text[p["end"]:f["start"]].strip(" \t") == ""):
            if f["score"] > p["score"]:
                p["score"], p["source"] = f["score"], f["source"]
            if f["type"] == "MY_ADDRESS":
                p["type"] = "MY_ADDRESS"
            p["end"] = max(p["end"], f["end"])
        else:
            out.append(dict(f))
    return out


def detect(text):
    findings = []
    for r in analyzer.analyze(text=text, language="en", score_threshold=MIN_SCORE):
        f = {"type": r.entity_type, "start": r.start, "end": r.end, "score": round(r.score, 2),
             "source": "model" if r.recognition_metadata["recognizer_name"] == "SpacyRecognizer" else "rule"}
        if f["source"] == "model" and f["type"] == "PERSON":
            f = _clean_model_person(text, f)
        if f:
            findings.append(f)
    findings = _merge_same_type(text, findings)
    # Different types overlapping (e.g. a phone number also fits the bank pattern): keep highest score, then longest.
    findings.sort(key=lambda f: (f["score"], f["end"] - f["start"]), reverse=True)
    kept = []
    for f in findings:
        if all(f["end"] <= k["start"] or f["start"] >= k["end"] for k in kept):
            kept.append(f)
    for f in kept:
        f["text"] = text[f["start"]:f["end"]]
    return sorted(kept, key=lambda f: f["start"])
