"""Build the fictional demo PDFs and their answer key. Run: .venv/Scripts/python -m demo.make_docs

Everything is made up. Agencies, companies and towns are fictional ("Sri Mawar", "Contoh").
MyKad numbers use place-of-birth codes 17-20, which JPN never issues, so they cannot belong to anyone.
E-mails use the reserved .example domain. Phone and bank numbers are random.

truth.json lists, per document, every personal value a reviewer would expect to be found.
Types in GAP_TYPES (health) are personal data the engine does not detect yet; they are
listed so the measurement shows the gap instead of hiding it.
"""
import json
from pathlib import Path

import pymupdf

OUT = Path(__file__).parent / "docs"
GAP_TYPES = {"HEALTH"}


class Page:
    def __init__(self, doc):
        self.page = doc.new_page(width=595, height=842)  # A4
        self.truth = []

    def v(self, kind, value):
        """Record a personal value in the answer key and return it for the text."""
        self.truth.append([kind, value])
        return value

    def text(self, x, y, w, s, size=10, bold=False, align=0, h=None):
        h = h or 812 - y  # default: box runs to the bottom margin; positions are set by y
        rc = self.page.insert_textbox(pymupdf.Rect(x, y, x + w, y + h), s, fontsize=size,
                                      fontname="hebo" if bold else "helv", align=align)
        assert rc >= 0, f"text does not fit its box: {s[:50]!r}"  # PyMuPDF silently drops overflowing text

    def table(self, x, y, widths, rows, row_h=20, size=9, header=True):
        for r, row in enumerate(rows):
            cx = x
            for w, cell in zip(widths, row):
                self.page.draw_rect(pymupdf.Rect(cx, y, cx + w, y + row_h), width=0.5)
                self.text(cx + 3, y + 3, w - 6, cell, size, bold=header and r == 0, h=row_h - 3)
                cx += w
            y += row_h
        return y


def letter(doc):
    """Official letter (Malay): recipient address block, long wrapped paragraph, signature block."""
    p = Page(doc)
    p.text(50, 40, 495, "JABATAN KEBAJIKAN DAERAH SRI MAWAR", 13, bold=True, align=1)
    p.text(50, 58, 495, "Aras 3, Kompleks Pentadbiran Sri Mawar, 43900 Sri Mawar, Selangor\n"
                            "Tel: 03-8700 1234   Faks: 03-8700 1299", 8, align=1)
    p.text(350, 100, 195, "Ruj. Kami: JKDSM.100-2/3/45\nTarikh: 3 Mac 2026", 9)
    p.text(50, 140, 300, f"Encik {p.v('PERSON', 'Mohd Faizal bin Osman')}\n"
                             f"{p.v('MY_ADDRESS', 'No. 7, Jalan Kenanga 2/1')},\n"
                             f"{p.v('MY_ADDRESS', 'Taman Bukit Indah')},\n"
                             f"{p.v('MY_ADDRESS', '43000 Kajang')}, Selangor.", 10)
    p.text(50, 220, 495, "Tuan,", 10)
    p.text(50, 240, 495, "PERMOHONAN BANTUAN AM BAGI WARGA EMAS", 10, bold=True)
    p.text(50, 262, 495,
           "Dengan hormatnya saya merujuk kepada permohonan tuan bertarikh 12 Februari 2026 bagi pihak ibu tuan, "
           f"Puan {p.v('PERSON', 'Rohani binti Abdul Hamid')} (No. KP: {p.v('MY_MYKAD', '520314-17-5126')}), "
           "yang kini menetap bersama tuan.\n\n"
           "2. Sukacita dimaklumkan bahawa permohonan tersebut telah diluluskan dengan bantuan bulanan sebanyak "
           "RM500.00 berkuat kuasa 1 April 2026. Bayaran akan dikreditkan terus ke akaun Bank Simpanan Contoh, "
           f"No. Akaun {p.v('MY_BANK_ACCOUNT', '1620 3344 5521 09')}, atas nama "
           f"{p.v('PERSON', 'Rohani binti Abdul Hamid')}.\n\n"
           "3. Sebarang pertanyaan boleh dikemukakan kepada pegawai kes, "
           f"Cik {p.v('PERSON', 'Nur Syafiqah Hamzah')}, di talian {p.v('MY_PHONE', '03-8912 4455')} atau "
           f"{p.v('MY_PHONE', '019-276 3301')}.\n\nSekian, terima kasih.", 10)
    p.text(50, 480, 300, "\"BERKHIDMAT UNTUK NEGARA\"\n\nSaya yang menjalankan amanah,\n\n\n"
                              f"({p.v('PERSON', 'HAJAH ZALEHA BINTI MOHD NOOR')})\nPengarah\n"
                              "Jabatan Kebajikan Daerah Sri Mawar", 10)
    p.text(50, 600, 400, f"s.k.  Puan {p.v('PERSON', 'Rohani binti Abdul Hamid')}", 9)
    return p


def form(doc):
    """Application form (Malay, ALL CAPS values): label/value table and a side-by-side parents table."""
    p = Page(doc)
    p.text(50, 40, 495, "YAYASAN PENDIDIKAN CONTOH\nBORANG PERMOHONAN BIASISWA 2026", 12, bold=True, align=1)
    p.text(50, 90, 495, "BAHAGIAN A: MAKLUMAT PEMOHON", 10, bold=True)
    y = p.table(50, 108, [150, 345], row_h=32, rows=[
        ["Perkara", "Maklumat"],
        ["Nama Penuh", p.v("PERSON", "NURUL AIN BINTI ZAKARIA")],
        ["No. MyKad", p.v("MY_MYKAD", "050823-18-0442")],
        ["Tarikh Lahir", p.v("DATE_OF_BIRTH", "23/08/2005")],
        ["Alamat Tetap", f"{p.v('MY_ADDRESS', 'NO. 21, LORONG MELATI 4')}, {p.v('MY_ADDRESS', 'TAMAN DESA PERMAI')}, "
                         f"{p.v('MY_ADDRESS', '08000 SUNGAI PETANI')}, KEDAH"],
        ["No. Telefon Bimbit", p.v("MY_PHONE", "017-552 8190")],
        ["E-mel", p.v("EMAIL_ADDRESS", "nurulain.z@contoh.example")],
    ])
    p.text(50, y + 20, 495, "BAHAGIAN B: MAKLUMAT IBU BAPA / PENJAGA", 10, bold=True)
    y = p.table(50, y + 38, [125, 185, 185], [
        ["Perkara", "Bapa", "Ibu"],
        ["Nama", p.v("PERSON", "ZAKARIA BIN ISMAIL"), p.v("PERSON", "ROSMAWATI BINTI YUSOF")],
        ["No. MyKad", p.v("MY_MYKAD", "720415-19-5013"), p.v("MY_MYKAD", "750930-19-5228")],
        ["Pekerjaan", "PEMANDU LORI", "SURI RUMAH"],
        ["Pendapatan Bulanan", "RM 2,800", "-"],
        ["No. Telefon", p.v("MY_PHONE", "013-468 2271"), p.v("MY_PHONE", "012-907 5534")],
    ])
    p.text(50, y + 25, 495, "Saya mengaku bahawa maklumat yang diberikan adalah benar.\n\n"
                                f"Tandatangan: ______________     Nama: {p.v('PERSON', 'NURUL AIN BINTI ZAKARIA')}", 9)
    return p


def claim(doc):
    """Insurance claim (English): two columns, medical details, payout account, declaration paragraph."""
    p = Page(doc)
    p.text(50, 40, 495, "CONTOH TAKAFUL BERHAD\nHOSPITALISATION CLAIM FORM", 12, bold=True, align=1)
    left = (f"PART A: POLICYHOLDER\n\nName: {p.v('PERSON', 'Lim Siew Peng')}\n"
            f"NRIC: {p.v('MY_MYKAD', '810607-20-5584')}\nPolicy No.: CT-HS-2291045\n"
            f"Mobile: {p.v('MY_PHONE', '+60 12-338 4410')}\nEmail: {p.v('EMAIL_ADDRESS', 'siewpeng.lim@contoh.example')}\n"
            f"Address: {p.v('MY_ADDRESS', '18, Jalan SS 2/24')}, {p.v('MY_ADDRESS', '47300 Petaling Jaya')}, Selangor\n\n"
            f"PART B: PAYOUT\n\nBank: Contoh Bank Berhad\nAccount No.: {p.v('MY_BANK_ACCOUNT', '5140-2288-3391')}\n"
            f"Account holder: {p.v('PERSON', 'Lim Siew Peng')}")
    right = (f"PART C: INSURED PERSON\n\nName: {p.v('PERSON', 'Lim Jia Wen')}\nRelationship: Daughter\n"
             f"NRIC: {p.v('MY_MYKAD', '100214-20-0786')}\n"
             f"Passport No.: {p.v('MY_PASSPORT', 'A38291047')}\n\n"
             f"PART D: MEDICAL DETAILS\n\nHospital: Hospital Pakar Contoh, Petaling Jaya\n"
             f"Admitted: 2 May 2026   Discharged: 6 May 2026\n"
             f"Diagnosis: {p.v('HEALTH', 'Dengue fever with warning signs')}\n"
             f"Treating doctor: Dr. {p.v('PERSON', 'Ganesh Kumar a/l Raman')}\n"
             f"Doctor's contact: {p.v('MY_PHONE', '03-7788 2100')}")
    p.text(50, 95, 240, left, 9)
    p.text(305, 95, 240, right, 9)
    p.text(50, 440, 495,
           "PART E: DECLARATION\n\n"
           f"I, {p.v('PERSON', 'LIM SIEW PENG')}, holder of NRIC No. {p.v('MY_MYKAD', '810607-20-5584')}, declare that "
           "the information given in this form is true and complete, and I authorise Contoh Takaful Berhad to "
           f"obtain medical records relating to {p.v('PERSON', 'Lim Jia Wen')} from any hospital or doctor.", 9)
    return p


def minutes(doc):
    """Meeting minutes (Malay): attendee list with titles, action items, many institution names."""
    p = Page(doc)
    p.text(50, 40, 495, "MINIT MESYUARAT JAWATANKUASA PENGURUSAN\nMAJLIS DAERAH SRI MAWAR BIL. 3/2026", 12,
           bold=True, align=1)
    p.text(50, 90, 495, "Tarikh: 15 April 2026 (Rabu)\nMasa: 10.00 pagi\n"
                            "Tempat: Bilik Mesyuarat Utama, Aras 5, Menara Majlis Daerah Sri Mawar", 9)
    p.text(50, 140, 495,
           "HADIR\n"
           f"1. Dato' Haji {p.v('PERSON', 'Kamaruddin bin Yaacob')} (Pengerusi)\n"
           f"2. Tan Sri Dr. {p.v('PERSON', 'Wong Kok Leong')}\n"
           f"3. Puan {p.v('PERSON', 'Saraswathy a/p Ramasamy')}\n"
           f"4. Encik {p.v('PERSON', 'Lee Chee Keong')}\n"
           f"5. Ir. {p.v('PERSON', 'Ahmad Syafiq Rosli')}\n\n"
           f"TURUT HADIR\nCik {p.v('PERSON', 'Farah Hanis Azmi')} (Urus Setia)\n\n"
           f"TIDAK HADIR DENGAN MAAF\nDatuk Seri {p.v('PERSON', 'Jamaluddin Harun')}", 9)
    p.text(50, 290, 495,
           "1. PERUTUSAN PENGERUSI\n"
           "1.1 Pengerusi mengalu-alukan kehadiran ahli mesyuarat.\n\n"
           "2. LAPORAN AUDIT DALAM\n"
           "2.1 Mesyuarat mengambil maklum laporan Unit Audit Dalam yang dibentangkan oleh "
           f"Encik {p.v('PERSON', 'Lee')}.\n"
           "2.2 Ahli mesyuarat bersetuju kontrak penyelenggaraan Syarikat Maju Jaya Sdn Bhd dilanjutkan "
           "selama 12 bulan.\nTindakan: Puan Saraswathy / Bahagian Kewangan\n\n"
           "3. ADUAN AWAM\n"
           f"3.1 Aduan daripada orang awam, Encik {p.v('PERSON', 'Tan Boon Huat')} (tel: {p.v('MY_PHONE', '016-772 3108')}), "
           f"berhubung longkang tersumbat di {p.v('MY_ADDRESS', 'Jalan Cempaka 5')}, "
           f"{p.v('MY_ADDRESS', 'Taman Seri Murni')} telah diambil tindakan oleh Jabatan Kejuruteraan.\n\n"
           "Mesyuarat ditangguhkan pada jam 12.30 tengah hari.", 9)
    p.text(50, 570, 495, f"Disediakan oleh: {p.v('PERSON', 'Farah Hanis Azmi')}\n"
                             f"Disahkan oleh: Dato' Haji {p.v('PERSON', 'Kamaruddin bin Yaacob')}", 9)
    p.truth.append(["PERSON", "Saraswathy"])  # "Tindakan: Puan Saraswathy" (first name only)
    return p


def staff_list(doc):
    """Test-data table for a vendor: narrow name column, so long names wrap inside the cell."""
    p = Page(doc)
    p.text(50, 40, 495, "SENARAI KAKITANGAN UNTUK UJIAN SISTEM HRMIS\n(Lampiran A)", 12, bold=True, align=1)
    people = [
        ("Muhammad Aiman Hakimi bin Zulkarnain", "910304-17-5571", "012-664 2093", "aiman.hakimi"),
        ("Chan Mei Yee", "880719-18-5240", "016-338 7712", "meiyee.chan"),
        ("Kavitha Selvarajah", "930126-19-5502", "011-2087 4415", "kavitha.s"),
        ("Douglas anak Jimbun", "850911-20-5917", "019-815 0347", "douglas.j"),
        ("Nurfarhana Atikah binti Mohd Ridzuan", "960502-17-5866", "013-772 9054", "nurfarhana"),
        ("Ooi Teck Seng", "790830-18-5115", "017-403 2268", "teckseng.ooi"),
        ("Juliet Masuyan", "900217-19-5732", "014-856 3390", "juliet.m"),
        ("Harvinder Kaur a/p Gurdev Singh", "870625-20-5408", "012-290 6631", "harvinder.k"),
    ]
    rows = [["Bil", "Nama", "No. KP", "Telefon", "E-mel"]]
    for i, (name, ic, tel, mail) in enumerate(people, 1):
        rows.append([str(i), p.v("PERSON", name), p.v("MY_MYKAD", ic), p.v("MY_PHONE", tel),
                     p.v("EMAIL_ADDRESS", f"{mail}@contoh.example")])
    p.table(50, 90, [30, 120, 95, 85, 165], rows, row_h=32)
    return p


DOCS = {"surat_kelulusan.pdf": letter, "borang_biasiswa.pdf": form, "tuntutan_takaful.pdf": claim,
        "minit_mesyuarat.pdf": minutes, "senarai_kakitangan.pdf": staff_list}


def main():
    OUT.mkdir(exist_ok=True)
    truth = {}
    for name, build in DOCS.items():
        doc = pymupdf.open()
        page = build(doc)
        if name == "surat_kelulusan.pdf":  # hidden personal data for the day 4 metadata-stripping test
            doc.set_metadata({"author": "Hajah Zaleha binti Mohd Noor", "title": "Kelulusan bantuan - Rohani binti Abdul Hamid"})
        doc.save(OUT / name)
        truth[name] = sorted({tuple(t) for t in page.truth})
    (OUT / "truth.json").write_text(json.dumps(truth, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(DOCS)} PDFs and truth.json to {OUT}")


if __name__ == "__main__":
    main()
