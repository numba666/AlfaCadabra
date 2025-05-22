import os
import csv
import re
import time
from BaseModule import BaseModule # Assuming BaseModule is in BaseModule.py

class ScanModule(BaseModule):
    def __init__(self, interface: str):
        super().__init__(interface)
        self.airodump_output_prefix = f"/tmp/airodump_scan_{os.getpid()}" # Unique prefix for this run
        self.aps = []
        self.clients = []
        self.csv_file = None # Will be set to the actual csv file path

    def start(self):
        """
        Starts airodump-ng scan on the specified interface.
        This method should be run in a separate thread to avoid blocking the GUI.
        """
        print(f"Starting Airodump-ng scan on {self.interface}...")
        self.status = "running"
        self._clear_buffers()
        self.aps = []
        self.clients = []

        # Command to start airodump-ng writing to a CSV file
        command = [
            'sudo', 'airodump-ng',
            '--output-format', 'csv',
            '--write', self.airodump_output_prefix,
            self.interface
        ]
        print(f"Airodump-ng command: {' '.join(command)}")

        # Start airodump-ng as a subprocess, don't wait for it to finish
        self.process = self._run_command(command, capture_output=False, wait=False)

        if self.process:
            # Poll the CSV file for updates
            print("Airodump-ng started. Polling for results...")
            while self.status == "running" and self.process.poll() is None:
                # Airodump-ng creates files like <prefix>-01.csv, -01.kismet.csv etc.
                # We are interested in the main CSV for APs/Clients
                current_csv_file = f"{self.airodump_output_prefix}-01.csv"
                if os.path.exists(current_csv_file):
                    self.csv_file = current_csv_file
                    self._parse_csv_output(current_csv_file)
                else:
                    # print(f"Waiting for {current_csv_file} to be created...")
                    pass # Keep quiet, it takes a moment to create
                time.sleep(2) # Poll every 2 seconds

            if self.process.poll() is not None:
                print("Airodump-ng process terminated.")
                self.status = "finished" # Or "error" if it exited with an error code

        else:
            self.status = "error"
            print("Failed to start Airodump-ng process.")

    def _parse_csv_output(self, csv_path: str):
        """Parses the airodump-ng CSV output file."""
        new_aps = []
        new_clients = []
        try:
            # Read the CSV file, ignoring potential encoding errors
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                ap_section = False
                client_section = False
                for row in reader:
                    # Skip empty rows
                    if not row or not row[0].strip():
                        continue

                    # Detect section headers
                    if row[0].strip() == 'BSSID' and not client_section: # APs section
                        ap_section = True
                        client_section = False
                        continue
                    elif row[0].strip() == 'Station MAC': # Clients section
                        client_section = True
                        ap_section = False
                        continue

                    if ap_section:
                        # BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, #beacons, #data, #/s, GPS latitude, GPS longitude, Altitude, Fixed, ESSID, Key
                        if len(row) >= 14: # Ensure enough columns for basic AP info
                            try:
                                ap_data = {
                                    'BSSID': row[0].strip(),
                                    'First time seen': row[1].strip(),
                                    'Last time seen': row[2].strip(),
                                    'Channel': row[3].strip(),
                                    'Speed': row[4].strip(),
                                    'Privacy': row[5].strip(),
                                    'Cipher': row[6].strip(),
                                    'Authentication': row[7].strip(),
                                    'Power': row[8].strip(),
                                    'ESSID': row[13].strip() if row[13].strip() else "[Hidden]" # ESSID can be empty
                                }
                                new_aps.append(ap_data)
                            except IndexError:
                                # This happens if a row is malformed or shorter than expected
                                # print(f"Skipping malformed AP row: {row}")
                                pass

                    elif client_section:
                        # Station MAC, First time seen, Last time seen, Power, #packets, BSSID, Probed ESSIDs
                        if len(row) >= 6: # Ensure enough columns for basic client info
                            try:
                                client_data = {
                                    'Station MAC': row[0].strip(),
                                    'First time seen': row[1].strip(),
                                    'Last time seen': row[2].strip(),
                                    'Power': row[3].strip(),
                                    'Packets': row[4].strip(),
                                    'BSSID': row[5].strip(), # AP MAC client is connected to (or (not associated))
                                    'Probed ESSIDs': [e.strip() for e in row[6:] if e.strip()] if len(row) > 6 else []
                                }
                                new_clients.append(client_data)
                            except IndexError:
                                # print(f"Skipping malformed Client row: {row}")
                                pass

            # Update results only if new data is available
            if new_aps:
                self.aps = new_aps
            if new_clients:
                self.clients = new_clients

            self.results = {
                "access_points": self.aps,
                "clients": self.clients
            }

        except FileNotFoundError:
            print(f"CSV file not found: {csv_path}")
        except Exception as e:
            print(f"Error parsing Airodump-ng CSV: {e}")

    def stop(self):
        """Stops the airodump-ng process and cleans up temporary files."""
        super().stop() # Call base class stop to terminate subprocess
        # Clean up CSV files
        if self.airodump_output_prefix:
            for ext in ['.csv', '.kismet.csv', '.cap', '.log']: # Airodump-ng creates various files
                file_to_delete = f"{self.airodump_output_prefix}-01{ext}"
                if os.path.exists(file_to_delete):
                    try:
                        os.remove(file_to_delete)
                        print(f"Cleaned up {file_to_delete}")
                    except OSError as e:
                        print(f"Error cleaning up {file_to_delete}: {e}")

    def get_results(self):
        """Returns the parsed APs and Clients."""
        return self.results

# Example Usage (simulate GUI interaction)
if __name__ == "__main__":
    # Ensure your interface is in monitor mode before running this!
    # e.g., using AlfaAdapterManager.set_monitor_mode('wlan0mon')
    test_interface = "wlan0mon" # Replace with your actual monitor interface

    print(f"Please ensure {test_interface} is in monitor mode and you have sudo rights.")
    # For testing, you might need to run a separate script to put it in monitor mode.
    # From a terminal: sudo airmon-ng start wlan0 (replace wlan0 with your adapter)

    scanner = ScanModule(test_interface)

    print("Starting scan (threaded)...")
    scanner.start_threaded()

    # Simulate GUI polling for results
    scan_duration = 20 # seconds
    start_time = time.time()
    while time.time() - start_time < scan_duration and scanner.get_status() == "running":
        results = scanner.get_results()
        if results['access_points']:
            print(f"\n--- Current APs ({len(results['access_points'])}): ---")
            for ap in results['access_points'][:5]: # Print first 5 APs
                print(f"  BSSID: {ap['BSSID']}, ESSID: {ap['ESSID']}, Channel: {ap['Channel']}, Privacy: {ap['Privacy']}")
        if results['clients']:
            print(f"\n--- Current Clients ({len(results['clients'])}): ---")
            for client in results['clients'][:5]: # Print first 5 clients
                print(f"  MAC: {client['Station MAC']}, Connected to: {client['BSSID']}, Probed: {client['Probed ESSIDs']}")
        time.sleep(5) # Update every 5 seconds

    scanner.stop_threaded()
    print("\nScan finished or stopped.")
    final_results = scanner.get_results()
    print("\n--- Final Scan Results ---")
    print(f"Total APs: {len(final_results['access_points'])}")
    print(f"Total Clients: {len(final_results['clients'])}")

    # You could also access raw output/errors if needed
    # raw_out, raw_err = scanner.get_output()
    # print("\nRaw Output:", raw_out)
    # print("Raw Errors:", raw_err)
