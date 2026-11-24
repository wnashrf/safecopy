"""Malaysian PII recognizers for Presidio."""
import re
from datetime import date
from pathlib import Path

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.predefined_recognizers import EmailRecognizer


class MyKadRecognizer(PatternRecognizer):
    """MyKad / NRIC: YYMMDD-PB-###G, dashes optional. Drops matches whose birth date is not a real date."""

    def __init__(self):
        super().__init__(
            supported_entity="MY_MYKAD",
            name="MyKadRecognizer",
            patterns=[
                Pattern("mykad_dashed", r"\b\d{6}-\d{2}-\d{4}\b", 0.7),
                Pattern("mykad_plain", r"\b\d{12}\b", 0.4),
            ],
            context=["mykad", "ic", "nric", "kad pengenalan", "no. kp", "kp", "identity card"],
        )

    def invalidate_result(self, pattern_text):
        d = re.sub(r"\D", "", pattern_text)
        yy, mm, dd = int(d[:2]), int(d[2:4]), int(d[4:6])
        # 2-digit year: valid if the date exists in either the 1900s or 2000s (covers 29 Feb)
        for century in (1900, 2000):
            try:
                date(century + yy, mm, dd)
                return False
            except ValueError:
                pass
        return True


# Mobile 01X-XXX XXXX, 011-XXXX XXXX; landline 0X-XXXX XXXX (also 7-digit subscriber); optional +60.
MY_PHONE = PatternRecognizer(
    supported_entity="MY_PHONE",
    name="MyPhoneRecognizer",
    patterns=[
        Pattern("my_mobile", r"(?:\+?60[\s-]?|\b0)1(?:1[\s-]?\d{4}|[02-9][\s-]?\d{3})[\s-]?\d{4}\b", 0.6),
        Pattern("my_landline", r"(?:\+?60[\s-]?|\b0)[3-9][\s-]?\d{3,4}[\s-]?\d{4}\b", 0.4),
    ],
    context=["tel", "telefon", "phone", "hp", "mobile", "bimbit", "hubungi", "contact", "call"],
)

# 10-16 digits with optional space/dash groups. Low base score: only context words lift it over the threshold.
MY_BANK_ACCOUNT = PatternRecognizer(
    supported_entity="MY_BANK_ACCOUNT",
    name="MyBankAccountRecognizer",
    patterns=[Pattern("my_bank_account", r"\b\d(?:[\s-]?\d){9,15}\b", 0.1)],
    context=["akaun", "account", "acc", "a/c", "bank", "maybank", "cimb", "rhb", "bsn"],
)

MY_PASSPORT = PatternRecognizer(
    supported_entity="MY_PASSPORT",
    name="MyPassportRecognizer",
    patterns=[Pattern("my_passport", r"\b[A-Z]\d{8}\b", 0.1)],
    context=["passport", "pasport"],
)

_MONTHS = ("januari|februari|mac|april|mei|jun|julai|ogos|september|oktober|november|disember|"
           "january|february|march|may|june|july|august|october|december|"
           "jan|feb|mar|apr|jul|aug|ogo|sep|sept|okt|oct|nov|dis|dec")


class DateOfBirthRecognizer(PatternRecognizer):
    """A date is only a date of birth with a birth word just before it ("Tarikh Lahir", "Date of birth", "DOB").
    Base score is below MIN_SCORE, so letter dates without such context are not flagged."""

    def __init__(self):
        super().__init__(
            supported_entity="DATE_OF_BIRTH",
            name="DateOfBirthRecognizer",
            patterns=[
                Pattern("dob_numeric", r"\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}\b", 0.1),
                Pattern("dob_text", rf"\b\d{{1,2}}\s+(?i:{_MONTHS})\.?\s+(?:19|20)\d{{2}}\b", 0.1),
            ],
            context=["lahir", "birth", "dob", "born"],
        )

    def invalidate_result(self, pattern_text):
        parts = re.split(r"[/.-]", pattern_text)
        if len(parts) != 3:
            return False  # text month: the regex already limits it
        try:
            date(int(parts[2]), int(parts[1]), int(parts[0]))  # Malaysian order: day/month/year
            return False
        except ValueError:
            return True


class OfflineEmailRecognizer(EmailRecognizer):
    """Presidio checks the domain ending with tldextract, which downloads the public suffix list from the
    internet and rejects unknown endings (internal domains). Skip that check: no network, better recall."""

    def validate_result(self, pattern_text):
        return None


# --- Addresses -------------------------------------------------------------------------------
_SEP = r"[ \t]+"  # name/address words stay on one line...
_SEP_WRAP = r"(?:[ \t]+|[ \t]*\n[ \t]*)"  # ...except where a line wrap is expected
_ADDR_KW = (r"(?:(?i:jalan|jln|lorong|lrg|persiaran|lebuhraya|lebuh|taman|tmn|kampung|kampong|lengkok|"
            r"lingkaran|pangsapuri|apartment|desa|bandar)|Kg)")
_ADDR_WORD = r"[A-Z0-9][\w'’/-]*"
MY_ADDRESS = PatternRecognizer(
    supported_entity="MY_ADDRESS",
    name="MyAddressRecognizer",
    patterns=[
        # "No. 12, Jalan Mawar 3", "18, Jalan SS 2/24", "Lot 88 Kampung Baru", "Taman Sri Kajang";
        # the street name may wrap to the next line right after "Jalan"
        Pattern("street", rf"(?:(?:\b(?i:no|lot|unit)\.?[ \t]*[\dA-Z][\w/-]*|\b\d+[A-Z]?(?:-\d+)?),?{_SEP})?"
                          rf"\b{_ADDR_KW}\.?{_SEP_WRAP}{_ADDR_WORD}(?:{_SEP}{_ADDR_WORD}){{0,4}}", 0.9),
        # postcode (01000-98999) + town: "43000 Kajang"
        Pattern("postcode_town", r"\b(?:0[1-9]|[1-8]\d|9[0-8])\d{3}[ \t]+[A-Z][A-Za-z]+(?:[ \t]+[A-Z][A-Za-z]+){0,2}", 0.6),
    ],
    context=["alamat", "address", "poskod", "postcode", "tinggal", "residing"],
    global_regex_flags=re.MULTILINE,
)

# --- Names -----------------------------------------------------------------------------------
# Capitalised words that sit next to names in forms/letters but are not names: labels, honorifics,
# Malay function words that start sentences, months. Also used to trim spaCy's PERSON spans.
# shortcut: hand-made lists, grow them from demo docs; swap for a Malay-trained NER model if they get long.
NOT_NAME = set("""
pemohon nama penama pelanggan pesakit waris pengadu saksi penuntut penerima tertuduh no alamat emel email tel telefon
tarikh rujukan ruj perkara sila hubungi terima kasih doktor doctor pegawai officer pengurus manager
kerani jururawat nurse rawatan laporan kepada daripada saya kami anda yang berkenaan berhormat hormat
encik en puan pn cik tuan mr mrs ms madam dr prof ir dear name customer applicant patient claimant complainant
witness insured beneficiary contact please to from the and of di dan pada oleh untuk dengan atas dari ke ini itu
person borang permohonan urus setia lampiran maklumat minit
januari februari mac april jun julai ogos september oktober november disember
january february march may june july august october december jan feb mar apr jul aug sep sept oct nov dec
""".split())
# A span containing one of these is an organisation/place/event, not a person.
INSTITUTION = set("""
jabatan kementerian majlis universiti hospital klinik sekolah kolej institut masjid surau dewan mesyuarat bank
syarikat persatuan lembaga pejabat mahkamah polis perbandaran bandaraya daerah kerajaan pusat jalan taman kampung
lorong persiaran sdn bhd berhad trading enterprise agung tahunan kebangsaan negara pendaftaran kesihatan pelajaran
khidmat bahagian unit seksyen company ministry department university school court council
yayasan kompleks menara wisma bangunan pentadbiran foundation
""".split())
PLACES = set("""
johor kedah kelantan melaka pahang perak perlis pinang penang sabah sarawak selangor terengganu sembilan putrajaya
labuan lumpur bahru kajang ipoh kuching kinabalu seremban klang shah alam petaling bangi cyberjaya
sungai bukit kuala pulau tanjung teluk kota batu simpang padang
""".split())
NAME_WORDS = {w.strip() for w in (Path(__file__).parent / "data" / "my_names.txt").read_text(encoding="utf-8").splitlines()
              if w.strip() and not w.startswith("#")}

_NOT_NAME_RX = "|".join(sorted(NOT_NAME, key=len, reverse=True))
_W = rf"(?!(?i:{_NOT_NAME_RX})\b)[A-Z][A-Za-z'’@-]+"  # one capitalised name word
_TITLE = (r"(?i:tun|tan{s}sri|puan{s}sri|toh{s}puan|datuk{s}seri|dato['’]?{s}s(?:e)?ri|datuk|dato['’]?|"
          r"datin{s}paduka|datin{s}seri|datin|haji|hajah|hjh?\.?|ustazah|ustaz)").format(s=_SEP)
_HONORIFIC = r"(?i:encik|en|puan|pn|cik|tuan|mr|mrs|ms|madam|dr|prof|ir)\.?"
_LABEL = (r"(?i:nama|penama|pemohon|pesakit|waris|pelanggan|pengadu|saksi|penuntut|penerima|"
          r"name|applicant|patient|claimant|complainant|witness|insured|beneficiary)")


def words(s):
    return [w.strip(".,:;()'’").lower() for w in s.split()]


class MalaysianNameRecognizer(EntityRecognizer):
    """Rules for names spaCy (English) misses or cuts short. The name is the `name` group of each regex."""

    RULES = [
        # "Siti Aminah binti Rahman", "Rajesh a/l Subramaniam", "Jimmy anak Jugah"
        # may wrap in a narrow table cell: "Muhammad Aiman Hakimi\nbin Zulkarnain"
        ("patronymic", 0.9, rf"\b(?P<name>{_W}(?:{_SEP_WRAP}{_W}){{0,3}}{_SEP_WRAP}"
                            rf"(?i:bin|binti|bt|bte|a/l|a/p|anak){_SEP_WRAP}{_W}(?:{_SEP_WRAP}{_W}){{0,3}})"),
        # title is part of the name: "Dato' Seri Kamarul Ariffin", "Haji Ismail Kassim"
        ("title", 0.85, rf"\b(?P<name>{_TITLE}(?:{_SEP}{_W}){{1,5}})"),
        # honorific is not: "Encik Farid Kamil" -> "Farid Kamil"
        ("honorific", 0.8, rf"\b{_HONORIFIC}{_SEP}(?P<name>{_W}(?:{_SEP}{_W}){{0,4}})"),
        # form label: "Nama: Zulaikha Rosli"
        ("label", 0.75, rf"\b{_LABEL}\b[ \t]*[:\-]?\s*(?P<name>{_W}(?:{_SEP}{_W}){{0,5}})"),
    ]
    _RUN = re.compile(rf"\b{_W}(?:{_SEP}{_W}){{1,4}}")  # 2-5 capitalised words, checked against NAME_WORDS

    def __init__(self):
        super().__init__(supported_entities=["PERSON"], name="MalaysianNameRecognizer")
        self._rules = [(n, s, re.compile(rx)) for n, s, rx in self.RULES]

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        spans = [(m.start("name"), m.end("name"), score) for _, score, rx in self._rules for m in rx.finditer(text)]
        spans += [(m.start(), m.end(), 0.6) for m in self._RUN.finditer(text) if NAME_WORDS & set(words(m.group()))]
        meta = {RecognizerResult.RECOGNIZER_NAME_KEY: self.name, RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: self.id}
        return [RecognizerResult("PERSON", s, e, score, recognition_metadata=meta)
                for s, e, score in spans
                if not (INSTITUTION | PLACES) & set(words(text[s:e]))]


def malaysian_recognizers():
    return [OfflineEmailRecognizer(), DateOfBirthRecognizer(), MyKadRecognizer(), MY_PHONE, MY_BANK_ACCOUNT, MY_PASSPORT, MY_ADDRESS, MalaysianNameRecognizer()]
