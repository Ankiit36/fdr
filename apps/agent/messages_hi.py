"""Hindi message templates and localization renderer for agent findings."""

from __future__ import annotations

from apps.agent.rules import MESSAGE_TEMPLATES

HINDI_MESSAGE_TEMPLATES: dict[str, str] = {
    "R01": "राशि बेमेल: प्रस्तुत={submitted}, निष्कर्षित={extracted}, स्निपेट={snippet}",
    "R02": "संदर्भ बेमेल: प्रस्तुत={submitted}, निष्कर्षित={extracted}, स्निपेट={snippet}",
    "R03": "तारीख बेमेल: प्रस्तुत={submitted}, निष्कर्षित={extracted}, स्निपेट={snippet}",
    "R04": "बैंक बेमेल: प्रस्तुत={submitted}, निष्कर्षित={extracted}, स्निपेट={snippet}",
    "R05": "दस्तावेज़ में पाठ परत (text layer) नहीं है: {snippet}",
    "R06": "जमा {reference_number} के लिए दस्तावेज़ गायब है",
    "R07": "परिपक्वता शीघ्र: परिपक्वता_तिथि={maturity_date}, शेष_दिन={days_left}",
    "R08": "परिपक्व, लेकिन नवीनीकृत नहीं: परिपक्वता_तिथि={maturity_date}, स्थिति={status}",
    "R09": "संभावित डुप्लिकेट: संदर्भ={reference_number}, बैंक={bank_name}, परस्पर_विरोधी_जमा={conflicting_pk}",
    "R10": "नवीनीकरण देय: परिपक्वता_तिथि={maturity_date}, स्थिति=EXPIRING, शेष_दिन={days_left}",
    "R11": "संभावित डुप्लिकेट: संदर्भ={reference_number}, बैंक={bank_name}, परस्पर_विरोधी_जमा={conflicting_pk}",
    "R11_CROSS_INSTITUTION_DUPLICATE": "संभावित डुप्लिकेट: संदर्भ={reference_number}, बैंक={bank_name}, परस्पर_विरोधी_जमा={conflicting_pk}",
    "F01": "PDF मेटाडेटा में संपादक या निर्माता कीवर्ड मिला: {snippet} (मेटाडेटा जांच, कोई प्रमाण नहीं)",
    "F02": "संशोधन तिथि निर्माण तिथि से 1 दिन से अधिक भिन्न है (मेटाडेटा जांच, कोई प्रमाण नहीं)",
    "F03": "एकाधिक %%EOF मार्कर मिले, जो वृद्धिशील अद्यतन/जोड़ दर्शाते हैं (मेटाडेटा जांच, कोई प्रमाण नहीं)",
    "F04": "PDF में कोई Producer या CreationDate मेटाडेटा नहीं मिला (मेटाडेटा जांच, कोई प्रमाण नहीं)",
}


def render_finding_message(finding, lang: str = "en") -> str:
    """Format finding message in requested language using stored params.

    Falls back safely to finding.message if params are missing, formatting fails,
    or for legacy rows.
    """
    if finding is None:
        return ""

    params = getattr(finding, "params", None)
    rule_code = getattr(finding, "rule_code", "")
    orig_message = getattr(finding, "message", "")

    # For empty params (e.g. legacy rows), return finding.message unchanged
    if not params or not isinstance(params, dict):
        return orig_message

    try:
        if lang == "hi" and rule_code in HINDI_MESSAGE_TEMPLATES:
            return HINDI_MESSAGE_TEMPLATES[rule_code].format(**params)
        elif lang == "en" and rule_code in MESSAGE_TEMPLATES:
            return MESSAGE_TEMPLATES[rule_code].format(**params)
    except Exception:
        return orig_message

    return orig_message
