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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

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

    # ========== DEFINISIKAN LEBAR KOLOM TABEL DI AWAL ==========
    col_widths = [
        35,   # No
        85,   # NIM
        230,  # Nama Mahasiswa
    ] + [26] * 16   # P1 - P16
    table_width = sum(col_widths)

    # ========== BUAT STYLE ==========
    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=11,
        leading=15
    )
    colon_style = ParagraphStyle(
        "Colon",
        parent=styles["Normal"],
        fontName="Times-Bold",
        fontSize=11,
        alignment=1
    )
    rekap_style = ParagraphStyle(
        "Rekap",
        parent=styles["Heading2"],
        alignment=TA_CENTER,
        fontName="Times-Bold",
        fontSize=12,
        leading=14,
        spaceAfter=6,
    )
    kop_style = ParagraphStyle(
        "KopStyle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        leading=14,
        spaceAfter=0,
        spaceBefore=0
    )
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Times-Bold",
        fontSize=14,
        leading=16,
        spaceAfter=2
    )
    semester_style = ParagraphStyle(
        "SemesterStyle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Times-Bold",
        fontSize=12,
        leading=13,
        spaceAfter=1
    )
    tahun_style = ParagraphStyle(
        "TahunStyle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontName="Times-Bold",
        fontSize=12,
        leading=13,
    )
    judul_tengah = ParagraphStyle(
        "JudulTengah",
        parent=styles["Heading2"],
        alignment=TA_CENTER
    )
    center_style = ParagraphStyle(
        "CenterStyle",
        parent=styles["Normal"],
        alignment=TA_CENTER
    )

    elements = []

    # ==================================
    # HEADER (KOP SURAT)
    # ==================================
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(BASE_DIR, "assets", "logostt.png")
    logo = Image(logo_path, width=70, height=70)

    kop_text = Paragraph("""
    <font size="14"><b>YAYASAN TUNAS HARAPAN BANGSA PATI</b></font><br/>
    <font size="18"><b>S T T P</b></font><br/>
    <font size="14"><b>SEKOLAH TINGGI TEKNIK PATI</b></font><br/>
    <font size="9">
    Jl. Raya Pati-Trangkil Km.4.5 &nbsp;&nbsp; Telp (0295)382470 &nbsp;&nbsp; Fax (0295)382234 &nbsp;&nbsp;
    </font><br/>
    <font size="9">
    www.sttp.ac.id &nbsp;&nbsp;&nbsp; email : sttpati@yahoo.com
    </font>
    """, kop_style)

    kop = Table(
        [[logo, kop_text]],
        colWidths=[70, 650]
    )
    kop.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(kop)

    blue_line = Table([[""]], colWidths=[760], rowHeights=[2])
    blue_line.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#1E4F9A"))
    ]))
    elements.append(blue_line)

    black_line = Table([[""]], colWidths=[760], rowHeights=[0.8])
    black_line.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.black)
    ]))
    elements.append(black_line)

    elements.append(Spacer(1, 8))

    # ==================================
    # JUDUL & PERIODE
    # ==================================
    elements.append(Paragraph("<b>DAFTAR HADIR MAHASISWA</b>", title_style))
    elements.append(Paragraph(f"<b>SEMESTER {course['jenis_semester'].upper()}</b>", semester_style))
    elements.append(Paragraph(f"<b>TAHUN AKADEMIK {course['tahun_ajaran']}</b>", tahun_style))
    elements.append(Spacer(1, 4))

    # ==================================
    # INFO MATA KULIAH
    # ==================================
    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontName="Times-Bold",
        fontSize=11,
        leading=15,
    )
    value_style = ParagraphStyle(
        "ValueStyle",
        parent=styles["Normal"],
        fontName="Times-Roman",
        fontSize=11,
        leading=15,
    )
    label_style_right = ParagraphStyle(
        "LabelStyleRight",
        parent=label_style,
        # leftIndent=20
    )
    value_style_right = ParagraphStyle(
        "ValueStyleRight",
        parent=value_style,
        # leftIndent=20
    )

    # ===== PERBAIKAN LEBAR KOLOM =====
    left_table = Table(
        [
            [
                Paragraph("Program Studi", label_style),
                Paragraph(":", label_style),
                Paragraph(course["prodi"], value_style),
            ],
            [
                Paragraph("Mata Kuliah", label_style),
                Paragraph(":", label_style),
                Paragraph(course["nama_mk"], value_style),
            ],
            [
                Paragraph("Dosen Pengampu", label_style),
                Paragraph(":", label_style),
                Paragraph(nama_dosen, value_style),
            ],
        ],
        colWidths=[85, 8, 287],  # diperlebar agar dosen pengampu tidak terpotong
    )

    left_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))

    right_table = Table(
        [
            [
                Paragraph("Semester", label_style_right),
                Paragraph(":", label_style_right),
                Paragraph(str(course["semester"]), value_style_right),
            ],
            [
                Paragraph("Jumlah SKS", label_style_right),
                Paragraph(":", label_style_right),
                Paragraph(str(course["sks"]), value_style_right),
            ],
            ["", "", ""],
        ],
        colWidths=[90, 8, 35],
    )

    right_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (0,-1), 18),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    right_table.hAlign = "RIGHT"

    info_table = Table(
        [[left_table, right_table]],
        colWidths=[375, table_width - 375]  # total = table_width
    )

    info_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('RIGHTPADDING', (1,0), (1,0), -8),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 6))

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
        # ===== PERBAIKAN MAPPING STATUS =====
        status_map = {
            "✔": "✓",
            "✓": "✓",
            "success": "✓",
            "L": "L",
            "late": "L",
            "i": "I",
            "I": "I",
            "izin": "I",
            "✖": "X",
            "X": "X",
            "failed": "X",
        }
        for manual in manual_logs:
            pertemuan = manual.get("pertemuan")
            if not pertemuan:
                continue
            raw_status = manual.get("status")
            if raw_status in status_map:
                symbol = status_map[raw_status]
            else:
                symbol = raw_status  # fallback
            if 1 <= pertemuan <= 16:
                attendance[pertemuan - 1] = symbol

        row.extend(attendance)
        table_data.append(row)

    elements.append(Paragraph("<b>REKAP KEHADIRAN MAHASISWA</b>", rekap_style))
    elements.append(Spacer(1, 10))

    # ==================================
    # TABLE ABSENSI
    # ==================================
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.7, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F3F3F3")),
        ('FONTNAME', (0,0), (-1,0), 'Times-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Times-Roman'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (2,1), (2,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('BOTTOMPADDING', (0,1), (-1,-1), 5),
        ('TOPPADDING', (0,1), (-1,-1), 5),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 30))

    # ==================================
    # KETERANGAN SIMBOL
    # ==================================
    keterangan_text = """
    <b>Keterangan:</b><br/>
    ✓ : Hadir<br/>
    L : Terlambat<br/>
    I : Izin<br/>
    X : Tidak Hadir
    """
    keterangan_table = Table(
        [[Paragraph(keterangan_text, info_style)]],
        colWidths=[table_width]
    )
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

    ttd_table = Table(
        ttd_data,
        colWidths=[table_width/2, table_width/2]
    )
    ttd_table.hAlign = 'CENTER'
    ttd_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(Spacer(1, 30))
    elements.append(ttd_table)

    doc.build(elements)
    return pdf_path