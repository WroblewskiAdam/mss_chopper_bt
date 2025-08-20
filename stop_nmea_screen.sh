#!/bin/bash

# Skrypt zatrzymujący NMEA Bluetooth Sender w screen

SCREEN_NAME="nmea-sender"

echo "🛑 Zatrzymywanie NMEA Bluetooth Sender..."

# Sprawdź czy screen działa
if screen -list | grep -q "$SCREEN_NAME"; then
    echo "Znaleziono aktywną sesję screen '$SCREEN_NAME'"
    
    # Wyślij sygnał SIGTERM do procesu Python
    echo "Wysyłanie sygnału zatrzymania..."
    screen -S $SCREEN_NAME -X stuff $'\003'  # Ctrl+C
    
    # Poczekaj chwilę na graceful shutdown
    sleep 3
    
    # Sprawdź czy proces nadal działa
    if screen -list | grep -q "$SCREEN_NAME"; then
        echo "Wymuszenie zamknięcia screen..."
        screen -S $SCREEN_NAME -X quit
    fi
    
    echo "✅ Program zatrzymany pomyślnie"
else
    echo "ℹ️  Brak aktywnej sesji screen '$SCREEN_NAME'"
fi

# Sprawdź czy nie ma wiszących procesów Python
PYTHON_PIDS=$(pgrep -f "nema_bluetooth_sender_AGRIC.py")
if [ ! -z "$PYTHON_PIDS" ]; then
    echo "🔍 Znaleziono wiszące procesy Python: $PYTHON_PIDS"
    echo "Wymuszenie zakończenia..."
    kill -9 $PYTHON_PIDS
    echo "✅ Wszystkie procesy zakończone"
fi

echo "📋 Status screen:"
screen -ls
