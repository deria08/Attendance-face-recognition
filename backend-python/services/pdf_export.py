from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib import colors
from reportlab.platypus import Image
from datetime import datetime
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, landscape
from config.database import (
    courses_collection,
    enrollments_collection,
    users_collection,
    attendance_collection,
    manual_attendance_collection
)

import os
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfgen import canvas

def add_page_number(canvas, doc):
    page_num = canvas.getPageNumber()
    canvas.drawRightString(580, 20, f"Halaman {page_num}")

def get_kaprodi(prodi):
    kaprodi_map = {
        "Informatika": "Zainal Abidin, S.ST., M.Kom.",
        "Teknik Informatika": "Zainal Abidin, S.ST., M.Kom.",
        "Elektro": "Leksono Mugi Aswanto, M.T.",
        "Teknik Elektro": "Leksono Mugi Aswanto, M.T."
    }
    return kaprodi_map.get(prodi, "________________________")

def generate_attendance_pdf(course_kode):

    course = courses_collection.find_one({"kode_mk": course_kode})
    if not course:
        return None

    pdf_path = f"exports/rekap_{course_kode}.pdf"

    # ========== AMBIL DATA DOSEN DENGAN GELAR ==========
    dosen = users_collection.find_one(
        {"_id": course["dosen_pengampu"]},
        {"name": 1, "gelar": 1}
    )

    if dosen:
        nama_dosen = dosen["name"]
        if dosen.get("gelar"):
            nama_dosen = f"{dosen['name']}, {dosen['gelar']}"
    else:
        nama_dosen = "-"

    nama_kaprodi = get_kaprodi(course["prodi"])

    os.makedirs("exports", exist_ok=True)

    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = []

    # ==================================
    # HEADER
    # ==================================
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(BASE_DIR, "assets", "logostt.png")

    kop_style = ParagraphStyle("KopStyle", parent=styles["Normal"], alignment=TA_CENTER)
    judul_tengah = ParagraphStyle("JudulTengah", parent=styles["Heading2"], alignment=TA_CENTER)
    center_style = ParagraphStyle("CenterStyle", parent=styles["Normal"], alignment=TA_CENTER)

    logo = Image(logo_path, width=60, height=60)
    kop = Table(
        [[
            logo,
            Paragraph(
                """
                <b>YAYASAN TUNAS HARAPAN BANGSA PATI</b><br/>
                <b>SEKOLAH TINGGI TEKNIK PATI</b><br/>
                Jl. Raya Pati-Trangkil Km. 4.5<br/>
                Telp (0295) 382470<br/>
                www.sttp.ac.id
                """,
                kop_style
            )
        ]],
        colWidths=[70, 420]
    )
    kop.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(kop)

    line = Table([[""]], colWidths=[520])
    line.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,-1), 2, colors.black)]))
    elements.append(line)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<b>DAFTAR HADIR MAHASISWA</b>", styles["Title"]))
    elements.append(Paragraph(f"<b>SEMESTER {course['jenis_semester'].upper()}</b>", judul_tengah))
    elements.append(Paragraph(f"<b>TAHUN AKADEMIK {course['tahun_ajaran']}</b>", judul_tengah))
    elements.append(Spacer(1, 15))

    # ==================================
    # INFO MATA KULIAH
    # ==================================
    info_table = Table([
    [f"Prodi                  : {course['prodi']}", f"                  Semester     : {course['semester']}"],
    [f"Mata Kuliah          : {course['nama_mk']}", f"                Jumlah SKS   : {course['sks']}"],
    [f"Dosen Pengampu : {nama_dosen}", ""]
    ], colWidths=[300, 200])
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # ==================================
    # AMBIL MAHASISWA
    # ==================================
    enrollments = list(enrollments_collection.find({"course": course["_id"]}))
    table_data = []
    header = ["No", "NIM", "Nama"] + [f"P{i}" for i in range(1, 17)]
    table_data.append(header)

    # ==================================
    # ISI TABEL
    # ==================================
    for idx, enroll in enumerate(enrollments, start=1):
        mahasiswa = users_collection.find_one({"_id": enroll["mahasiswa"]})
        if not mahasiswa:
            continue

        row = [
            idx,
            mahasiswa["nim_nidn"],
            Paragraph(mahasiswa["name"], styles["Normal"])
        ]

        attendance = [""] * 16

        logs = list(attendance_collection.find({
            "user_id": mahasiswa["_id"],
            "course_id": course["_id"]
        }))
        for log in logs:
            pertemuan = log.get("pertemuan")
            if not pertemuan:
                continue
            status = log.get("status")
            symbol = ""
            if status == "success":
                symbol = "✓"
            elif status == "late":
                symbol = "L"
            elif status == "izin":
                symbol = "I"
            elif status == "failed":
                symbol = "X"
            if 1 <= pertemuan <= 16:
                attendance[pertemuan - 1] = symbol

        manual_logs = list(manual_attendance_collection.find({
            "user_id": mahasiswa["_id"],
            "course_id": course["_id"]
        }))
        status_map = {"✔": "✓", "✓": "✓", "L": "L", "i": "I", "I": "I", "✖": "X", "X": "X"}
        for manual in manual_logs:
            pertemuan = manual.get("pertemuan")
            if not pertemuan:
                continue
            status = manual.get("status")
            if 1 <= pertemuan <= 16:
                attendance[pertemuan - 1] = status_map.get(status, status)

        row.extend(attendance)
        table_data.append(row)

    elements.append(Paragraph("<b>REKAP KEHADIRAN MAHASISWA</b>", kop_style))
    elements.append(Spacer(1, 10))

    # ==================================
    # TABLE ABSENSI
    # ==================================
    col_widths = [25, 75, 180] + [18] * 16
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 30))

    # ==================================
    # KETERANGAN SIMBOL (sejajar dengan tabel)
    # ==================================
    # Lebar total tabel absensi: 25 + 75 + 180 + 18*16 = 568
    total_table_width = sum(col_widths)

    keterangan_text = """
    <b>Keterangan:</b><br/>
    ✓ : Hadir<br/>
    L : Terlambat<br/>
    I : Izin<br/>
    X : Tidak Hadir
    """
    keterangan_paragraph = Paragraph(keterangan_text, styles["Normal"])

    # Bungkus dalam tabel dengan lebar yang sama agar rata kiri
    keterangan_table = Table([[keterangan_paragraph]], colWidths=[total_table_width])
    keterangan_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(keterangan_table)

    # ==================================
    # TANDA TANGAN
    # ==================================
    elements.append(Spacer(1, 20))

    ttd_data = [
        [
            Paragraph("Mengetahui,<br/>Ketua Program Studi", center_style),
            Paragraph(f"Pati, {datetime.now().strftime('%d-%m-%Y')}<br/>Dosen Pengampu", center_style)
        ],
        ["", ""],
        ["", ""],
        ["", ""],
        [
            Paragraph(f"({nama_kaprodi})", center_style),
            Paragraph(f"({nama_dosen})", center_style)
        ]
    ]

    ttd_table = Table(ttd_data, colWidths=[250, 250])
    ttd_table.hAlign = 'CENTER'
    ttd_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(Spacer(1, 30))
    elements.append(ttd_table)

    doc.build(elements)
    return pdf_path