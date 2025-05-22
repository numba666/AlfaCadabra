import subprocess

def get_wlan_interfaces():
    try:
        output = subprocess.check_output(['iwconfig'], universal_newlines=True)
        interfaces = []
        for line in output.split('\n'):
            if 'IEEE 802.11' in line:
                parts = line.split()
                interface_name = parts[0]
                interfaces.append(interface_name)
        return interfaces
    except subprocess.CalledProcessError:
        print("Error: iwconfig not found or permission denied.")
        return []

def set_monitor_mode(interface):
    try:
        subprocess.run(['sudo', 'ifconfig', interface, 'down'], check=True)
        subprocess.run(['sudo', 'iwconfig', interface, 'mode', 'monitor'], check=True)
        subprocess.run(['sudo', 'ifconfig', interface, 'up'], check=True)
        print(f"{interface} set to monitor mode.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error setting {interface} to monitor mode: {e}")
        return False

# Beispiel:
# available_interfaces = get_wlan_interfaces()
# for iface in available_interfaces:
#     if "wlan" in iface: # Filter for typical WLAN interfaces
#         set_monitor_mode(iface)
