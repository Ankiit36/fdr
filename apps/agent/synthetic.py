"""Synthetic PDF generator using only standard library text-only PDF generation."""

from __future__ import annotations


def build_text_pdf(text_lines: list[str] | str, title: str | None = None) -> bytes:
    """Build minimal, valid, multi-page text-only PDF bytes using Helvetica font.

    Limits each page to at most 45 lines. If a title is provided and there are
    subsequent pages, each subsequent page begins with "{title} (continued)".
    Does not depend on reportlab, Pillow, or any non-standard library.
    """
    if isinstance(text_lines, str):
        text_lines = [text_lines]

    all_lines = list(text_lines)
    max_lines_per_page = 45

    pages_lines: list[list[str]] = []
    if not all_lines:
        pages_lines = [[title or "Summary Report"]]
    else:
        for i in range(0, len(all_lines), max_lines_per_page):
            chunk = all_lines[i : i + max_lines_per_page]
            if i > 0 and title:
                chunk = [f"{title} (continued)"] + chunk
            pages_lines.append(chunk)

    num_pages = len(pages_lines)
    catalog_obj_id = 1
    pages_obj_id = 2
    font_obj_id = 3

    page_obj_ids = [4 + 2 * i for i in range(num_pages)]
    stream_obj_ids = [5 + 2 * i for i in range(num_pages)]

    objects: dict[int, bytes] = {}
    objects[catalog_obj_id] = (
        f"{catalog_obj_id} 0 obj\n<< /Type /Catalog /Pages {pages_obj_id} 0 R >>\nendobj\n"
    ).encode("latin-1")

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[pages_obj_id] = (
        f"{pages_obj_id} 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>\nendobj\n"
    ).encode("latin-1")

    objects[font_obj_id] = (
        f"{font_obj_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    ).encode("latin-1")

    for i in range(num_pages):
        pid = page_obj_ids[i]
        sid = stream_obj_ids[i]
        objects[pid] = (
            f"{pid} 0 obj\n<< /Type /Page /Parent {pages_obj_id} 0 R "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
            f"/MediaBox [0 0 612 792] /Contents {sid} 0 R >>\nendobj\n"
        ).encode("latin-1")

        lines = pages_lines[i]
        content_parts = ["BT", "/F1 10 Tf", "14 TL", "50 740 Td"]
        for j, line in enumerate(lines):
            safe_line = (
                str(line)
                .replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
            )
            if j == 0:
                content_parts.append(f"({safe_line}) Tj")
            else:
                content_parts.append(f"T* ({safe_line}) Tj")
        content_parts.append("ET\n")
        stream_bytes = "\n".join(content_parts).encode("latin-1")

        objects[sid] = (
            f"{sid} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1")
            + stream_bytes
            + b"endstream\nendobj\n"
        )

    total_objs = 3 + 2 * num_pages
    header = b"%PDF-1.4\n"
    offset = len(header)
    offsets: dict[int, int] = {}

    body = b""
    for oid in range(1, total_objs + 1):
        offsets[oid] = offset
        obj_data = objects[oid]
        body += obj_data
        offset += len(obj_data)

    xref_lines = [b"xref", f"0 {total_objs + 1}".encode("latin-1"), b"0000000000 65535 f "]
    for oid in range(1, total_objs + 1):
        xref_lines.append(f"{offsets[oid]:010d} 00000 n ".encode("latin-1"))
    xref_section = b"\n".join(xref_lines) + b"\n"

    trailer = (
        f"trailer\n<< /Size {total_objs + 1} /Root {catalog_obj_id} 0 R >>\n"
        f"startxref\n{offset}\n%%EOF\n"
    ).encode("latin-1")

    return header + body + xref_section + trailer
