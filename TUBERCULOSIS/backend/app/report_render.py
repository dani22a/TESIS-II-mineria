"""Render the shared summary dict to PDF / DOCX / XLSX."""
import io

from docx import Document
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

DISCLAIMER = "Decision-support research prototype. Not a diagnostic device."


def _rows(s: dict, kind: str) -> list[tuple[str, list[tuple[str, object]]]]:
    o = s["operational"]
    ps = o["processing_seconds"]
    sections = [
        ("Totals", [("Total cases", o["total_cases"]), ("Technical failures", o["technical_failures"]),
                    ("Not evaluable", o["not_evaluable"])]),
        ("Cases by status", list(o["cases_by_status"].items())),
        ("Results by outcome", list(o["results_by_outcome"].items()) or [("(none)", 0)]),
    ]
    if kind == "operational":
        sections += [
            ("Processing time (s)", [("n", ps["n"]), ("mean", ps["mean"]), ("median", ps["median"]),
                                     ("max", ps["max"])]),
            ("Inferences by model version", list(o["inferences_by_model_version"].items()) or [("(none)", 0)]),
        ]
    else:
        rv = o["reviews"]
        sections += [("Reviewer activity", [("Reviews", rv["total"]), ("Agreed with model", rv["agreed"]),
                                            ("Disagreed", rv["disagreed"])])]
    sc = s["scientific"]
    sections.append(("Scientific metrics", [("available", sc["available"]), ("reason", sc["reason"])]))
    return sections


def _head(s: dict, kind: str) -> tuple[str, list[str]]:
    lines = [f"Generated: {s['generated_at']}", f"Filters: {s['filters'] or 'none'}", DISCLAIMER]
    if s["is_demo"]:
        lines.insert(0, s["demo_notice"])
    return f"TB screening - {kind} report", lines


def to_pdf(s: dict, kind: str) -> bytes:
    buf, st = io.BytesIO(), getSampleStyleSheet()
    title, lines = _head(s, kind)
    story = [Paragraph(title, st["Title"])]
    story += [Paragraph(line, st["Normal"]) for line in lines] + [Spacer(1, 12)]
    for name, rows in _rows(s, kind):
        story.append(Paragraph(name, st["Heading2"]))
        story.append(Table([[str(a), Paragraph(str(b), st["Normal"])] for a, b in rows], colWidths=[150, 330]))
    SimpleDocTemplate(buf, pagesize=A4).build(story)
    return buf.getvalue()


def to_docx(s: dict, kind: str) -> bytes:
    d, (title, lines) = Document(), _head(s, kind)
    d.add_heading(title, 0)
    for line in lines:
        d.add_paragraph(line)
    for name, rows in _rows(s, kind):
        d.add_heading(name, 2)
        t = d.add_table(rows=0, cols=2)
        for a, b in rows:
            cells = t.add_row().cells
            cells[0].text, cells[1].text = str(a), str(b)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def to_xlsx(s: dict, kind: str) -> bytes:
    wb, (title, lines) = Workbook(), _head(s, kind)
    ws = wb.active
    ws.title = "Report"
    ws.append([title])
    for line in lines:
        ws.append([line])
    for name, rows in _rows(s, kind):
        ws.append([])
        ws.append([name])
        for a, b in rows:
            ws.append([str(a), b if isinstance(b, (int, float, str)) or b is None else str(b)])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


RENDERERS = {
    "pdf": (to_pdf, "application/pdf"),
    "docx": (to_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "xlsx": (to_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
}
