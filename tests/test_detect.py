"""All data here is fictional: made-up names, format-valid numbers that belong to nobody."""
import pytest

from engine.detect import detect


def types_of(text):
    return {(f["type"], f["text"]) for f in detect(text)}


SAMPLE = ("Siti Aminah binti Rahman, MyKad 880512-10-5532, No. 12, Jalan Mawar 3, Taman Sri Kajang, "
          "43000 Kajang, 012-345 6789, account 1102 4400 8812 37")


def test_sample_record():
    found = types_of(SAMPLE)
    assert ("PERSON", "Siti Aminah binti Rahman") in found
    assert ("MY_MYKAD", "880512-10-5532") in found
    assert ("MY_PHONE", "012-345 6789") in found
    assert ("MY_BANK_ACCOUNT", "1102 4400 8812 37") in found


@pytest.mark.parametrize("text,ic", [
    ("No. KP pemohon: 900101-14-5678.", "900101-14-5678"),
    ("NRIC 900101145678 dilampirkan.", "900101145678"),
    ("IC lahir tahun lompat 000229-01-1234.", "000229-01-1234"),
])
def test_mykad_caught(text, ic):
    assert ("MY_MYKAD", ic) in types_of(text)


@pytest.mark.parametrize("text", [
    "IC 881345-10-5532 tidak sah.",   # month 13
    "IC 880230-10-5532 tidak sah.",   # 30 Feb
    "IC 010229-10-5532 tidak sah.",   # 29 Feb in a non-leap year (1901 and 2001)
])
def test_invalid_mykad_date_not_caught(text):
    assert not any(t == "MY_MYKAD" for t, _ in types_of(text))


@pytest.mark.parametrize("phone", [
    "012-345 6789", "0123456789", "011-2345 6789", "+60 12-345 6789", "+6011 2345 6789", "03-8765 4321",
])
def test_phone_caught(phone):
    assert ("MY_PHONE", phone) in types_of(f"Sila hubungi {phone} selepas 5 petang.")


def test_phone_not_tagged_uk_nhs():
    assert not any(f["type"] == "UK_NHS" for f in detect("Tel: 012-345 6789"))


def test_bank_needs_context():
    assert ("MY_BANK_ACCOUNT", "5642 1234 5678") in types_of("No. akaun Maybank: 5642 1234 5678")
    assert not any(t == "MY_BANK_ACCOUNT" for t, _ in types_of("Rujukan fail 5642 1234 5678 sahaja."))


def test_passport_needs_context():
    assert ("MY_PASSPORT", "A12345678") in types_of("No. pasport A12345678 tamat 2029.")
    assert not any(t == "MY_PASSPORT" for t, _ in types_of("Kod produk A12345678."))


@pytest.mark.parametrize("name", [
    "Muhammad Hafiz bin Abdullah", "Nurul Izzah binti Kamal", "Rajesh a/l Subramaniam",
    "Kavitha a/p Muniandy", "AHMAD FAIZAL BIN OSMAN",
])
def test_patronymic_names_found(name):
    assert ("PERSON", name) in types_of(f"Pemohon {name} hadir pada 3 Mac.")


def test_findings_shape():
    f = detect(SAMPLE)[0]
    assert set(f) >= {"type", "start", "end", "score", "source"}
    assert f["source"] in {"rule", "model"}
    assert SAMPLE[f["start"]:f["end"]] == f["text"]


# --- Day 2: names without bin/binti, titles, wrong-hit cleanup, addresses ---

@pytest.mark.parametrize("text,name", [
    ("Nama: Zulaikha Rosli\nNo. KP: 900101-14-5678", "Zulaikha Rosli"),          # label, not crossing the line
    ("Kepada Datin Rosnah Abdul Latif,", "Datin Rosnah Abdul Latif"),             # title kept, spaCy pieces joined
    ("Laporan disediakan oleh Teoh Jia Hui pada 5 Jun 2026.", "Teoh Jia Hui"),    # trailing date trimmed
    ("Sila hubungi Encik Farid Kamil di pejabat.", "Farid Kamil"),                # honorific dropped
])
def test_name_spans(text, name):
    assert [f["text"] for f in detect(text) if f["type"] == "PERSON"] == [name]


@pytest.mark.parametrize("text", [
    "Jabatan Pendaftaran Negara Putrajaya menerima permohonan.",
    "Rawatan di Hospital Sultanah Aminah, Johor Bahru.",
    "Mesyuarat Agung Tahunan akan diadakan di Dewan Seri Perdana.",
    "Kepada Yang Berkenaan,",
    "Emel: pentadbir@contoh.my",
])
def test_no_name_in_malay_institution_text(text):
    assert not any(f["type"] == "PERSON" for f in detect(text))


def test_address_parts():
    found = types_of(SAMPLE)
    assert ("MY_ADDRESS", "No. 12, Jalan Mawar 3") in found
    assert ("MY_ADDRESS", "Taman Sri Kajang") in found
    assert ("MY_ADDRESS", "Jalan Tun Razak") in types_of("Jalan Tun Razak ditutup.")  # address, not a person


def test_postcode_not_left_behind():
    found = types_of("Alamat: Lot 88, Kampung Baru Sungai Buloh, 47000 Sungai Buloh, Selangor.")
    assert ("MY_ADDRESS", "47000 Sungai Buloh") in found
