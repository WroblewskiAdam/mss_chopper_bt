#!/bin/bash

echo "🔧 Instalacja automatycznego uruchamiania NMEA Bluetooth Sender w screen..."

# Sprawdź czy jesteś root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Ten skrypt musi być uruchomiony jako root (sudo)"
    echo "Uruchom: sudo ./install_screen_autostart.sh"
    exit 1
fi

# Sprawdź czy pliki istnieją
if [ ! -f "start_nmea_screen.sh" ]; then
    echo "❌ Plik start_nmea_screen.sh nie istnieje!"
    exit 1
fi

if [ ! -f "stop_nmea_screen.sh" ]; then
    echo "❌ Plik stop_nmea_screen.sh nie istnieje!"
    exit 1
fi

if [ ! -f "nema_bluetooth_sender_AGRIC.py" ]; then
    echo "❌ Plik nema_bluetooth_sender_AGRIC.py nie istnieje!"
    exit 1
fi

echo "📁 Kopiowanie skryptów do /usr/local/bin/..."

# Skopiuj skrypty do systemu
cp start_nmea_screen.sh /usr/local/bin/
cp stop_nmea_screen.sh /usr/local/bin/

# Ustaw odpowiednie uprawnienia
chmod +x /usr/local/bin/start_nmea_screen.sh
chmod +x /usr/local/bin/stop_nmea_screen.sh

echo "📝 Tworzenie pliku systemd service..."

# Utwórz plik systemd service
cat > /etc/systemd/system/nmea-screen.service << EOF
[Unit]
Description=NMEA Bluetooth Sender Screen Session
After=network.target bluetooth.service
Wants=network.target bluetooth.service

[Service]
Type=oneshot
User=pi
ExecStart=/usr/local/bin/start_nmea_screen.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Przeładowanie systemd..."
systemctl daemon-reload

echo "✅ Włączanie serwisu..."
systemctl enable nmea-screen.service

echo "🚀 Uruchamianie serwisu..."
systemctl start nmea-screen.service

echo ""
echo "🎉 Instalacja zakończona pomyślnie!"
echo ""
echo "📋 Status serwisu:"
systemctl status nmea-screen.service --no-pager -l

echo ""
echo "📚 Przydatne komendy:"
echo "  Podłącz się do terminala: screen -r nmea-sender"
echo "  Lista sesji:              screen -ls"
echo "  Zatrzymaj program:        sudo /usr/local/bin/stop_nmea_screen.sh"
echo "  Uruchom ponownie:         sudo systemctl restart nmea-screen"
echo "  Status serwisu:           sudo systemctl status nmea-screen"
echo ""
echo "🔄 Program będzie automatycznie uruchamiany w screen przy każdym starcie RPi!"
echo "📱 Po połączeniu SSH użyj 'screen -r nmea-sender' aby zobaczyć output na żywo!"
