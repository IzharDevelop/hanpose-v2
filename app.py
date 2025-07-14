# app.py - Versi UI Dua Tahap & Sensor
# Pastikan pustaka berikut sudah diinstal:
# pip install opencv-python mediapipe flask flask-socketio pyserial

from flask import Flask, render_template, jsonify, request, Response, session, redirect, url_for
from flask_socketio import SocketIO, emit
import cv2
import mediapipe as mp
import serial.tools.list_ports
import time
import base64
import threading
import json # Untuk memproses data sensor jika JSON
import webbrowser # Untuk membuka browser secara otomatis

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here' # Ganti dengan kunci rahasia yang kuat
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variable to store loaded translations
translations = {}
AVAILABLE_LANGUAGES = ['en', 'id'] # Define available languages

def load_translations(lang_code):
    """Loads translations from the specified language file."""
    global translations
    lang_file_path = f"C:/Users/MSI GF63/Downloads/apps - Copy/language/{lang_code}.json"
    try:
        with open(lang_file_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
    except FileNotFoundError:
        print(f"Translation file not found for {lang_code}. Loading default (en).")
        with open("C:/Users/MSI GF63/Downloads/apps - Copy/language/en.json", 'r', encoding='utf-8') as f:
            translations = json.load(f)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {lang_file_path}. Loading default (en).")
        with open("C:/Users/MSI GF63/Downloads/apps - Copy/language/en.json", 'r', encoding='utf-8') as f:
            translations = json.load(f)



# --- Variabel Global untuk Mengelola Status Aplikasi ---
arduino = None
cap = None # Objek VideoCapture
camera_thread = None
stop_camera_thread_flag = [False]
# Tambahan: untuk menyimpan data sensor terakhir
last_sensor_data = {
    'temperature': 'N/A',
    'humidity': 'N/A',
    'light': 'N/A',
    'ph_water': 'N/A',
    'water_level': 'N/A',
    'pump_status': 'N/A'
}
serial_monitor_lines = [] # Untuk menyimpan baris log serial monitor

# --- Konfigurasi MediaPipe Hands ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

prev_hand_state = None

# --- Fungsi Utility untuk Deteksi Port Serial ---
@app.route('/get_serial_ports')
def get_serial_ports():
    ports = serial.tools.list_ports.comports()
    available_ports = []
    for port, desc, hwid in sorted(ports):
        if "COM" in port or "/dev/tty" in port:
            clean_desc = desc.split('(')[0].strip() if '(' in desc else desc.strip()
            available_ports.append({'port': port, 'description': clean_desc})
    return jsonify(available_ports)

# --- Fungsi Utility untuk Deteksi Kamera ---
@app.route('/get_cameras')
def get_cameras():
    available_cameras = []
    for i in range(5):
        temp_cap = cv2.VideoCapture(i)
        if temp_cap.isOpened():
            available_cameras.append({'id': i, 'name': f'{translations["camera_name"]} {i}'})
            temp_cap.release()
    return jsonify(available_cameras)

# --- Endpoint untuk Pratinjau Kamera Konfigurasi ---
@app.route('/preview_camera/<int:camera_id>')
def preview_camera(camera_id):
    def generate_preview():
        preview_cap = cv2.VideoCapture(camera_id)
        if not preview_cap.isOpened():
            return b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + cv2.imencode('.jpg', cv2.imread('static/no_camera.png'))[1].tobytes() + b'\r\n' # Gambar placeholder
        
        preview_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320) # Resolusi lebih kecil untuk preview
        preview_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        start_time = time.time()
        while (time.time() - start_time) < 5: # Preview hanya selama 5 detik
            success, frame = preview_cap.read()
            if not success:
                break
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        preview_cap.release()
    
    return Response(generate_preview(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- SocketIO Event Handler: Memulai Sistem (Konfigurasi Submit) ---
@socketio.on('start_system')
def start_system_handler(data):
    """Menangani permintaan untuk memulai sistem dengan konfigurasi yang dipilih."""
    global arduino, cap, prev_hand_state, camera_thread, serial_monitor_lines

    selected_port = data.get('port')
    selected_baud_rate = int(data.get('baudRate', 9600))
    selected_camera_id = int(data.get('cameraId', 0))

    # --- 1. Koneksi Arduino ---
    if arduino and arduino.is_open:
        try: arduino.close()
        except: pass
    arduino = None
    serial_monitor_lines = [] # Reset monitor serial

    try:
        arduino = serial.Serial(selected_port, selected_baud_rate, timeout=1)
        time.sleep(2) # Beri waktu Arduino untuk reset
        load_translations(session.get('lang', 'en'))
        emit('arduino_status', {'success': True, 'message': f'{translations["connected_to_arduino"]} {selected_port}'})
        print(f"Koneksi serial ke Arduino berhasil di {selected_port}!")
    except serial.SerialException as e:
        emit('arduino_status', {'success': False, 'message': f'{translations["failed_to_connect_arduino"]} {e}'})
        print(f"Gagal terhubung ke Arduino: {e}")
        # Jangan return di sini, lanjutkan mencoba kamera meskipun Arduino gagal
    
    # --- 2. Inisialisasi Kamera ---
    if camera_thread and camera_thread.is_alive():
        stop_camera_thread_flag[0] = True
        camera_thread.join(timeout=2)
        stop_camera_thread_flag[0] = False

    if cap and cap.isOpened():
        cap.release()
        print("Kamera sebelumnya dilepaskan.")
    cap = None # Pastikan cap None sebelum inisialisasi baru

    cap = cv2.VideoCapture(selected_camera_id)
    if not cap.isOpened():
        load_translations(session.get('lang', 'en'))
        emit('camera_status', {'success': False, 'message': f'{translations["failed_to_open_camera"]} {selected_camera_id}.'})
        print(f"Gagal membuka kamera ID {selected_camera_id}.")
        return # Jika kamera gagal, tidak ada gunanya melanjutkan

    # Set resolusi kamera utama untuk deteksi pose
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    load_translations(session.get('lang', 'en'))
    emit('camera_status', {'success': True, 'message': f'{translations["streaming_from_camera"]} {selected_camera_id} dimulai.'})
    print(f"Streaming dari Kamera {selected_camera_id} dimulai.")
    prev_hand_state = None

    # --- 3. Memulai Thread Pemrosesan ---
    stop_camera_thread_flag[0] = False
    camera_thread = threading.Thread(target=generate_frames_and_sensors)
    camera_thread.daemon = True
    camera_thread.start()

    # Beri sinyal ke frontend untuk beralih ke tampilan operasional
    emit('system_started', {'success': True})


# --- Fungsi Deteksi Status Tangan ---
def get_hand_state(hand_landmarks):
    # Logika deteksi tangan Anda (tidak berubah dari versi sebelumnya)
    fingers_open_count = 0
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    thumb_ip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP]
    thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_MCP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

    if (thumb_tip.x < thumb_ip.x and thumb_tip.x < thumb_mcp.x - (thumb_mcp.x - wrist.x) * 0.5) or \
       (thumb_tip.x > thumb_ip.x and thumb_tip.x > thumb_mcp.x + (wrist.x - thumb_mcp.x) * 0.5):
        fingers_open_count += 1

    finger_tips = [mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
                   mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.PINKY_TIP]
    finger_pips = [mp_hands.HandLandmark.INDEX_FINGER_PIP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
                   mp_hands.HandLandmark.RING_FINGER_PIP, mp_hands.HandLandmark.PINKY_PIP]

    for i in range(4):
        if hand_landmarks.landmark[finger_tips[i]].y < hand_landmarks.landmark[finger_pips[i]].y:
            fingers_open_count += 1

    if fingers_open_count >= 4:
        return 'open'
    else:
        return 'closed'

# --- Fungsi Utama: Generate Frames, Deteksi Pose, Baca Sensor ---
def generate_frames_and_sensors():
    """Mengambil frame, memproses pose, membaca sensor, dan mengirim ke frontend. (VERSI PERBAIKAN)"""
    global prev_hand_state, cap, last_sensor_data, serial_monitor_lines

    # PERBAIKAN 2: Muat terjemahan sekali saja di awal thread, bukan di dalam loop.
    # Ini menghindari masalah akses 'session' dari thread latar belakang.
    lang = session.get('lang', 'en')
    load_translations(lang)
    
    if not cap or not cap.isOpened():
        print(translations.get('camera_not_open', 'Error: Camera is not open or available.'))
        return

    print("generate_frames_and_sensors: Memulai loop pemrosesan...")
    
    while cap.isOpened() and not stop_camera_thread_flag[0]:
        # --- 1. Baca Frame Kamera & Deteksi Pose ---
        success, image = cap.read()
        if not success:
            print(translations.get('failed_to_read_frame', 'Error: Failed to read frame from camera.'))
            break

        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)

        current_status_text = translations.get('not_detected', 'Not Detected')
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                current_hand_state = get_hand_state(hand_landmarks)

                if current_hand_state != prev_hand_state:
                    command_to_send = 'O' if current_hand_state == 'open' else 'C'
                    
                    # Menggunakan .get() untuk keamanan jika kunci terjemahan tidak ada
                    hand_status_str = translations.get(current_hand_state, current_hand_state)
                    servo_pos = '90' if current_hand_state == 'open' else '0'
                    current_status_text = f"{translations.get('hand_status', 'Hand')} {hand_status_str} ({translations.get('servo', 'Servo')} {servo_pos})"

                    if arduino and arduino.is_open:
                        try:
                            arduino.write(command_to_send.encode('utf-8'))
                            print(f"Mengirim '{command_to_send}' ke Arduino.")
                        except serial.SerialException as e:
                            print(f"Serial error during send: {e}")
                        except Exception as e:
                            print(f"Unexpected error during send: {e}")
                    prev_hand_state = current_hand_state
                else:
                    hand_status_str = translations.get(prev_hand_state, prev_hand_state)
                    servo_pos = '90' if prev_hand_state == 'open' else '0'
                    current_status_text = f"{translations.get('hand_status', 'Hand')} {hand_status_str} ({translations.get('servo', 'Servo')} {servo_pos})"
        else:
            if prev_hand_state is not None:
                print(translations.get('hand_lost', 'Hand tracking lost.'))
                prev_hand_state = None
            current_status_text = translations.get('not_detected', 'Not Detected')

        socketio.emit('hand_status', {'status': current_status_text})

        try:
            ret, buffer = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            encoded_frame = base64.b64encode(buffer.tobytes()).decode('utf-8')
            socketio.emit('video_frame', {'image': 'data:image/jpeg;base64,' + encoded_frame})
        except Exception as e:
            print(f"Error encoding frame: {e}")

        # --- 2. Baca Data Sensor dari Arduino (VERSI PERBAIKAN) ---
        if arduino and arduino.is_open:
            try:
                while arduino.in_waiting > 0:
                    line = arduino.readline().decode('utf-8').strip()
                    if not line:
                        continue

                    # Simpan semua output ke log monitor
                    serial_monitor_lines.append(line)
                    if len(serial_monitor_lines) > 50:
                        serial_monitor_lines.pop(0)
                    socketio.emit('arduino_log_line', {'line': line})

                    # PERBAIKAN 1: Parsing lebih fleksibel dan aman
                    # Tidak lagi memerlukan "DATA:", cukup cari baris dengan 5 koma (6 nilai)
                    sensor_values = line.split(',')
                    if len(sensor_values) == 6:
                        try:
                            # Coba konversi semua nilai, jika gagal, baris ini bukan data sensor
                            light_val = sensor_values[0]
                            water_level_val = sensor_values[1]
                            ph_water_val = sensor_values[2]
                            humidity_val = sensor_values[3]
                            temp_val = sensor_values[4]
                            pump_status_val = sensor_values[5]

                            # Jika berhasil, update last_sensor_data
                            last_sensor_data['light'] = light_val
                            last_sensor_data['water_level'] = water_level_val
                            last_sensor_data['ph_water'] = ph_water_val
                            last_sensor_data['humidity'] = humidity_val
                            last_sensor_data['temperature'] = temp_val
                            last_sensor_data['pump_status'] = pump_status_val
                            
                            # Kirim data yang berhasil di-parse ke frontend
                            socketio.emit('sensor_data', last_sensor_data)
                            print(f"Sensor data parsed and sent: {last_sensor_data}")

                        except ValueError as e:
                            # Gagal konversi, mungkin ini bukan baris data. Abaikan.
                            print(f"Could not parse sensor values from line: '{line}'. Error: {e}")
                        except Exception as e:
                            print(f"An unexpected error occurred during sensor parsing: {e}")

            except serial.SerialException as e:
                print(f"Serial error during read: {e}")
            except Exception as e:
                print(f"Unexpected error processing serial data: {e}")

        socketio.sleep(0.01) # Sedikit ditambah untuk memberi waktu CPU

    # --- Pembersihan setelah loop selesai ---
    print(translations.get('loop_stopped', 'Processing loop stopped.'))
    if cap and cap.isOpened():
        cap.release()
    print(translations.get('camera_released', 'Camera released.'))


# --- Flask Routes ---
@app.route('/')
def index():
    """Melayani halaman utama UI."""
    return render_template('index.html', lang=session.get('lang', 'en'), t=translations)

@app.route('/team')
def team():
    """Melayani halaman informasi tim."""
    return render_template('team.html', lang=session.get('lang', 'en'), t=translations)

@app.route('/documentation')
def documentation():
    """Melayani halaman dokumentasi."""
    return render_template('documentation.html', lang=session.get('lang', 'en'), t=translations)

# --- SocketIO Connection & Disconnection Handlers ---
@socketio.on('connect')
def handle_connect():
    """Dijalankan saat klien web baru terhubung."""
    print(translations['client_connected'])
    # Kirim daftar port dan kamera saat terhubung
    emit('available_ports', get_serial_ports().json)
    emit('available_cameras', get_cameras().json)
    # Kirim data sensor terakhir dan log serial monitor saat klien terhubung
    emit('sensor_data', last_sensor_data)
    for line in serial_monitor_lines:
        emit('arduino_log_line', {'line': line})


@socketio.on('disconnect')
def handle_disconnect():
    """Dijalankan saat klien web terputus."""
    print(translations['client_disconnected'])
    # Beri sinyal thread kamera untuk berhenti jika masih berjalan
    if camera_thread and camera_thread.is_alive():
        stop_camera_thread_flag[0] = True
        camera_thread.join(timeout=2)
        stop_camera_thread_flag[0] = False # Reset bendera

    # Lepaskan objek kamera jika masih aktif
    if cap and cap.isOpened():
        print(translations['camera_released_on_disconnect'])
        cap.release()

# --- Main Execution Block ---
if __name__ == '__main__':
    port = 5000
    url = f"http://127.0.0.1:{port}"
    load_translations('en') # Load English translations for console messages
    print(f"{translations['running_flask_server']} {url}")

    # Fungsi untuk membuka browser setelah server siap
    def open_browser():
        webbrowser.open(url)

    # Menjalankan fungsi open_browser setelah penundaan singkat
    threading.Timer(1.5, open_browser).start()

    try:
        socketio.run(app, debug=False, allow_unsafe_werkzeug=True, host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print(translations['server_stopped_by_user'])
    except Exception as e:
        print(f"{translations['fatal_server_error']} {e}")
    finally:
        # --- Pembersihan Akhir Saat Program Utama Berhenti ---
        if arduino and arduino.is_open:
            arduino.close()
            print(translations['arduino_serial_closed'])
        
        if camera_thread and camera_thread.is_alive():
            stop_camera_thread_flag[0] = True
            camera_thread.join(timeout=2) 
            stop_camera_thread_flag[0] = False

        if cap and cap.isOpened():
            cap.release()
            print(translations['camera_released'])
        print(translations['python_program_cleaned_up'])