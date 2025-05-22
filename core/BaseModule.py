import subprocess
import threading
import time

class BaseModule:
    def __init__(self, output_callback=None, status_callback=None):
        """
        Basisklasse für alle Module des AlfaCadabra Frameworks.
        Bietet grundlegende Funktionalität zum Starten/Stoppen von Prozessen
        und zur Statusmeldung.

        Args:
            output_callback (callable): Eine Funktion, die aufgerufen wird,
                                       wenn es neue Ausgaben vom Prozess gibt.
            status_callback (callable): Eine Funktion, die aufgerufen wird,
                                        um den Status des Moduls zu aktualisieren.
        """
        self.process = None
        self.is_running = False
        self.output_callback = output_callback
        self.status_callback = status_callback
        self.output_thread = None
        self.error_message = None

    def _update_status(self, message, level="info"):
        """Interne Methode zum Senden von Statusaktualisierungen."""
        if self.status_callback:
            self.status_callback(message, level)
        print(f"[{level.upper()}] {message}") # Debugging-Ausgabe im Terminal

    def _read_output(self, process):
        """Liest die Ausgabe des Prozesses in einem separaten Thread."""
        self.error_message = None # Fehler vor neuem Start zurücksetzen
        while self.is_running and process.poll() is None:
            line = process.stdout.readline()
            if line:
                decoded_line = line.decode('utf-8', errors='ignore').strip()
                if self.output_callback:
                    self.output_callback(decoded_line)
                #print(f"Output: {decoded_line}") # Debugging-Ausgabe
            time.sleep(0.01) # Kleine Pause, um CPU-Auslastung zu reduzieren

        # Wenn der Prozess beendet ist, lies den Rest der Ausgabe
        remaining_output = process.stdout.read()
        if remaining_output:
            decoded_remaining = remaining_output.decode('utf-8', errors='ignore').strip()
            if self.output_callback:
                self.output_callback(decoded_remaining)
            #print(f"Remaining Output: {decoded_remaining}") # Debugging-Ausgabe

        # Überprüfe den Exit-Code des Prozesses
        return_code = process.poll()
        if return_code != 0:
            error_output = process.stderr.read()
            if error_output:
                decoded_error = error_output.decode('utf-8', errors='ignore').strip()
                self.error_message = decoded_error
                self._update_status(f"Prozess mit Fehler beendet (Code: {return_code}): {decoded_error}", "error")
            else:
                self.error_message = f"Prozess mit Fehler beendet (Code: {return_code}), keine detaillierte Fehlermeldung."
                self._update_status(self.error_message, "error")
        else:
            self._update_status(f"Prozess beendet (Code: {return_code})", "info")


    def start(self, command):
        """
        Startet einen externen Prozess.

        Args:
            command (list): Eine Liste von Strings, die den Befehl und seine Argumente darstellen.
                            Beispiel: ['airodump-ng', 'wlan0mon']
        Returns:
            bool: True, wenn der Prozess erfolgreich gestartet wurde, sonst False.
        """
        if self.is_running:
            self._update_status("Modul läuft bereits.", "warning")
            return False

        try:
            self._update_status(f"Starte Befehl: {' '.join(command)}", "info")
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, # Auch stderr abfangen
                text=False, # Wichtig, um Bytes zu lesen, die dann dekodiert werden
                bufsize=1, # Line-buffered output
                universal_newlines=False # Wichtig, um Bytes zu lesen
            )
            self.is_running = True
            # Starte einen Thread, um die Ausgabe zu lesen, damit die GUI nicht blockiert wird
            self.output_thread = threading.Thread(target=self._read_output, args=(self.process,))
            self.output_thread.daemon = True # Der Thread wird beendet, wenn das Hauptprogramm endet
            self.output_thread.start()
            self._update_status("Modul erfolgreich gestartet.", "success")
            return True
        except FileNotFoundError:
            self.error_message = f"Befehl nicht gefunden: '{command[0]}'. Stellen Sie sicher, dass das Tool installiert und im PATH ist."
            self._update_status(self.error_message, "error")
            return False
        except Exception as e:
            self.error_message = f"Fehler beim Starten des Moduls: {e}"
            self._update_status(self.error_message, "error")
            return False

    def stop(self):
        """Stoppt den laufenden Prozess."""
        if not self.is_running or self.process is None:
            self._update_status("Modul ist nicht aktiv.", "info")
            return False

        self._update_status("Stoppe Modul...", "info")
        try:
            if self.process.poll() is None: # Prüfen, ob der Prozess noch läuft
                self.process.terminate() # Sendet SIGTERM
                self.process.wait(timeout=5) # Warte 5 Sekunden auf Beendigung
                if self.process.poll() is None: # Wenn er immer noch läuft
                    self.process.kill() # Sendet SIGKILL
                    self._update_status("Prozess zwangsbeendet (SIGKILL).", "warning")
                else:
                    self._update_status("Prozess beendet.", "info")
            else:
                self._update_status("Prozess war bereits beendet.", "info")

            self.is_running = False
            if self.output_thread and self.output_thread.is_alive():
                self.output_thread.join(timeout=1) # Gib dem Thread kurz Zeit zum Beenden
            self._update_status("Modul erfolgreich gestoppt.", "success")
            return True
        except Exception as e:
            self.error_message = f"Fehler beim Stoppen des Moduls: {e}"
            self._update_status(self.error_message, "error")
            return False

    def get_error(self):
        """Gibt die letzte Fehlermeldung zurück."""
        return self.error_message

# Beispiel für die Nutzung von BaseModule (zum Testen, kann später entfernt werden)
if __name__ == "__main__":
    print("Starte BaseModule Test...")

    def test_output_callback(line):
        print(f"Callback Output: {line}")

    def test_status_callback(message, level):
        print(f"Callback Status ({level}): {message}")

    # Test 1: Gültiger Befehl (z.B. 'ls')
    print("\n--- Test 1: 'ls -l' ---")
    test_module_ls = BaseModule(test_output_callback, test_status_callback)
    if test_module_ls.start(['ls', '-l']):
        time.sleep(2) # Gib dem Befehl Zeit, sich zu beenden
        test_module_ls.stop()
    print(f"LS Error: {test_module_ls.get_error()}")

    # Test 2: Ungültiger Befehl (sollte Fehler auslösen)
    print("\n--- Test 2: Ungültiger Befehl 'nonexistent_command' ---")
    test_module_fail = BaseModule(test_output_callback, test_status_callback)
    if not test_module_fail.start(['nonexistent_command']):
        print(f"Erwarteter Fehler: {test_module_fail.get_error()}")
    else:
        print("Unerwarteter Erfolg bei nonexistent_command")
        test_module_fail.stop()


    # Test 3: Befehl, der eine Weile läuft (z.B. ping)
    print("\n--- Test 3: 'ping -c 5 google.com' (und früh stoppen) ---")
    test_module_ping = BaseModule(test_output_callback, test_status_callback)
    if test_module_ping.start(['ping', '-c', '5', 'google.com']):
        time.sleep(2) # Lässt ping 2 Sekunden laufen
        test_module_ping.stop()
    print(f"PING Error: {test_module_ping.get_error()}")
    print("\nAlle BaseModule Tests abgeschlossen.")