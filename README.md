# Dashboard Kontrol Hand Gesture & Sensor Monitoring

Proyek ini adalah sebuah sistem kontrol dan monitoring berbasis web yang memungkinkan interaksi dengan perangkat keras Arduino melalui deteksi gerakan tangan dan pembacaan sensor secara *real-time*.

## Fitur Utama

-   **Deteksi Gerakan Tangan:** Menggunakan kamera dan MediaPipe untuk mendeteksi status tangan (terbuka/tertutup) dan mengirimkan perintah ke Arduino.
-   **Monitoring Sensor:** Membaca dan menampilkan data dari berbagai sensor yang terhubung ke Arduino:
    -   **Cahaya:** Mengontrol LED/relay (Pin D11) berdasarkan intensitas cahaya (Sensor A0).
    -   **Level Air:** Mengontrol pompa (Pin D10) berdasarkan level air (Sensor A1).
    -   **pH Air:** Mengontrol buzzer (Pin D9) berdasarkan nilai pH (Sensor A2).
    -   **Kelembaban:** Mengontrol kipas (Pin D8) berdasarkan tingkat kelembaban (Sensor A3).
    -   **Suhu:** Membaca suhu lingkungan (Sensor A4).
-   **Kontrol Pompa:** Menampilkan status ON/OFF pompa air secara real-time.
-   **Tampilan LCD I2C:** Menampilkan informasi penting (sambutan, status, data sensor) secara bergantian pada LCD 16x2 yang terhubung ke Arduino.
-   **Antarmuka Web Interaktif:** Dashboard modern dan responsif yang dibangun dengan HTML, CSS, dan JavaScript, memungkinkan konfigurasi perangkat, visualisasi data sensor, dan monitoring log serial.
-   **Halaman Informasi & Dokumentasi:** Menyediakan detail tentang tim pengembang dan panduan lengkap tentang arsitektur sistem serta cara penggunaannya.

## Arsitektur Sistem

Sistem ini terdiri dari tiga komponen utama:

1.  **Backend (Python Flask & SocketIO):** Berfungsi sebagai server web, memproses video dari kamera, melakukan deteksi tangan, berkomunikasi dengan Arduino melalui serial, dan mengirim data ke frontend secara *real-time*.
2.  **Frontend (HTML, CSS, JavaScript):** Antarmuka pengguna berbasis web yang menampilkan video feed, status deteksi tangan, data sensor, dan log Arduino. Juga menyediakan kontrol untuk konfigurasi awal.
3.  **Hardware (Arduino, Sensor, Aktuator, LCD):** Perangkat fisik yang berinteraksi dengan lingkungan. Arduino membaca data sensor, mengontrol aktuator, dan berkomunikasi dengan backend.

## Panduan Penggunaan

Untuk menjalankan proyek ini, ikuti langkah-langkah berikut:

### 1. Persiapan Lingkungan

-   Pastikan Anda memiliki **Python 3** dan **pip** terinstal di sistem Anda.
-   Instal **Arduino IDE** dan pastikan *library* `LiquidCrystal_I2C` sudah terinstal (Anda bisa mencarinya melalui Sketch > Include Library > Manage Libraries...).

### 2. Unggah Kode Arduino

1.  Buka file `arduino/arduino_code.ino` di Arduino IDE.
2.  Pastikan Anda telah menginstal *library* `LiquidCrystal_I2C`.
3.  Hubungkan papan Arduino Anda ke komputer.
4.  Pilih Board dan Port yang sesuai di Arduino IDE.
5.  Unggah kode ke Arduino Anda.

### 3. Persiapan Lingkungan Python

1.  Buka terminal atau Command Prompt.
2.  Navigasi ke direktori utama proyek ini (tempat file `app.py` berada):
    ```bash
    cd path/to/your/project/folder
    ```
    (Ganti `path/to/your/project/folder` dengan lokasi sebenarnya)
3.  Buat *virtual environment* (sangat disarankan untuk mengelola dependensi):
    ```bash
    python -m venv .venv
    ```
4.  Aktifkan *virtual environment*:
    -   **Windows:**
        ```bash
        .venv\Scripts\activate
        ```
    -   **macOS/Linux:**
        ```bash
        source .venv/bin/activate
        ```
5.  Instal semua *library* Python yang dibutuhkan:
    ```bash
    pip install opencv-python mediapipe flask flask-socketio pyserial
    ```

### 4. Jalankan Aplikasi

1.  Pastikan Arduino Anda terhubung ke komputer dan kode sudah terunggah.
2.  Dari terminal yang sama (dengan *virtual environment* aktif), jalankan server Flask:
    ```bash
    python app.py
    ```
3.  Buka browser web Anda dan akses alamat:
    ```
    http://127.0.0.1:5000
    ```

### 5. Konfigurasi dan Penggunaan

-   Di halaman awal, pilih port serial Arduino dan kamera yang ingin Anda gunakan dari dropdown.
-   Klik tombol "Mulai Sistem" untuk memulai deteksi tangan dan monitoring sensor.
-   Anda akan melihat video feed, status deteksi tangan, data sensor *real-time*, dan log dari Arduino.
-   Navigasi ke halaman "Tentang Tim Kami" dan "Dokumentasi" melalui tautan di header untuk informasi lebih lanjut.

## Struktur Proyek

```
. (root proyek)
├── app.py              # Backend Python (Flask, SocketIO, OpenCV, MediaPipe, PySerial)
├── arduino/
│   └── arduino_code.ino  # Kode Arduino untuk sensor, aktuator, dan LCD
├── static/
│   ├── css/
│   │   └── style.css     # Gaya CSS untuk seluruh aplikasi
│   ├── js/
│   │   └── main.js       # Skrip JavaScript untuk interaktivitas frontend
│   └── images/           # Folder untuk logo/gambar (jika ada)
└── templates/
    ├── index.html      # Halaman utama dashboard
    ├── team.html       # Halaman informasi tim
    └── documentation.html # Halaman dokumentasi proyek
└── README.md           # File ini
```

## Kontribusi

Jika Anda ingin berkontribusi pada proyek ini, silakan fork repositori dan ajukan *pull request*.
## Thanks to

| [!IZHARDEVELOP](https://github.com/izhardevelop.png?size=100)](https://github.com/izhardevelop) |

## Lisensi

Proyek ini dilisensikan di bawah [Lisensi MIT](https://opensource.org/licenses/MIT).
