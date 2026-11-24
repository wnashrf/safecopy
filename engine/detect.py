"""detect(text) -> findings. Local only: Presidio + spaCy + Malaysian rules."""
import re

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import SpacyRecognizer

from engine.recognizers import INSTITUTION, NAME_WORDS, NOT_NAME, PLACES, malaysian_recognizers, words

MIN_SCORE = 0.3  # bank/passport without context words (0.1) stay below this

# Only our recognizers (incl. offline email) + spaCy names/places. Presidio's US/UK ones are left out
# (e.g. UK_NHS on MY phones).
_registry = RecognizerRegistry(supported_languages=["en"])
_registry.add_recognizer(SpacyRecognizer(supported_entities=["PERSON", "LOCATION"]))
for r in malaysian_recognizers():
    _registry.add_recognizer(r)

analyzer = AnalyzerEngine(registry=_registry, supported_languages=["en"])


TITLE_ONLY = {"tun", "tan", "sri", "seri", "puan", "toh", "datuk", "dato", "datin", "paduka", "haji", "hajah", "hj", "hjh"}


def _clean_model(text, f):
    """spaCy's English model tags Malay labels and common words as names/places. Returns 0+ cleaned findings.
    Each line of the span is judged on its own (in forms a line break is usually a cell border)."""
    out = []
    for line in re.finditer(r"[^\n]+", text[f["start"]:f["end"]]):
        g = dict(f, start=f["start"] + line.start(), end=f["start"] + line.end())
        toks = list(re.finditer(r"\S+", text[g["start"]:g["end"]]))

        def junk(m):
            w = m.group().strip(".,:;()'’")
            return not w or not w[0].isupper() or w.lower() in NOT_NAME

        while toks and junk(toks[0]):  # trim labels, lowercase words, dates off both ends
            toks.pop(0)
        while toks and junk(toks[-1]):
            toks.pop()
        if not toks:
            continue
        g["start"], g["end"] = g["start"] + toks[0].start(), g["start"] + toks[-1].end()
        ws = words(text[g["start"]:g["end"]])
        known = NAME_WORDS if g["type"] == "PERSON" else PLACES
        # lone capitalised Malay words ("Pekerjaan", "Bil", "Rabu") are dropped after merging, unless they
        # joined a neighbouring piece of the same name ("Nurul" + "Syahirah Azman")
        g["lone"] = len(ws) == 1 and ws[0] not in known
        if set(ws) <= TITLE_ONLY:  # "Tan Sri" on its own
            continue
        if g["type"] == "PERSON":
            before = words(text[:g["start"]])[-1:]  # "Dewan Seri Perdana": a building named after someone
            if (set(ws) | set(before)) & INSTITUTION:
                continue
            if set(ws) & PLACES:  # "Sungai Buloh", "Johor Bahru"
                g["type"] = "LOCATION"
        out.append(g)
    return out


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
            p["lone"] = False
        else:
            out.append(dict(f))
    return [f for f in out if not f.pop("lone", False)]


def detect(text):
    findings = []
    for r in analyzer.analyze(text=text, language="en", score_threshold=MIN_SCORE):
        f = {"type": r.entity_type, "start": r.start, "end": r.end, "score": round(r.score, 2),
             "source": "model" if r.recognition_metadata["recognizer_name"] == "SpacyRecognizer" else "rule"}
        findings += _clean_model(text, f) if f["source"] == "model" else [f]
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
