#!/bin/bash

echo "🗑️  Deinstalacja automatycznego uruchamiania NMEA Bluetooth Sender w screen..."

# Sprawdź czy jesteś root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Ten skrypt musi być uruchomiony jako root (sudo)"
    echo "Uruchom: sudo ./uninstall_screen_autostart.sh"
    exit 1
fi

echo "🛑 Zatrzymywanie serwisu..."
systemctl stop nmea-screen.service

echo "❌ Wyłączanie serwisu..."
systemctl disable nmea-screen.service

echo "🗑️  Usuwanie pliku service..."
rm -f /etc/systemd/system/nmea-screen.service

echo "🗑️  Usuwanie skryptów z systemu..."
rm -f /usr/local/bin/start_nmea_screen.sh
rm -f /usr/local/bin/stop_nmea_screen.sh

echo "🔄 Przeładowanie systemd..."
systemctl daemon-reload

echo "🛑 Zatrzymywanie programu w screen..."
if screen -list | grep -q "nmea-sender"; then
    screen -S nmea-sender -X quit
    echo "✅ Screen nmea-sender zatrzymany"
fi

echo "🧹 Sprawdzanie wiszących procesów..."
PYTHON_PIDS=$(pgrep -f "nema_bluetooth_sender_AGRIC.py")
if [ ! -z "$PYTHON_PIDS" ]; then
    echo "🔍 Znaleziono wiszące procesy Python: $PYTHON_PIDS"
    echo "Wymuszenie zakończenia..."
    kill -9 $PYTHON_PIDS
    echo "✅ Wszystkie procesy zakończone"
fi

echo ""
echo "✅ Deinstalacja zakończona pomyślnie!"
echo "Automatyczne uruchamianie NMEA Bluetooth Sender w screen zostało usunięte."
echo ""
echo "📋 Status screen:"
screen -ls
