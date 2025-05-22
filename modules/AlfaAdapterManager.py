import subprocess
import threading
import time
import re # Benötigt für reguläre Ausdrücke

from core.BaseModule import BaseModule

class AlfaAdapterManager(BaseModule):
    def __init__(self, output_callback=None, status_callback=None):
        super().__init__(output_callback, status_callback)
        self.interface = None # Aktuell ausgewählte Netzwerkschnittstelle
        self.original_mac = {} # Speichert die ursprüngliche MAC-Adresse pro Schnittstelle

    def set_interface(self, interface):
        """Setzt die Netzwerkschnittstelle, mit der gearbeitet werden soll."""
        self.interface = interface
        self._update_status(f"Arbeits-Schnittstelle auf '{interface}' gesetzt.", "info")

    def get_interfaces(self):
        """
        Listet verfügbare Netzwerkschnittstellen auf.
        Benötigt 'ip link show' und 'iwconfig' zur besseren Erkennung von WLAN-Adaptern.
        """
        self.interfaces_cache = [] # Cache für gefundene Interfaces
        self._update_status("Suche nach Netzwerkschnittstellen...", "info")
        
        found_interfaces = set() # Verwende ein Set, um Duplikate zu vermeiden

        # --- Methode 1: ip link show (moderner und bevorzugt) ---
        try:
            command_ip = ['ip', 'link', 'show']
            result_ip = subprocess.run(command_ip, capture_output=True, text=True, check=True, errors='ignore', timeout=10)
            for line in result_ip.stdout.splitlines():
                # Regex, um Schnittstellennamen wie "2: wlan0: <BROADCAST..." zu finden
                match = re.match(r'^\d+:\s+(\w+):.*<BROADCAST,MULTICAST,UP,LOWER_UP>.*', line)
                if match:
                    iface_name = match.group(1).strip()
                    # Prüfe, ob es sich um eine WLAN-Schnittstelle handeln könnte (heuristisch)
                    # Dies ist nicht 100% genau, aber eine gute Annäherung
                    if "wlan" in iface_name or "wl" in iface_name or "mon" in iface_name:
                        found_interfaces.add(iface_name)
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self._update_status(f"Fehler bei 'ip link show': {e}", "warning")
            # Nicht fatal, versuchen wir die nächste Methode

        # --- Methode 2: iwconfig (falls ip link show nicht alles findet oder fehlen sollte) ---
        try:
            command_iw = ['iwconfig']
            result_iw = subprocess.run(command_iw, capture_output=True, text=True, check=True, errors='ignore', timeout=10)
            for line in result_iw.stdout.splitlines():
                if "IEEE 802.11" in line: # Zeigt an, dass es ein WLAN-Adapter ist
                    iface_name = line.split(" ")[0].strip()
                    if iface_name:
                        found_interfaces.add(iface_name)
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self._update_status(f"Fehler bei 'iwconfig': {e}. Stellen Sie sicher, dass wireless-tools installiert sind.", "warning")
        
        interfaces = sorted(list(found_interfaces)) # Konvertiere zu Liste und sortiere
        self.interfaces_cache = interfaces # Cache aktualisieren

        if not interfaces:
            self._update_status("Keine WLAN-Schnittstellen gefunden. Stellen Sie sicher, dass Ihre Adapter angeschlossen und Treiber geladen sind.", "error")
        else:
            self._update_status(f"Gefundene Schnittstellen: {', '.join(interfaces)}", "success")
        return interfaces

    def get_current_mac(self, interface=None):
        """Ruft die aktuelle MAC-Adresse der Schnittstelle ab."""
        target_interface = interface if interface else self.interface
        if not target_interface:
            self._update_status("Keine Schnittstelle zum Abrufen der MAC-Adresse angegeben.", "error")
            return None

        try:
            # Befehl: ip link show wlan0
            command = ['ip', 'link', 'show', target_interface]
            result = subprocess.run(command, capture_output=True, text=True, check=True, errors='ignore', timeout=5)
            output_lines = result.stdout.splitlines()
            for line in output_lines:
                if "link/ether" in line:
                    mac_address = line.split("link/ether")[1].strip().split(" ")[0]
                    self._update_status(f"Aktuelle MAC von {target_interface}: {mac_address}", "info")
                    return mac_address
            self._update_status(f"Keine MAC-Adresse für {target_interface} gefunden. Ist der Adapter aktiv?", "warning")
            return None
        except FileNotFoundError:
            self._update_status("Befehl 'ip' nicht gefunden. Stellen Sie sicher, dass iproute2 installiert ist.", "error")
            return None
        except subprocess.CalledProcessError as e:
            self._update_status(f"Fehler beim Abrufen der MAC für {target_interface}: {e.stderr.strip()}", "error")
            return None
        except subprocess.TimeoutExpired:
            self._update_status(f"Zeitüberschreitung beim Abrufen der MAC für {target_interface}.", "error")
            return None
        except Exception as e:
            self._update_status(f"Unerwarteter Fehler beim Abrufen der MAC: {e}", "error")
            return None

    def set_monitor_mode(self, interface=None):
        """
        Versetzt die Netzwerkschnittstelle in den Monitor-Modus.
        Verwendet 'airmon-ng' für Einfachheit.
        """
        target_interface = interface if interface else self.interface
        if not target_interface:
            self._update_status("Keine Schnittstelle zum Setzen des Monitor-Modus angegeben.", "error")
            return False

        self._update_status(f"Versuche, {target_interface} in den Monitor-Modus zu versetzen...", "info")

        try:
            # 1. Kill Prozesse, die stören könnten (airmon-ng check kill)
            self._update_status("Beende störende Prozesse mit 'airmon-ng check kill'...", "info")
            # airmon-ng check kill gibt auf stderr aus, wir leiten es zu stdout um für _read_output
            kill_cmd = ['sudo', 'airmon-ng', 'check', 'kill']
            self.start(kill_cmd)
            # Wichtig: Wir müssen warten, bis der Prozess fertig ist, bevor wir fortfahren
            # BaseModule.start startet im Hintergrund. Hier wollen wir synchrone Ausführung
            if self.process:
                self.process.wait()
                if self.process.returncode != 0:
                    self._update_status("Airmon-ng check kill hatte Probleme. Manuelle Prüfung empfohlen.", "warning")
            self.is_running = False # BaseModule hat den Prozess gestartet und beendet

            # 2. Schnittstelle deaktivieren, um MAC-Adresse zu wechseln (optional, aber gute Praxis)
            self._update_status(f"Deaktiviere Schnittstelle {target_interface}...", "info")
            disable_cmd = ['sudo', 'ip', 'link', 'set', target_interface, 'down']
            result = subprocess.run(disable_cmd, capture_output=True, text=True, check=False, errors='ignore', timeout=5)
            if result.returncode != 0:
                self._update_status(f"Fehler beim Deaktivieren von {target_interface}: {result.stderr.strip()}", "warning")
            time.sleep(1) # Kurze Pause

            # 3. Monitor-Modus aktivieren
            monitor_cmd = ['sudo', 'airmon-ng', 'start', target_interface]
            self._update_status(f"Starte '{' '.join(monitor_cmd)}'...", "info")
            # Wir verwenden subprocess.run hier, um die Ausgabe zu fangen, die den neuen Namen enthält
            # BaseModule.start ist für kontinuierliche Ausgaben gedacht
            result = subprocess.run(monitor_cmd, capture_output=True, text=True, check=False, errors='ignore', timeout=30)
            
            if result.returncode != 0:
                self._update_status(f"Airmon-ng start für {target_interface} fehlgeschlagen (Code: {result.returncode}): {result.stderr.strip()}", "error")
                return False

            # Die Ausgabe von airmon-ng enthält den neuen Namen (z.B. wlan0mon)
            new_interface = self._find_monitor_interface_from_output(result.stdout, target_interface)
            
            if new_interface:
                self.interface = new_interface # Aktualisiere die Arbeits-Schnittstelle
                self._update_status(f"'{target_interface}' erfolgreich in Monitor-Modus '{new_interface}' versetzt.", "success")
                return True
            else:
                self._update_status(f"Konnte neuen Monitor-Schnittstellennamen nicht finden nach 'airmon-ng start {target_interface}'.", "error")
                return False
        except FileNotFoundError:
            self._update_status("Tool 'airmon-ng' nicht gefunden. Stellen Sie sicher, dass aircrack-ng installiert ist.", "error")
            return False
        except subprocess.TimeoutExpired:
            self._update_status("Zeitüberschreitung bei 'airmon-ng start'.", "error")
            return False
        except Exception as e:
            self._update_status(f"Fehler beim Setzen des Monitor-Modus für {target_interface}: {e}", "error")
            return False

    def disable_monitor_mode(self, interface=None):
        """
        Deaktiviert den Monitor-Modus und versetzt die Schnittstelle in den Managed-Modus.
        Verwendet 'airmon-ng' zum Stoppen.
        """
        target_interface = interface if interface else self.interface
        if not target_interface:
            self._update_status("Keine Schnittstelle zum Deaktivieren des Monitor-Modus angegeben.", "error")
            return False

        self._update_status(f"Versuche, Monitor-Modus für {target_interface} zu deaktivieren...", "info")
        try:
            # 1. Beende airmon-ng
            stop_monitor_cmd = ['sudo', 'airmon-ng', 'stop', target_interface]
            self._update_status(f"Starte '{' '.join(stop_monitor_cmd)}'...", "info")
            result = subprocess.run(stop_monitor_cmd, capture_output=True, text=True, check=False, errors='ignore', timeout=30)
            
            if result.returncode != 0:
                self._update_status(f"Airmon-ng stop für {target_interface} fehlgeschlagen (Code: {result.returncode}): {result.stderr.strip()}", "warning")
                # Trotzdem versuchen, die Schnittstelle hochzufahren und den Modus zu prüfen

            # 2. Schnittstelle wieder aktivieren und auf den ursprünglichen Namen setzen (falls umbenannt)
            # Wir nehmen an, dass der ursprüngliche Name der ohne "mon" am Ende ist.
            original_iface = target_interface.replace("mon", "") if target_interface.endswith("mon") else target_interface
            
            self._update_status(f"Aktiviere Schnittstelle {original_iface} und setze sie hoch...", "info")
            enable_cmd = ['sudo', 'ip', 'link', 'set', original_iface, 'up']
            result_up = subprocess.run(enable_cmd, capture_output=True, text=True, check=False, errors='ignore', timeout=5)
            if result_up.returncode != 0:
                self._update_status(f"Fehler beim Aktivieren von {original_iface}: {result_up.stderr.strip()}", "warning")
            
            time.sleep(1) # Kurze Pause

            # 3. Prüfen, ob der Modus wieder Managed ist
            current_mode = self._get_interface_mode(original_iface)
            if current_mode in ["Managed", "Master"]: # Master für AP-Modus, Managed für Client
                self._update_status(f"'{target_interface}' erfolgreich deaktiviert. Modus von '{original_iface}' ist jetzt '{current_mode}'.", "success")
                self.interface = original_iface # Setze auf den Originalnamen zurück
                return True
            else:
                self._update_status(f"Konnte Monitor-Modus für '{target_interface}' nicht vollständig deaktivieren. Aktueller Modus von '{original_iface}': {current_mode}", "warning")
                return False
        except FileNotFoundError:
            self._update_status("Tool 'airmon-ng' nicht gefunden. Stellen Sie sicher, dass aircrack-ng installiert ist.", "error")
            return False
        except subprocess.TimeoutExpired:
            self._update_status("Zeitüberschreitung bei 'airmon-ng stop'.", "error")
            return False
        except Exception as e:
            self._update_status(f"Fehler beim Deaktivieren des Monitor-Modus für {target_interface}: {e}", "error")
            return False

    def change_mac_address(self, interface=None, new_mac=None):
        """
        Ändert die MAC-Adresse der Schnittstelle.
        Verwendet 'macchanger'.
        """
        target_interface = interface if interface else self.interface
        if not target_interface:
            self._update_status("Keine Schnittstelle für MAC-Änderung angegeben.", "error")
            return False

        current_mac = self.get_current_mac(target_interface)
        if current_mac and target_interface not in self.original_mac:
            self.original_mac[target_interface] = current_mac # Speichere nur beim ersten Mal

        if new_mac is None:
            # Zufällige MAC-Adresse
            mac_cmd = ['sudo', 'macchanger', '-r', target_interface]
            self._update_status(f"Ändere MAC-Adresse von {target_interface} auf zufällig...", "info")
        else:
            # Spezifische MAC-Adresse
            mac_cmd = ['sudo', 'macchanger', '--mac', new_mac, target_interface]
            self._update_status(f"Ändere MAC-Adresse von {target_interface} auf {new_mac}...", "info")

        try:
            # Schnittstelle deaktivieren
            self._update_status(f"Deaktiviere Schnittstelle {target_interface} für MAC-Änderung...", "info")
            disable_cmd = ['sudo', 'ip', 'link', 'set', target_interface, 'down']
            result_down = subprocess.run(disable_cmd, capture_output=True, text=True, check=False, errors='ignore', timeout=5)
            if result_down.returncode != 0:
                self._update_status(f"Fehler beim Deaktivieren von {target_interface} für MAC-Änderung: {result_down.stderr.strip()}", "warning")
            time.sleep(1) # <-- Etwas mehr Pause nach dem Deaktivieren

            # MAC-Adresse ändern
            result_mac = subprocess.run(mac_cmd, capture_output=True, text=True, check=False, errors='ignore', timeout=10)
            if result_mac.returncode != 0:
                self._update_status(f"Fehler bei 'macchanger' für {target_interface}: {result_mac.stderr.strip()}", "error")
            time.sleep(1) # <-- Etwas mehr Pause nach macchanger
            
            # Schnittstelle wieder aktivieren
            self._update_status(f"Aktiviere Schnittstelle {target_interface}...", "info")
            enable_cmd = ['sudo', 'ip', 'link', 'set', target_interface, 'up']
            result_up = subprocess.run(enable_cmd, capture_output=True, text=True, check=False, errors='ignore', timeout=5)
            if result_up.returncode != 0:
                self._update_status(f"Fehler beim Aktivieren von {target_interface} nach MAC-Änderung: {result_up.stderr.strip()}", "warning")
            time.sleep(2) # <-- Längere Pause nach dem Aktivieren, um den Adapter zu stabilisieren

            new_current_mac = self.get_current_mac(target_interface)
            # Prüfe, ob die MAC-Adresse tatsächlich anders ist oder eine neue zufällig generiert wurde
            if new_current_mac and (new_current_mac.lower() != current_mac.lower() or new_mac is None):
                self._update_status(f"MAC-Adresse für {target_interface} erfolgreich geändert auf {new_current_mac}.", "success")
                return True
            else:
                self._update_status(f"MAC-Adresse für {target_interface} konnte nicht geändert werden. Aktuelle MAC: {new_current_mac}", "error")
                if result_mac.stderr.strip():
                    self._update_status(f"Macchanger-Meldung: {result_mac.stderr.strip()}", "info")
                return False
        except FileNotFoundError:
            self._update_status("Tool 'macchanger' nicht gefunden. Stellen Sie sicher, dass macchanger installiert ist.", "error")
            return False
        except subprocess.TimeoutExpired:
            self._update_status("Zeitüberschreitung bei MAC-Adressenänderung.", "error")
            return False
        except Exception as e:
            self._update_status(f"Fehler beim Ändern der MAC-Adresse für {target_interface}: {e}", "error")
            return False

    def reset_mac_address(self, interface=None):
        """Setzt die MAC-Adresse auf die ursprüngliche zurück (falls gespeichert)."""
        target_interface = interface if interface else self.interface
        if not target_interface:
            self._update_status("Keine Schnittstelle für MAC-Reset angegeben.", "error")
            return False

        # Prüfen, ob die ursprüngliche MAC für die aktuelle (ggf. umbenannte) Schnittstelle gespeichert ist
        # oder für den Originalnamen
        mac_to_reset = None
        if target_interface in self.original_mac and self.original_mac[target_interface]:
            mac_to_reset = self.original_mac[target_interface]
        elif target_interface.replace("mon", "") in self.original_mac: # falls wlan0mon zu wlan0 wurde
            mac_to_reset = self.original_mac[target_interface.replace("mon", "")]


        if mac_to_reset:
            self._update_status(f"Setze MAC-Adresse für {target_interface} auf ursprüngliche zurück: {mac_to_reset}", "info")
            return self.change_mac_address(target_interface, mac_to_reset)
        else:
            self._update_status(f"Keine ursprüngliche MAC-Adresse für {target_interface} gespeichert oder gefunden.", "warning")
            return False

    def _get_interface_mode(self, interface):
        """Interne Hilfsfunktion: Ruft den aktuellen Modus der Schnittstelle ab (Managed, Monitor, etc.)."""
        try:
            command = ['iwconfig', interface]
            result = subprocess.run(command, capture_output=True, text=True, check=True, errors='ignore', timeout=5)
            output_lines = result.stdout.splitlines()
            for line in output_lines:
                if "Mode:" in line:
                    mode = line.split("Mode:")[1].split(" ")[0].strip()
                    return mode
            return "Unbekannt"
        except (FileNotFoundError, subprocess.CalledProcessError):
            return "Fehler"
        except subprocess.TimeoutExpired:
            self._update_status(f"Zeitüberschreitung beim Abrufen des Interface-Modus für {interface}.", "error")
            return "Fehler"
        except Exception as e:
            self._update_status(f"Unerwarteter Fehler beim Abrufen des Interface-Modus für {interface}: {e}", "error")
            return "Fehler"

    def _find_monitor_interface_from_output(self, airmon_output, original_interface):
        """
        Interne Hilfsfunktion: Sucht den neuen Monitor-Schnittstellennamen in der airmon-ng Ausgabe.
        Airmon-ng gibt oft etwas wie "Monitor mode enabled on wlan0mon" oder "Interface changed to wlan0mon" aus.
        """
        # Suche nach spezifischen Mustern in der airmon-ng-Ausgabe
        # Beispiel: "monitor mode enabled on wlan0mon"
        match = re.search(r'monitor mode enabled on (\w+)', airmon_output, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Beispiel: "interface wlan0 changed to wlan0mon"
        match = re.search(r'interface\s+\w+\s+changed\s+to\s+(\w+)', airmon_output, re.IGNORECASE)
        if match:
            return match.group(1)

        # Fallback: Wenn airmon-ng einfach nur wlan0mon erstellt, ohne es explizit zu sagen
        # oder wenn der Original-Name mit "mon" erweitert wurde
        if original_interface.endswith("mon"): # Falls es schon im Mon-Modus war und so hieß
            return original_interface
        
        # Prüfe, ob ein neuer "mon"-Adapter aufgetaucht ist
        # Manchmal ist es einfach der Originalname + "mon"
        possible_new_iface = original_interface + "mon"
        if possible_new_iface in self.get_interfaces(): # Rufe die Schnittstellen neu ab
            return possible_new_iface

        # Wenn alles fehlschlägt, kehren wir den Originalnamen zurück
        # oder geben None zurück, wenn kein Mon-Modus erkannt wurde.
        return None

# Der Test-Block bleibt in main.py, nicht hier.
# Beispiel für die Nutzung von AlfaAdapterManager (zum Testen)
# if __name__ == "__main__":
#     ... (Dieser Teil ist in main.py)