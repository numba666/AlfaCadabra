import os
import time
from BaseModule import BaseModule # Assuming BaseModule is in BaseModule.py

class CrackingModule(BaseModule):
    def __init__(self, interface: str):
        super().__init__(interface)
        self.cap_file = None # Path to the .cap file containing the handshake
        self.wordlist_path = None
        self.cracked_password = None
        self.target_bssid = None
        self.target_essid = None

    def start(self, cap_file: str, wordlist_path: str, bssid: str = None, essid: str = None):
        """
        Starts WPA/WPA2 cracking using aircrack-ng.
        Args:
            cap_file (str): Path to the .cap file containing the WPA handshake.
            wordlist_path (str): Path to the wordlist file.
            bssid (str, optional): BSSID of the target AP (improves efficiency).
            essid (str, optional): ESSID of the target AP (improves efficiency).
        """
        if not os.path.exists(cap_file):
            self.status = "error"
            self.error_buffer.append(f"Error: CAP file not found at {cap_file}")
            print(f"Error: CAP file not found at {cap_file}")
            return
        if not os.path.exists(wordlist_path):
            self.status = "error"
            self.error_buffer.append(f"Error: Wordlist not found at {wordlist_path}")
            print(f"Error: Wordlist not found at {wordlist_path}")
            return

        self.cap_file = cap_file
        self.wordlist_path = wordlist_path
        self.target_bssid = bssid
        self.target_essid = essid
        self.cracked_password = None
        self.status = "running"
        self._clear_buffers()

        command = [
            'sudo', 'aircrack-ng',
            '-w', self.wordlist_path,
            self.cap_file
        ]
        if bssid:
            command.extend(['-b', bssid])
        if essid:
            command.extend(['-e', essid]) # Note: -e is for ESSID filter, -b for BSSID

        print(f"Aircrack-ng command: {' '.join(command)}")

        # Run aircrack-ng and wait for it to finish.
        # Aircrack-ng prints progress to stderr.
        result = self._run_command(command, capture_output=True, wait=True)

        if result and result.returncode == 0:
            stdout_str = result.stdout
            stderr_str = result.stderr
            self.output_buffer.append(stdout_str)
            self.error_buffer.append(stderr_str)
            self._parse_aircrack_output(stdout_str + stderr_str) # Aircrack-ng prints to both

            if self.cracked_password:
                print(f"Password cracked: {self.cracked_password}")
                self.status = "finished"
            else:
                print("No password cracked.")
                self.status = "finished_no_result" # Or 'failed' based on your logic

        else:
            self.status = "error"
            print("Aircrack-ng execution failed.")

    def _parse_aircrack_output(self, output: str):
        """Parses aircrack-ng output for cracked password."""
        # Aircrack-ng's output format is quite specific.
        # Look for "KEY FOUND! [password]"
        match = re.search(r'KEY FOUND!\s*\[([^\]]+)\]', output)
        if match:
            self.cracked_password = match.group(1)
            self.results['cracked_password'] = self.cracked_password
            self.results['target_bssid'] = self.target_bssid
            self.results['target_essid'] = self.target_essid
            print(f"Parsed cracked password: {self.cracked_password}")
        else:
            print("No 'KEY FOUND!' string found in aircrack-ng output.")

    def get_results(self):
        """Returns the cracked password if found."""
        return self.results

# Example Usage (simulate GUI interaction)
if __name__ == "__main__":
    # !!! IMPORTANT: You need a .cap file with a WPA handshake and a wordlist.
    # To get a .cap file:
    # 1. Use ScanModule to find an AP.
    # 2. Use DeauthModule to deauth a client on that AP (while airodump-ng is running on that channel)
    #    This will capture the handshake.
    # 3. Stop airodump-ng (ScanModule.stop()). The .cap file will be in /tmp/airodump_scan_XXXX-01.cap

    # Create dummy files for demonstration (replace with actual files in your tests)
    dummy_cap_file = "/tmp/test_handshake.cap"
    dummy_wordlist = "/tmp/test_wordlist.txt"

    with open(dummy_cap_file, 'w') as f:
        f.write("DUMMY CAP FILE CONTENT - REPLACE WITH REAL .CAP")
    with open(dummy_wordlist, 'w') as f:
        f.write("password123\nhello\nworld\nsecretkey\n")

    test_bssid = "00:11:22:33:44:55"
    test_essid = "TestAP"

    print(f"Using dummy cap file: {dummy_cap_file}")
    print(f"Using dummy wordlist: {dummy_wordlist}")

    cracker = CrackingModule("N/A") # Interface is not directly used by aircrack-ng once .cap is captured

    print("\nStarting cracking (threaded)...")
    cracker.start_threaded(
        cap_file=dummy_cap_file,
        wordlist_path=dummy_wordlist,
        bssid=test_bssid,
        essid=test_essid
    )

    # Simulate GUI waiting for completion
    print("Cracking in progress (simulated wait of 10s)...")
    cracker.thread.join(timeout=10) # Wait for the thread to finish

    print("\nCracking finished.")
    print("Final status:", cracker.get_status())
    cracked_results = cracker.get_results()
    if 'cracked_password' in cracked_results:
        print(f"Cracked Password: {cracked_results['cracked_password']}")
    else:
        print("No password cracked or cracking failed.")

    print("\n--- Raw Output from Cracking ---")
    stdout, stderr = cracker.get_output()
    print("STDOUT:", stdout)
    print("STDERR:", stderr)

    # Clean up dummy files
    if os.path.exists(dummy_cap_file):
        os.remove(dummy_cap_file)
    if os.path.exists(dummy_wordlist):
        os.remove(dummy_wordlist)
