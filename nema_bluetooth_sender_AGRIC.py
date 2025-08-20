import serial
import time
import threading
import socket
import json
import base64

class NmeaBluetoothSender:
    # --- Konfiguracja (bez zmian) ---
    SERIAL_PORT = '/dev/ttyUSB0'
    BAUD_RATE = 115200
    TARGET_BT_MAC = '88:A2:9E:07:AD:97'
    TARGET_BT_PORT = 1

    # --- Konfiguracja Klienta NTRIP (bez zmian) ---
    NTRIP_IP = 'system.asgeupos.pl'
    NTRIP_PORT = 8080
    NTRIP_MOUNTPOINT = 'RTN4G_VRS_RTCM32'
    NTRIP_USER = 'pweiti/turbobolek'  # ZASTĄP
    NTRIP_PASSWORD = 'Globus7142001' # ZASTĄP
    NTRIP_GGA_INTERVAL = 10

    def __init__(self):
        self.ser = None
        self.bt_sock = None
        self.ntrip_sock = None

        # --- ZMIANA 1: Dodano pole 'roll' ---
        self.latest_gps_data = {
            'lat': 0.0,
            'lon': 0.0,
            'speed': 0.0,
            'heading': 0.0,
            'roll': 0.0, # <-- NOWE POLE
            'rtk_status': 0,
            'altitude': 0.0,
            'gps_time': ""
        }
        
        self.last_gga_for_ntrip = None
        self.last_gga_send_time = 0
        self.data_lock = threading.Lock()
        self.stop_event = threading.Event()

    # --- Wszystkie funkcje connect_* pozostają BEZ ZMIAN ---
    def connect_serial(self):
        while not self.stop_event.is_set():
            try:
                print(f"Próba połączenia z portem szeregowym {self.SERIAL_PORT}...")
                self.ser = serial.Serial(self.SERIAL_PORT, self.BAUD_RATE, timeout=1)
                print("Połączono z portem szeregowym.")
                return True
            except serial.SerialException as e:
                print(f"Błąd portu szeregowego: {e}. Ponowna próba za 5s.")
                time.sleep(5)
        return False

    def connect_bluetooth(self):
        while not self.stop_event.is_set():
            try:
                print(f"Próba połączenia z serwerem Bluetooth {self.TARGET_BT_MAC}...")
                if self.bt_sock: self.bt_sock.close()
                self.bt_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                self.bt_sock.connect((self.TARGET_BT_MAC, self.TARGET_BT_PORT))
                print("Połączono z serwerem Bluetooth na @traktor.")
                return True
            except socket.error as e:
                print(f"Błąd połączenia Bluetooth: {e}. Ponowna próba za 1s.")
                if self.bt_sock: self.bt_sock.close()
                self.bt_sock = None
                time.sleep(1)
        return False

    def connect_ntrip(self):
        if not self.last_gga_for_ntrip:
            print("Oczekiwanie na pierwszą wiadomość GGA przed połączeniem z NTRIP...")
            return False
        try:
            print(f"Łączenie z serwerem NTRIP {self.NTRIP_IP}:{self.NTRIP_PORT}...")
            if self.ntrip_sock: self.ntrip_sock.close()
            self.ntrip_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ntrip_sock.settimeout(10)
            self.ntrip_sock.connect((self.NTRIP_IP, self.NTRIP_PORT))
            user_pwd = f"{self.NTRIP_USER}:{self.NTRIP_PASSWORD}"
            user_pwd_encoded = base64.b64encode(user_pwd.encode('utf-8')).decode('utf-8')
            http_request = (
                f"GET /{self.NTRIP_MOUNTPOINT} HTTP/1.1\r\n"
                f"User-Agent: NTRIP PythonClient/1.0\r\n"
                f"Authorization: Basic {user_pwd_encoded}\r\n"
                f"Connection: close\r\n\r\n"
            )
            self.ntrip_sock.sendall(http_request.encode('ascii'))
            response = self.ntrip_sock.recv(4096)
            if b"ICY 200 OK" in response:
                print("Autoryzacja NTRIP pomyślna.")
                self.ntrip_sock.sendall(self.last_gga_for_ntrip.encode('ascii'))
                self.last_gga_send_time = time.time()
                return True
            else:
                print(f"Błąd autoryzacji NTRIP. Odpowiedź: {response.decode('ascii', 'ignore')}")
                self.ntrip_sock.close(); self.ntrip_sock = None
                return False
        except socket.error as e:
            print(f"Błąd gniazda NTRIP: {e}")
            if self.ntrip_sock: self.ntrip_sock.close()
            self.ntrip_sock = None
            return False

    def _nmea_to_decimal(self, nmea_coord, hemisphere):
        if not nmea_coord: return 0.0
        try:
            val = float(nmea_coord)
            deg = int(val / 100)
            minutes = val - deg * 100
            decimal = deg + minutes / 60.0
            if hemisphere.upper() in ['S', 'W']: decimal *= -1.0
            return decimal
        except (ValueError, TypeError): return 0.0

    def read_serial_data_thread(self):
        print("Uruchomiono wątek odczytu NMEA i zarządzania NTRIP.")
        while not self.stop_event.is_set():
            if not self.ser or not self.ser.is_open:
                self.connect_serial()
                continue
            try:
                line = self.ser.readline().decode('ascii', errors='ignore').strip()
                
                # --- ZMIANA 2: Logika parsowania dostosowana do #AGRICA ---
                if line.startswith("$GNGGA"):
                    parts = line.split(',')
                    if len(parts) > 9:
                        with self.data_lock:
                            self.latest_gps_data['lat'] = self._nmea_to_decimal(parts[2], parts[3])
                            self.latest_gps_data['lon'] = self._nmea_to_decimal(parts[4], parts[5])
                            self.latest_gps_data['rtk_status'] = int(parts[6]) if parts[6] else 0
                            self.latest_gps_data['gps_time'] = parts[1] if parts[1] else ""
                            self.latest_gps_data['altitude'] = float(parts[9]) if parts[9] else 0.0
                        self.last_gga_for_ntrip = line + "\r\n"

                elif line.startswith("#AGRICA"):
                    try:
                        data_part = line.split(';')[1].split('*')[0]
                        agric_parts = data_part.split(',')
                        heading_status = int(agric_parts[11 - 2])
                        if heading_status in [4, 5,0]: # Tylko jeśli kurs jest wiarygodny
                            with self.data_lock:
                                self.latest_gps_data['heading'] = float(agric_parts[21 - 2])
                                self.latest_gps_data['roll'] = float(agric_parts[22 - 2])
                                speed_kmh = float(agric_parts[24 - 2])
                                self.latest_gps_data['speed'] = speed_kmh / 3.6
                    except (ValueError, IndexError) as e:
                        print(f"\nBłąd parsowania AGRIC '{line}': {e}")
                # --- Koniec Zmiany 2 ---

                if self.last_gga_for_ntrip:
                    if not self.ntrip_sock:
                        self.connect_ntrip()
                    elif time.time() - self.last_gga_send_time > self.NTRIP_GGA_INTERVAL:
                        try:
                            self.ntrip_sock.sendall(self.last_gga_for_ntrip.encode('ascii'))
                            self.last_gga_send_time = time.time()
                        except socket.error as e:
                            print(f"\nBłąd wysyłania GGA do NTRIP: {e}.")
                            if self.ntrip_sock: self.ntrip_sock.close(); self.ntrip_sock = None
            except serial.SerialException as e:
                print(f"\nBłąd odczytu z portu szeregowego: {e}")
                if self.ser: self.ser.close(); self.ser = None
            except Exception as e:
                print(f"\nNieoczekiwany błąd w wątku odczytu: {e}")

    # --- Wątek ntrip_reader_thread pozostaje BEZ ZMIAN ---
    def ntrip_reader_thread(self):
        print("Uruchomiono wątek odbioru poprawek NTRIP.")
        while not self.stop_event.is_set():
            if not self.ntrip_sock:
                time.sleep(1)
                continue
            try:
                data = self.ntrip_sock.recv(4096)
                if data:
                    if self.ser and self.ser.is_open:
                        self.ser.write(data)
                else:
                    print("\nPołączenie NTRIP zamknięte przez serwer.")
                    if self.ntrip_sock: self.ntrip_sock.close()
                    self.ntrip_sock = None
            except socket.timeout:
                continue
            except (socket.error, serial.SerialException) as e:
                print(f"\nBłąd w pętli NTRIP: {e}")
                if self.ntrip_sock: self.ntrip_sock.close()
                self.ntrip_sock = None

    def send_data_via_bluetooth_thread(self):
        print("Uruchomiono wątek wysyłania przez Bluetooth.")
        while not self.stop_event.is_set():
            if not self.bt_sock:
                self.connect_bluetooth()
                if self.stop_event.is_set(): break
                continue
            with self.data_lock:
                data_to_send = json.dumps(self.latest_gps_data).encode('utf-8')
            try:
                self.bt_sock.sendall(data_to_send + b'\n')
            except socket.error:
                print("\nBłąd wysyłania przez Bluetooth. Próba ponownego połączenia...")
                if self.bt_sock: self.bt_sock.close(); self.bt_sock = None
            
            # --- ZMIANA 3: Dostosowanie częstotliwości do 20 Hz ---
            time.sleep(0.05)

    def run(self):
        serial_manager_thread = threading.Thread(target=self.read_serial_data_thread, daemon=True)
        ntrip_corrections_thread = threading.Thread(target=self.ntrip_reader_thread, daemon=True)
        bluetooth_sender_thread = threading.Thread(target=self.send_data_via_bluetooth_thread, daemon=True)

        serial_manager_thread.start()
        ntrip_corrections_thread.start()
        bluetooth_sender_thread.start()

        try:
            while True:
                with self.data_lock:
                    # --- ZMIANA 4: Dodano 'roll' do odczytu i wydruku ---
                    lat = self.latest_gps_data['lat']
                    lon = self.latest_gps_data['lon']
                    status = self.latest_gps_data['rtk_status']
                    speed = self.latest_gps_data['speed']
                    heading = self.latest_gps_data['heading']
                    roll = self.latest_gps_data['roll']
                
                status_map = {0: "Brak", 1: "SPS", 2: "DGPS", 4: "RTK-FIX", 5: "RTK-FLOAT"}
                bt_status = "OK" if self.bt_sock and self.bt_sock.fileno() != -1 else "Brak"
                ntrip_status = "OK" if self.ntrip_sock and self.ntrip_sock.fileno() != -1 else "Brak"
                
                print(f"Lat: {lat:.6f}, Lon: {lon:.6f} | RTK: {status_map.get(status, f'Inny({status})')} | V: {speed:.4f} m/s | H: {heading:.4f}° | R: {roll:.4f}° | BT: {bt_status} | NTRIP: {ntrip_status}      ", end='\r')
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nZamykanie...")
            self.stop_event.set()
            serial_manager_thread.join(timeout=1)
            ntrip_corrections_thread.join(timeout=1)
            bluetooth_sender_thread.join(timeout=1)
            if self.ser: self.ser.close()
            if self.bt_sock: self.bt_sock.close()
            if self.ntrip_sock: self.ntrip_sock.close()
            print("Zasoby zwolnione. Do widzenia.")

if __name__ == '__main__':
    sender = NmeaBluetoothSender()
    sender.run()