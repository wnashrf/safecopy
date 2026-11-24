"""All data here is fictional: made-up names, format-valid numbers that belong to nobody."""
import pytest

from engine.detect import detect


def types_of(text):
    return {(f["type"], f["text"]) for f in detect(text)}


SAMPLE = ("Siti Aminah binti Rahman, MyKad 880512-17-5532, No. 12, Jalan Mawar 3, Taman Sri Kajang, "
          "43000 Kajang, 012-345 6789, account 1102 4400 8812 37")


def test_sample_record():
    found = types_of(SAMPLE)
    assert ("PERSON", "Siti Aminah binti Rahman") in found
    assert ("MY_MYKAD", "880512-17-5532") in found
    assert ("MY_PHONE", "012-345 6789") in found
    assert ("MY_BANK_ACCOUNT", "1102 4400 8812 37") in found


@pytest.mark.parametrize("text,ic", [
    ("No. KP pemohon: 900101-18-5678.", "900101-18-5678"),
    ("NRIC 900101185678 dilampirkan.", "900101185678"),
    ("IC lahir tahun lompat 000229-19-1234.", "000229-19-1234"),
])
def test_mykad_caught(text, ic):
    assert ("MY_MYKAD", ic) in types_of(text)


@pytest.mark.parametrize("text", [
    "IC 881345-17-5532 tidak sah.",   # month 13
    "IC 880230-17-5532 tidak sah.",   # 30 Feb
    "IC 010229-17-5532 tidak sah.",   # 29 Feb in a non-leap year (1901 and 2001)
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
    ("Nama: Zulaikha Rosli\nNo. KP: 900101-18-5678", "Zulaikha Rosli"),          # label, not crossing the line
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


# --- Day 3: demo documents, wraps, no network ---

def test_no_network_during_detect(monkeypatch):
    """The pitch says nothing leaves the laptop: detection must not open any connection."""
    import socket

    def blocked(*a, **k):
        raise AssertionError("detect() tried to open a network connection")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    found = types_of("Emel: siti.aminah@jabatan.gov.my, intranet: admin@hr.internal")
    assert ("EMAIL_ADDRESS", "siti.aminah@jabatan.gov.my") in found
    assert ("EMAIL_ADDRESS", "admin@hr.internal") in found  # internal domains count too


def test_wrapped_patronymic_in_table_cell():
    assert ("PERSON", "Muhammad Aiman Hakimi\nbin Zulkarnain") in types_of("1\nMuhammad Aiman Hakimi\nbin Zulkarnain\n910304-17-5571")


@pytest.mark.parametrize("addr", ["18, Jalan SS 2/24", "No. 7, Jalan Kenanga 2/1", "Jalan\nCempaka 5"])
def test_street_forms(addr):
    assert ("MY_ADDRESS", addr) in types_of(f"Alamat di {addr}, Taman Seri Murni.")


def test_lone_form_words_not_names():
    text = "Perkara\nMaklumat\nPekerjaan\nPEMANDU LORI\nBil\nNama\nMasa: 10.00 pagi"
    assert not any(f["type"] == "PERSON" for f in detect(text))


def test_demo_documents_fully_found():
    from demo.make_docs import GAP_TYPES
    from demo.make_docs import main as make_docs
    from tests.doc_accuracy import OUT, json, measure
    make_docs()
    for name, expected in json.loads((OUT / "truth.json").read_text(encoding="utf-8")).items():
        results, _ = measure(OUT / name, expected)
        misses = [r for r in results if r[0] not in GAP_TYPES and r[2] != "found"]
        assert not misses, (name, misses)


@pytest.mark.parametrize("text,dob", [
    ("Tarikh Lahir\n23/08/2005", "23/08/2005"),
    ("Date of birth: 7 August 1981", "7 August 1981"),
    ("Tarikh lahir: 14 Ogos 1975", "14 Ogos 1975"),
    ("DOB 02-11-1990", "02-11-1990"),
])
def test_date_of_birth(text, dob):
    assert ("DATE_OF_BIRTH", dob) in types_of(text)


@pytest.mark.parametrize("text", [
    "Permohonan tuan bertarikh 12 Februari 2026 telah diterima.",  # ordinary letter date
    "Tarikh Lahir: 31/02/2005",                                      # not a real date
])
def test_date_not_flagged_as_birth(text):
    assert not any(f["type"] == "DATE_OF_BIRTH" for f in detect(text))
