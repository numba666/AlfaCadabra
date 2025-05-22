import sys
import os
import time

# Pfad zum Framework hinzufügen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'AlfaCadabra_Framework')))

from AlfaCadabra_Framework.modules.AlfaAdapterManager import AlfaAdapterManager

# Callback-Funktion für die Ausgabe des Managers
def manager_output_callback(output):
    print(f"Manager Output: {output}")

# Callback-Funktion für Statusmeldungen des Managers
def manager_status_callback(status_type, message):
    # Einfache Formatierung für den Test
    print(f"Manager Status ({status_type.upper()}): {message}")
    # Optionale detaillierte Debug-Ausgabe
    # print(f"[{status_type.upper()}] {message}")

if __name__ == "__main__":
    print("Starte AlfaAdapterManager Test via main.py...")

    # AlfaAdapterManager instanziieren
    adapter_manager = AlfaAdapterManager(
        output_callback=manager_output_callback,
        status_callback=manager_status_callback
    )

    # --- Test 1: Schnittstellen abrufen ---
    print("\n--- Test 1: Schnittstellen abrufen ---")
    interfaces = adapter_manager.get_interfaces()
    if interfaces:
        first_interface = interfaces[0]
        print(f"Erste gefundene Schnittstelle für weitere Tests: {first_interface}")
        adapter_manager.set_interface(first_interface)
    else:
        print("Keine Schnittstellen gefunden. Tests können nicht fortgesetzt werden.")
        exit()

    # --- Test 2: Aktuelle MAC-Adresse von der ersten Schnittstelle abrufen ---
    print(f"\n--- Test 2: Aktuelle MAC-Adresse von {adapter_manager.interface} abrufen ---")
    current_mac_before_change = adapter_manager.get_current_mac()
    if current_mac_before_change:
        print(f"Aktuelle MAC-Adresse vor Änderung: {current_mac_before_change}")
    else:
        print("Konnte MAC-Adresse nicht abrufen. Fortfahren auf eigenes Risiko.")

    # --- Test 3: Ändere MAC-Adresse auf zufällig (im Managed-Modus) ---
    print(f"\n--- Test 3: Ändere MAC-Adresse von {adapter_manager.interface} auf zufällig ---")
    mac_changed = adapter_manager.change_mac_address()
    if mac_changed:
        print("MAC-Änderung erfolgreich.")
    else:
        print("MAC-Änderung fehlgeschlagen.")
    time.sleep(2) # Kurze Pause nach MAC-Änderung


    # --- Test 4: Setze Schnittstelle in Monitor-Modus ---
    # Beachte: Die Schnittstelle hat jetzt bereits die neue MAC-Adresse
    print(f"\n--- Test 4: Setze {adapter_manager.interface} in Monitor-Modus ---")
    monitor_mode_set = adapter_manager.set_monitor_mode()
    if monitor_mode_set:
        print(f"Monitor-Modus für {adapter_manager.interface} erfolgreich gesetzt.")
    else:
        print("Setzen des Monitor-Modus fehlgeschlagen.")
    time.sleep(2) # Kurze Pause nach Monitor-Modus

    # --- Test 5: MAC-Adresse im Monitor-Modus abrufen (optional, zur Überprüfung) ---
    # Oft wird die MAC im Monitor-Modus nicht immer korrekt angezeigt oder ist anders.
    # Dieser Test ist primär zur Beobachtung.
    if adapter_manager.interface and adapter_manager.interface.endswith('mon'):
        print(f"\n--- Test 5: Aktuelle MAC-Adresse von {adapter_manager.interface} (Monitor-Modus) abrufen ---")
        mac_in_monitor_mode = adapter_manager.get_current_mac()
        if mac_in_monitor_mode:
            print(f"MAC-Adresse im Monitor-Modus: {mac_in_monitor_mode}")
        else:
            print("Konnte MAC-Adresse im Monitor-Modus nicht abrufen.")
    else:
        print("\n--- Test 5 übersprungen: Nicht im Monitor-Modus ---")


    # --- Test 6: Deaktiviere Monitor-Modus für die Schnittstelle ---
    print(f"\n--- Test 6: Deaktiviere Monitor-Modus für {adapter_manager.interface} ---")
    monitor_mode_disabled = adapter_manager.disable_monitor_mode()
    if monitor_mode_disabled:
        print(f"Monitor-Modus für {adapter_manager.interface} erfolgreich deaktiviert.")
    else:
        print("Deaktivieren des Monitor-Modus fehlgeschlagen.")
    time.sleep(2) # Kurze Pause nach Deaktivierung


    # --- Test 7: Setze MAC-Adresse auf ursprünglich zurück (optional) ---
    print(f"\n--- Test 7: Setze MAC-Adresse von {adapter_manager.interface} auf ursprünglich zurück ---")
    mac_reset = adapter_manager.reset_mac_address()
    if mac_reset:
        print("MAC-Adresse erfolgreich auf ursprünglich zurückgesetzt.")
    else:
        print("Zurücksetzen der MAC-Adresse fehlgeschlagen oder nicht nötig.")
    
    print("\nAlfaAdapterManager Tests abgeschlossen.")