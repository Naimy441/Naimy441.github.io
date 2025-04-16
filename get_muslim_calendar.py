import requests
import re
from datetime import datetime
from xml.sax.saxutils import escape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Table
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

# --- Download ICS feed ---
# 28807 - CML
# 28808 - MSA
ics_url = "https://duke.campusgroups.com/ics?group_ids=28807%2C28808&school=duke"
ics_text = requests.get(ics_url).text
events_raw = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics_text, re.DOTALL)

# --- Helper Functions ---
def find_field(field, block):
    match = re.search(rf"{field}(?:;[^:]*)*:(.*)", block)
    return match.group(1).strip() if match else ""

def clean_description(raw_desc):
    raw_desc = re.sub(r'---.*', '', raw_desc, flags=re.DOTALL)
    desc = raw_desc.replace('\\n', '\n')
    desc = re.sub(r'\s*\.\s*\.\s*\.\s*', '\n\n', desc)
    desc = re.sub(r'\s*\.\s*\.\s*', '\n\n', desc)
    desc = re.sub(r'\n+', '\n', desc)
    return desc.strip()

def parse_event_block(block):
    return {
        "summary": find_field("SUMMARY", block),
        "description": find_field("DESCRIPTION", block),
        "location": find_field("LOCATION", block),
        "url": find_field("URL", block),
        "start": find_field("DTSTART", block),
        "end": find_field("DTEND", block),
    }

def format_datetime(dt_str):
    try:
        dt = datetime.strptime(dt_str, "%Y%m%dT%H%M%SZ")
        return dt.strftime("%A, %B %d, %Y %I:%M %p")
    except:
        return dt_str

def parse_datetime(dt_str):
    try:
        return datetime.strptime(dt_str, "%Y%m%dT%H%M%SZ")
    except:
        return datetime.max

# --- Parse and Sort Events ---
events = [parse_event_block(b) for b in events_raw]
events.sort(key=lambda e: parse_datetime(e["start"]))

# --- Duke Blue ---
DUKE_BLUE = colors.HexColor("#012169")

# --- Styles ---
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Header', fontSize=20, leading=24, textColor=DUKE_BLUE, spaceAfter=20))
styles.add(ParagraphStyle(name='EventTitle', fontSize=14, leading=16, spaceBefore=12, spaceAfter=6, textColor=DUKE_BLUE, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name='EventInfo', fontSize=11, leading=14))
styles.add(ParagraphStyle(name='Description', fontSize=10, leading=13, spaceAfter=10))

# --- Document ---  
doc = SimpleDocTemplate("muslim_calendar.pdf", pagesize=letter,
                        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
story = []

story.append(Paragraph("Upcoming Duke Muslim Life Events", styles['Header']))

for event in events:
    story.append(Paragraph(event["summary"], styles['EventTitle']))

    start = format_datetime(event["start"])
    end = format_datetime(event["end"])
    location = event["location"]

    # RSVP
    rsvp_match = re.search(r'https?:\/\/duke\.campusgroups\.com\/rsvp\?id=\d+', event["description"])
    rsvp_url = rsvp_match.group(0) if rsvp_match else event["url"]

    # Cleaned description
    desc_clean = clean_description(event["description"])
    desc_html = escape(desc_clean).replace('\n', '<br/>')

    # Event info table
    event_info_data = [
        [Paragraph("<b>When:</b>", styles["EventInfo"]), Paragraph(f"{start} to {end}", styles["EventInfo"])],
        [Paragraph("<b>Where:</b>", styles["EventInfo"]), Paragraph(location, styles["EventInfo"])],
    ]
    if rsvp_url:
        event_info_data.append([Paragraph("<b>RSVP:</b>", styles["EventInfo"]), Paragraph(rsvp_url, styles["EventInfo"])])

    table = Table(event_info_data, colWidths=[60, 360])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("BOX", (0, 0), (-1, -1), 0.25, DUKE_BLUE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)

    # Description
    if desc_html:
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<br/>{desc_html}", styles['Description']))

    # Divider
    story.append(Spacer(1, 8))
    story.append(Table([[""]], colWidths=[450], style=[
        ('LINEABOVE', (0, 0), (-1, -1), 0.4, DUKE_BLUE),
    ]))
    story.append(Spacer(1, 12))

# --- Save ---
doc.build(story)