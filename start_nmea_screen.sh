#!/bin/bash

# Skrypt uruchamiający NMEA Bluetooth Sender w screen
# Uruchamia się automatycznie po bootowaniu RPi

SCREEN_NAME="nmea-sender"
SCRIPT_PATH="/home/pi/mss/nema_bluetooth_sender_AGRIC.py"
WORKING_DIR="/home/pi/mss"

# Sprawdź czy screen już działa
if screen -list | grep -q "$SCREEN_NAME"; then
    echo "Screen $SCREEN_NAME już działa. Restartuję..."
    screen -S $SCREEN_NAME -X quit
    sleep 2
fi

# Przejdź do katalogu roboczego
cd "$WORKING_DIR"

# Uruchom program w nowym screen
echo "Uruchamianie NMEA Bluetooth Sender w screen '$SCREEN_NAME'..."
screen -dmS $SCREEN_NAME bash -c "cd '$WORKING_DIR' && python3 '$SCRIPT_PATH'"

# Sprawdź czy się uruchomił
sleep 3
if screen -list | grep -q "$SCREEN_NAME"; then
    echo "✅ Program uruchomiony pomyślnie w screen '$SCREEN_NAME'"
    echo ""
    echo "📋 Aby się podłączyć do terminala:"
    echo "   screen -r $SCREEN_NAME"
    echo ""
    echo "📋 Lista aktywnych sesji:"
    echo "   screen -ls"
    echo ""
    echo "📋 Aby wyjść z screen (program nadal działa):"
    echo "   Ctrl+A, potem D"
else
    echo "❌ Błąd uruchamiania programu w screen"
    exit 1
fi
