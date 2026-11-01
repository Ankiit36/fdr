"""PDF summary report generation without external libraries."""

from apps.agent.synthetic import build_text_pdf


def render_summary_pdf(title: str, lines: list[str]) -> bytes:
    """Render a text-only PDF summary report reusing build_text_pdf.

    Args:
        title: The document title to place at the top of the report.
        lines: Sequential list of text lines for the report body.

    Returns:
        Valid PDF bytes starting with %PDF-1.4.
    """
    header_lines = [
        title,
        "=" * max(len(title), 40),
        "",
    ]
    full_lines = header_lines + list(lines)
    return build_text_pdf(full_lines, title=title)
