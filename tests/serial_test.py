import serial.tools.list_ports

print("=== COM-Port Test ===")
print("Suche nach verfügbaren COM-Ports...")

try:
    ports = list(serial.tools.list_ports.comports())
    
    if ports:
        print(f"\nGefundene Ports ({len(ports)}):")
        for i, port in enumerate(ports, 1):
            print(f"{i}. Port: {port.device}")
            print(f"   Beschreibung: {port.description}")
            print(f"   Hardware-ID: {port.hwid}")
            print()
    else:
        print("KEINE COM-Ports gefunden!")
        print("Mögliche Ursachen:")
        print("- Arduino nicht angeschlossen")
        print("- Treiber nicht installiert")
        print("- Port von anderem Programm verwendet")
        
except ImportError:
    print("FEHLER: pyserial nicht installiert!")
    print("Installiere mit: pip install pyserial")

except Exception as e:
    print(f"FEHLER beim Port-Scan: {e}")

print("\n=== Test beendet ===")
input("Drücke Enter zum Schließen...")