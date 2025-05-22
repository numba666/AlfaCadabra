# Einfacher ReportLab Beispiel-Snippet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors

class ReportGenerator:
    def __init__(self, filename="pentest_report.pdf"):
        self.doc = SimpleDocTemplate(filename)
        self.styles = getSampleStyleSheet()
        self.story = []

    def add_heading(self, text, level=1):
        if level == 1:
            self.story.append(Paragraph(text, self.styles['h1']))
        elif level == 2:
            self.story.append(Paragraph(text, self.styles['h2']))
        self.story.append(Spacer(1, 0.2 * inch))

    def add_paragraph(self, text):
        self.story.append(Paragraph(text, self.styles['Normal']))
        self.story.append(Spacer(1, 0.1 * inch))

    def add_table(self, data, col_widths=None):
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 0.2 * inch))

    def generate_report(self):
        self.doc.build(self.story)
        print(f"Report generated: {self.doc.filename}")

# Beispielnutzung:
# report = ReportGenerator("Mein_WLAN_Pentest_Report.pdf")
# report.add_heading("WLAN Penetration Test Report", level=1)
# report.add_paragraph("Dieser Report fasst die Ergebnisse des WLAN-Penetrationstests zusammen.")
# report.add_heading("Gefundene Access Points", level=2)
#
# ap_data = [
#     ["BSSID", "ESSID", "Channel", "Privacy"],
#     ["AA:BB:CC:DD:EE:FF", "MeinHeimnetz", "6", "WPA2"],
#     ["11:22:33:44:55:66", "Cafe_WLAN", "1", "WPA"],
# ]
# report.add_table(ap_data)
#
# report.add_heading("Geknackte Passwörter", level=2)
# cracked_data = [
#     ["ESSID", "Passwort"],
#     ["MeinHeimnetz", "SicheresPasswort123"],
# ]
# report.add_table(cracked_data)
#
# report.generate_report()
