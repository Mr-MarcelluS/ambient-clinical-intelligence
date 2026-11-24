import io
import json
from xml.sax.saxutils import escape
from docx import Document
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

DISCLAIMER = 'This is an academic research prototype for clinical documentation assistance. It is not a medical diagnostic system and must not be used for real clinical decision-making or patient care.'


def export(record, kind):
    if not record['approved']:
        raise ValueError('Human approval is required before export.')
    if kind == 'json':
        return json.dumps(record, indent=2).encode(), 'application/json'
    buffer = io.BytesIO()
    sections = record['analysis']['note']
    if kind == 'docx':
        doc = Document()
        doc.add_heading('ACI | Fictional consultation', 0)
        doc.add_paragraph(DISCLAIMER)
        doc.add_paragraph(f"Version {record['version']} — human-reviewed prototype note")
        for name, content in sections.items():
            doc.add_heading(name, 1)
            doc.add_paragraph(content)
        doc.save(buffer)
        mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif kind == 'pdf':
        styles = getSampleStyleSheet()
        flow = [Paragraph('ACI | Fictional consultation', styles['Title']), Paragraph(DISCLAIMER, styles['BodyText'])]
        for name, content in sections.items():
            flow += [Spacer(1, 12), Paragraph(name, styles['Heading2']),
                     Paragraph(escape(content).replace('\n', '<br/>'), styles['BodyText'])]
        SimpleDocTemplate(buffer).build(flow)
        mime = 'application/pdf'
    else:
        raise ValueError('Unsupported export format.')
    return buffer.getvalue(), mime
