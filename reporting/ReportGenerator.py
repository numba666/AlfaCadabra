from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter

class ReportGenerator:
    def __init__(self, output_filename="pentest_report.pdf"):
        self.output_filename = output_filename
        self.doc = SimpleDocTemplate(output_filename, pagesize=letter)
        self.styles = getSampleStyleSheet()
        self.story = []

    def add_heading(self, text, level=1):
        """Adds a heading to the report."""
        if level == 1:
            self.story.append(Paragraph(text, self.styles['h1']))
        elif level == 2:
            self.story.append(Paragraph(text, self.styles['h2']))
        elif level == 3:
            self.story.append(Paragraph(text, self.styles['h3']))
        self.story.append(Spacer(1, 0.2 * inch))

    def add_paragraph(self, text):
        """Adds a paragraph of text to the report."""
        self.story.append(Paragraph(text, self.styles['Normal']))
        self.story.append(Spacer(1, 0.1 * inch))

    def add_code_block(self, code_text):
        """Adds a block of code/log output to the report."""
        # Using preformatted style for code
        self.story.append(Paragraph(code_text, self.styles['Code']))
        self.story.append(Spacer(1, 0.1 * inch))

    def add_table(self, data: list[list], title: str = None, col_widths=None):
        """
        Adds a table to the report.
        Args:
            data (list[list]): List of lists, where the first list is the header.
            title (str, optional): An optional title for the table.
            col_widths (list, optional): List of column widths (e.g., [1*inch, 2*inch]).
        """
        if title:
            self.add_heading(title, level=3) # Use a sub-heading for table title

        if not data:
            self.add_paragraph("No data available for this section.")
            return

        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')), # Green header
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'), # Align content to top
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 0.2 * inch))

    def generate_report(self,
                        general_info: dict = None,
                        scan_results: dict = None,
                        deauth_results: list = None, # List of deauth attempts
                        evil_twin_results: list = None, # List of evil twin sessions
                        cracking_results: list = None # List of cracking attempts
                        ):
        """
        Generates the final PDF report with collected data.
        """
        self.add_heading("WLAN Penetration Test Report", level=1)
        self.add_paragraph(f"Report generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.add_paragraph("This report summarizes the findings and actions performed during the WLAN penetration test.")
        self.story.append(Spacer(1, 0.4 * inch))

        # --- General Information ---
        self.add_heading("1. General Information", level=2)
        if general_info:
            self.add_paragraph(f"**Target Scope:** {general_info.get('scope', 'Not specified')}")
            self.add_paragraph(f"**Tester:** {general_info.get('tester', 'Not specified')}")
            self.add_paragraph(f"**Date(s) of Test:** {general_info.get('date_range', 'Not specified')}")
            self.add_paragraph(f"**Objective:** {general_info.get('objective', 'Not specified')}")
        else:
            self.add_paragraph("No general information provided.")
        self.story.append(Spacer(1, 0.2 * inch))

        # --- Scan Results ---
        self.add_heading("2. Network Scan Results", level=2)
        if scan_results and scan_results.get('access_points'):
            ap_data = [["BSSID", "ESSID", "Channel", "Privacy", "Power", "Last Seen"]]
            for ap in scan_results['access_points']:
                ap_data.append([
                    ap.get('BSSID', ''),
                    ap.get('ESSID', '[Hidden]'),
                    ap.get('Channel', ''),
                    ap.get('Privacy', ''),
                    ap.get('Power', ''),
                    ap.get('Last time seen', '')
                ])
            self.add_table(ap_data, title="Detected Access Points")

            if scan_results.get('clients'):
                client_data = [["Station MAC", "Connected To (BSSID)", "Probed ESSIDs", "Power", "Last Seen"]]
                for client in scan_results['clients']:
                    client_data.append([
                        client.get('Station MAC', ''),
                        client.get('BSSID', ''),
                        ", ".join(client.get('Probed ESSIDs', [])),
                        client.get('Power', ''),
                        client.get('Last time seen', '')
                    ])
                self.add_table(client_data, title="Detected Clients")
            else:
                self.add_paragraph("No clients detected during scan.")
        else:
            self.add_paragraph("No access points detected during scan.")
        self.story.append(Spacer(1, 0.2 * inch))

        # --- Deauthentication Attacks ---
        self.add_heading("3. Deauthentication Attacks", level=2)
        if deauth_results:
            deauth_table_data = [["Target BSSID", "Target Client", "Packets Sent", "Status", "Timestamp"]]
            for res in deauth_results:
                deauth_table_data.append([
                    res.get('bssid', ''),
                    res.get('client_mac', 'All'),
                    res.get('packets_sent', ''),
                    res.get('status', ''),
                    res.get('timestamp', '')
                ])
            self.add_table(deauth_table_data, title="Deauthentication Attempts")
        else:
            self.add_paragraph("No deauthentication attacks were performed.")
        self.story.append(Spacer(1, 0.2 * inch))

        # --- Evil Twin Attacks ---
        self.add_heading("4. Evil Twin Attacks", level=2)
        if evil_twin_results:
            et_table_data = [["ESSID", "Channel", "Encryption", "Bettercap Used", "Status", "Timestamp"]]
            for res in evil_twin_results:
                et_table_data.append([
                    res.get('essid', ''),
                    res.get('channel', ''),
                    res.get('encryption', ''),
                    "Yes" if res.get('bettercap_enabled') else "No",
                    res.get('status', ''),
                    res.get('timestamp', '')
                ])
            self.add_table(et_table_data, title="Evil Twin Deployments")
            self.add_paragraph("Note: Captured credentials from Evil Twin attacks would typically be logged by Bettercap or other tools and require manual extraction and addition here or automated parsing from log files.")
        else:
            self.add_paragraph("No Evil Twin attacks were performed.")
        self.story.append(Spacer(1, 0.2 * inch))


        # --- WPA/WPA2 Cracking Results ---
        self.add_heading("5. WPA/WPA2 Cracking Results", level=2)
        if cracking_results:
            cracked_data = [["Target ESSID", "Target BSSID", "Cracked Password", "Status", "Timestamp"]]
            for res in cracking_results:
                cracked_data.append([
                    res.get('target_essid', '[Unknown]'),
                    res.get('target_bssid', '[Unknown]'),
                    res.get('cracked_password', 'Not Cracked'),
                    res.get('status', ''),
                    res.get('timestamp', '')
                ])
            self.add_table(cracked_data, title="WPA/WPA2 Cracking Attempts")
        else:
            self.add_paragraph("No WPA/WPA2 cracking attempts were made or no passwords were cracked.")
        self.story.append(Spacer(1, 0.2 * inch))

        # --- Recommendations ---
        self.add_heading("6. Recommendations", level=2)
        self.add_paragraph("Based on the findings, the following recommendations are provided to improve the security posture of the wireless network:")
        self.add_paragraph("- Use strong, unique passwords for WPA2/WPA3 networks. Avoid common dictionary words.")
        self.add_paragraph("- Ensure WPA3 is enabled if supported by hardware for enhanced encryption.")
        self.add_paragraph("- Regularly update firmware of Access Points and client devices.")
        self.add_paragraph("- Implement MAC filtering (as a minor additional layer, not primary security).")
        self.add_paragraph("- Consider implementing 802.1x authentication (WPA2/3-Enterprise) for corporate environments.")
        self.add_paragraph("- Disable WPS if not actively in use.")
        self.add_paragraph("- Monitor network traffic for unusual activity.")
        self.story.append(Spacer(1, 0.4 * inch))

        # --- Disclaimer ---
        self.add_heading("Disclaimer", level=2)
        self.add_paragraph("This report is for educational and informational purposes only. The tools and techniques described herein should only be used in a legal and ethical manner, with explicit permission from the network owner.")
        self.story.append(Spacer(1, 0.2 * inch))


        try:
            self.doc.build(self.story)
            print(f"Report '{self.output_filename}' generated successfully.")
        except Exception as e:
            print(f"Error generating PDF report: {e}")

# Example Usage
if __name__ == "__main__":
    # Simulate collected data from module runs
    mock_scan_results = {
        'access_points': [
            {'BSSID': '00:1A:2B:3C:4D:5E', 'ESSID': 'MyHomeNet', 'Channel': '6', 'Privacy': 'WPA2', 'Power': '-50', 'Last time seen': '2025-05-21 10:00:00'},
            {'BSSID': 'F0:E1:D2:C3:B4:A5', 'ESSID': 'CoffeeShop', 'Channel': '1', 'Privacy': 'WPA', 'Power': '-75', 'Last time seen': '2025-05-21 10:05:00'},
            {'BSSID': 'AA:BB:CC:DD:EE:FF', 'ESSID': '[Hidden]', 'Channel': '11', 'Privacy': 'WEP', 'Power': '-60', 'Last time seen': '2025-05-21 10:10:00'}
        ],
        'clients': [
            {'Station MAC': '11:22:33:44:55:66', 'BSSID': '00:1A:2B:3C:4D:5E', 'Probed ESSIDs': ['MyHomeNet', 'AnotherNet'], 'Power': '-45', 'Last time seen': '2025-05-21 10:01:00'},
            {'Station MAC': '77:88:99:AA:BB:CC', 'BSSID': '(not associated)', 'Probed ESSIDs': ['PublicWiFi'], 'Power': '-80', 'Last time seen': '2025-05-21 10:06:00'}
        ]
    }

    mock_deauth_results = [
        {'bssid': 'F0:E1:D2:C3:B4:A5', 'client_mac': 'All', 'packets_sent': 100, 'status': 'Completed', 'timestamp': '2025-05-21 10:15:00'},
        {'bssid': '00:1A:2B:3C:4D:5E', 'client_mac': '11:22:33:44:55:66', 'packets_sent': 50, 'status': 'Completed', 'timestamp': '2025-05-21 10:16:00'}
    ]

    mock_evil_twin_results = [
        {'essid': 'Free_WiFi_Hotspot', 'channel': 6, 'encryption': 'open', 'bettercap_enabled': True, 'status': 'Successful', 'timestamp': '2025-05-21 10:30:00'}
    ]

    mock_cracking_results = [
        {'target_essid': 'MyHomeNet', 'target_bssid': '00:1A:2B:3C:4D:5E', 'cracked_password': 'SuperSecretPassword', 'status': 'Cracked', 'timestamp': '2025-05-21 10:45:00'},
        {'target_essid': 'CoffeeShop', 'target_bssid': 'F0:E1:D2:C3:B4:A5', 'cracked_password': 'Not Cracked', 'status': 'Failed (Wordlist Exhausted)', 'timestamp': '2025-05-21 11:00:00'}
    ]

    mock_general_info = {
        'scope': 'Internal Office Network',
        'tester': 'Your Name / Team',
        'date_range': '2025-05-20 to 2025-05-21',
        'objective': 'Identify weak configurations and potential vulnerabilities in the wireless infrastructure.'
    }

    report = ReportGenerator("KaliWLAN_Pentest_Report_Example.pdf")
    report.generate_report(
        general_info=mock_general_info,
        scan_results=mock_scan_results,
        deauth_results=mock_deauth_results,
        evil_twin_results=mock_evil_twin_results,
        cracking_results=mock_cracking_results
    )
