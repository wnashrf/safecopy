"""Measure Malaysian name detection on fictional names. Run: .venv/Scripts/python -m tests.name_accuracy

Day 1 set: used while tuning. Held-out set: names and sentence shapes written on day 2 BEFORE tuning,
never tuned against, so its score is the honest one. No-name set: counts wrong PERSON hits.
"""
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import SpacyRecognizer

from engine.detect import analyzer, detect

DAY1_NAMES = [
    # patronymic (bin/binti/a/l/a/p/anak)
    "Siti Aminah binti Rahman", "Muhammad Hafiz bin Abdullah", "Nurul Izzah binti Kamal",
    "Mohd Faizal bin Osman", "Wan Nur Aisyah binti Wan Ismail", "Ahmad Zaki bin Hassan",
    "Rajesh a/l Subramaniam", "Kavitha a/p Muniandy", "Jimmy anak Jugah", "NOR AZLINA BINTI YUSOF",
    # no patronymic: Malay short form, Chinese, Indian, Kadazan, titles
    "Aminah Rahman", "Tan Wei Ming", "Lim Mei Ling", "Wong Kar Seng", "Priya Devi",
    "Hafizah Zainal", "Ong Bee Lian", "Dato' Seri Kamarul Ariffin", "Juliana Gimbang", "Farid Kamil",
]
DAY1_TEMPLATES = [
    "Pemohon {} telah menghantar borang pada 3 Mac 2026.",
    "Please contact {} regarding the claim.",
]

HELDOUT_NAMES = [
    "Nik Aiman bin Nik Mahmud", "Sharifah Nadia binti Syed Hamzah", "Haslinda binti Mat Isa",
    "Thinesh a/l Rajendran", "Saraswathy a/p Kandasamy", "Richard anak Ngumbang",
    "Tan Sri Lee Chong Hock", "Datin Rosnah Abdul Latif", "Haji Ismail Kassim",
    "Chong Siew Ling", "Yap Kok Wai", "Teoh Jia Hui", "Ng Boon Keat", "Arumugam Velu", "Deepa Nair",
    "Nurul Syahirah Azman", "Aqil Haziq", "Zulaikha Rosli", "Mohd Amirul Hakim", "Linda Masidi",
]
HELDOUT_TEMPLATES = [
    "Nama: {}\nNo. KP: 900101-14-5678",
    "Kepada {},\nTerima kasih atas permohonan anda.",
    "The claimant, {}, was admitted on 3 March.",
    "Laporan disediakan oleh {} pada 5 Jun 2026.",
]

NO_NAME = [
    "Jabatan Pendaftaran Negara Putrajaya menerima permohonan.",
    "Bank Islam Malaysia Berhad menghantar penyata.",
    "Rawatan di Hospital Sultanah Aminah, Johor Bahru.",
    "Universiti Kebangsaan Malaysia membuka pendaftaran.",
    "Emel: pentadbir@contoh.my",
    "Sila hubungi Khidmat Pelanggan untuk maklumat lanjut.",
    "Kepada Yang Berkenaan,",
    "See Attachment A for the claim form.",
    "Tan Brothers Trading Sdn Bhd menghantar invois.",
    "Mesyuarat Agung Tahunan akan diadakan di Dewan Seri Perdana.",
    "Jalan Tun Razak ditutup untuk perarakan.",
    "Majlis Perbandaran Kajang meluluskan permit.",
    "Kementerian Kesihatan Malaysia mengeluarkan pekeliling.",
    "Terima kasih atas kerjasama tuan.",
    "Please Sign Here and Return Before Friday.",
]


def score(spans, start, end):
    """exact = a PERSON span equals the name; full = covers it (maybe with extra words); partial = overlaps."""
    if (start, end) in spans:
        return "exact"
    if any(s <= start and e >= end for s, e in spans):
        return "full"
    if any(s < end and e > start for s, e in spans):
        return "partial"
    return "miss"


_spacy_only = AnalyzerEngine(nlp_engine=analyzer.nlp_engine, registry=RecognizerRegistry(
    recognizers=[SpacyRecognizer(supported_entities=["PERSON"])], supported_languages=["en"]))


def model_spans(text):
    return [(r.start, r.end) for r in _spacy_only.analyze(text=text, language="en", entities=["PERSON"])]


def combined_spans(text):
    return [(f["start"], f["end"]) for f in detect(text) if f["type"] == "PERSON"]


def run_set(label, names, templates, verbose):
    tally = {"spaCy only": {}, "combined": {}}
    for name in names:
        row = []
        for tpl in templates:
            text = tpl.format(name)
            start = text.index(name)
            for key, fn in (("spaCy only", model_spans), ("combined", combined_spans)):
                res = score(fn(text), start, start + len(name))
                tally[key][res] = tally[key].get(res, 0) + 1
                if key == "combined":
                    row.append(res)
        if verbose:
            print(f"  {name:34} {' '.join(f'{r:7}' for r in row)}")
    n = len(names) * len(templates)
    for key, t in tally.items():
        found = t.get("exact", 0) + t.get("full", 0)
        print(f"{label:9} {key:10} found {found:2}/{n} (exact {t.get('exact', 0)}, "
              f"wider {t.get('full', 0)})  partial {t.get('partial', 0)}  miss {t.get('miss', 0)}")


def main(verbose=True):
    run_set("day1", DAY1_NAMES, DAY1_TEMPLATES, verbose)
    run_set("held-out", HELDOUT_NAMES, HELDOUT_TEMPLATES, verbose)
    # Same held-out set with every held-out name part removed from the name list: names the list has never seen.
    from engine import recognizers
    seen = {w for n in HELDOUT_NAMES for w in recognizers.words(n)} & recognizers.NAME_WORDS
    recognizers.NAME_WORDS -= seen
    print(f"(removing {len(seen)} held-out name parts from the name list: {' '.join(sorted(seen))})")
    run_set("unseen", HELDOUT_NAMES, HELDOUT_TEMPLATES, False)
    recognizers.NAME_WORDS |= seen
    wrong = [(t, f["text"]) for t in NO_NAME for f in detect(t) if f["type"] == "PERSON"]
    print(f"no-name   wrong PERSON hits: {len(wrong)} in {len(NO_NAME)} sentences")
    for t, w in wrong:
        print(f"  {w!r:30} in {t!r}")


if __name__ == "__main__":
    main()
