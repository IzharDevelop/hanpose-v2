// arduino_code.ino - Kode Arduino untuk Kontrol Hand Pose, Sensor, dan LCD
// Versi Lengkap dan Siap Rilis

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h> // Tambahkan library Servo

// Inisialisasi LCD dengan alamat I2C 0x27 dan 16 kolom, 2 baris
// Alamat I2C bisa berbeda (0x3F atau 0x27). Coba salah satu jika tidak berfungsi.
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Inisialisasi objek Servo
Servo myServo;

// Pin untuk aktuator
const int LED_PIN = 11;    // Untuk cahaya (ON/OFF)
const int PUMP_PIN = 10;   // Untuk pompa air
const int BUZZER_PIN = 9;  // Untuk buzzer pH
const int FAN_PIN = 8;     // Untuk kipas kelembaban
const int SERVO_PIN = 7;   // Pin untuk Servo (misal: untuk kontrol pintu/gerbang)

// Pin untuk sensor
const int LIGHT_SENSOR_PIN = A0;    // Sensor cahaya (LDR)
const int WATER_SENSOR_PIN = A1;    // Sensor level air
const int TDS_SENSOR_PIN = A2;      // Sensor TDS/pH (analog output)
const int HUMIDITY_SENSOR_PIN = A3; // Sensor kelembaban (analog output, bukan DHT)
const int TEMP_SENSOR_PIN = A4;     // Sensor suhu (misal: LM35/TMP36)

// Variabel untuk menyimpan nilai sensor
int lightValue = 0;
int waterValue = 0;
float phValue = 0.0;
int humidityValue = 0; // Ini adalah nilai analog yang dipetakan, bukan % RH sebenarnya dari DHT
float temperatureValue = 0.0; // Nilai suhu dalam Celsius

// Variabel untuk kontrol servo (dari deteksi tangan)
char incomingByte = ' ';
int servoPosition = 0; // Posisi servo saat ini (0 atau 90)

// Variabel untuk LCD display cycling
unsigned long lastLcdUpdate = 0;
const long lcdUpdateInterval = 5000; // Update setiap 5 detik
int lcdScreen = 0;
const int totalLcdScreens = 6; // Jumlah total layar LCD yang akan dirotasi

void setup() {
  Serial.begin(9600); // Pastikan baud rate sama dengan di Python

  // Inisialisasi pin aktuator sebagai OUTPUT
  pinMode(LED_PIN, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);

  // Attach servo ke pin yang ditentukan
  myServo.attach(SERVO_PIN);
  myServo.write(0); // Pastikan servo di posisi awal (0 derajat)

  // Pastikan semua aktuator OFF di awal
  digitalWrite(LED_PIN, LOW);
  digitalWrite(PUMP_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(FAN_PIN, LOW);

  // Inisialisasi LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Selamat Datang!");
  lcd.setCursor(0, 1);
  lcd.print("Hand Pose Control");
  delay(2000);
}

void loop() {
  // Baca semua nilai sensor
  readSensors();

  // Proses perintah dari Python (deteksi tangan)
  if (Serial.available() > 0) {
    incomingByte = Serial.read();
    if (incomingByte == 'O') { // Tangan Terbuka
      myServo.write(90); // Gerakkan servo ke 90 derajat
      servoPosition = 90;
      Serial.println("ARDUINO_LOG: Tangan Terbuka - Servo 90");
    } else if (incomingByte == 'C') { // Tangan Tertutup
      myServo.write(0); // Gerakkan servo ke 0 derajat
      servoPosition = 0;
      Serial.println("ARDUINO_LOG: Tangan Tertutup - Servo 0");
    }
  }

  // Logika kontrol aktuator berdasarkan sensor
  controlActuators();

  // Kirim data sensor ke Python
  sendSensorDataToPython();

  // Update LCD secara bergantian
  updateLcdDisplay();

  delay(100); // Sedikit delay agar tidak terlalu cepat membanjiri serial
}

void readSensors() {
  // Sensor Cahaya (A0) - LDR
  // Nilai akan berkisar 0-1023. Nilai lebih rendah = lebih banyak cahaya.
  lightValue = analogRead(LIGHT_SENSOR_PIN);

  // Sensor Level Air (A1)
  // Nilai akan berkisar 0-1023. Nilai lebih tinggi = level air lebih tinggi (tergantung sensor).
  waterValue = analogRead(WATER_SENSOR_PIN);

  // Sensor TDS/pH (A2) - Asumsi sensor analog yang memberikan nilai mentah
  // Anda perlu kalibrasi sensor pH Anda yang sebenarnya untuk mendapatkan nilai akurat.
  // Contoh pemetaan sederhana: 0-1023 -> 0-14 pH
  int tdsRaw = analogRead(TDS_SENSOR_PIN);
  phValue = map(tdsRaw, 0, 1023, 0, 1400) / 100.0; // Peta ke 0-14, dengan 2 desimal

  // Sensor Kelembaban (A3) - Asumsi sensor kelembaban tanah atau sejenisnya dengan output analog
  // Ini BUKAN sensor DHT11/22. Nilai analog 0-1023 dipetakan ke 0-100%.
  // Anda perlu kalibrasi sensor kelembaban Anda yang sebenarnya.
  int humidityRaw = analogRead(HUMIDITY_SENSOR_PIN);
  humidityValue = map(humidityRaw, 0, 1023, 0, 100); // Peta ke 0-100%

  // Sensor Suhu (A4) - Asumsi LM35/TMP36
  // LM35: 10mV per derajat Celsius. Arduino 5V, 1024 resolusi -> 4.88mV per unit analog.
  // Suhu (C) = (nilai_analog * (5000 / 1024)) / 10
  int tempRaw = analogRead(TEMP_SENSOR_PIN);
  temperatureValue = (tempRaw * (5.0 / 1024.0)) * 100.0; // Konversi ke Celsius
}

void controlActuators() {
  // Kontrol LED/Cahaya (Pin 11)
  // Jika cahaya di bawah ambang batas (gelap), nyalakan LED.
  if (lightValue < 400) { // Ambang batas bisa disesuaikan
    digitalWrite(LED_PIN, HIGH); // LED ON
    // Serial.println("ARDUINO_LOG: LED ON (Cahaya < 400)"); // Nonaktifkan untuk mengurangi spam serial
  } else {
    digitalWrite(LED_PIN, LOW); // LED OFF
    // Serial.println("ARDUINO_LOG: LED OFF (Cahaya >= 400)"); // Nonaktifkan untuk mengurangi spam serial
  }

  // Kontrol Pompa Air (Pin 10)
  // Jika level air di atas ambang batas (misal: tangki penuh), nyalakan pompa.
  if (waterValue > 700) { // Ambang batas bisa disesuaikan
    digitalWrite(PUMP_PIN, HIGH); // Pompa ON
    // Serial.println("ARDUINO_LOG: Pompa ON (Air > 700)"); // Nonaktifkan untuk mengurangi spam serial
  } else {
    digitalWrite(PUMP_PIN, LOW); // Pompa OFF
    // Serial.println("ARDUINO_LOG: Pompa OFF (Air <= 700)"); // Nonaktifkan untuk mengurangi spam serial
  }

  // Kontrol Buzzer pH (Pin 9)
  // Jika nilai pH di luar rentang ideal (misal: terlalu basa), bunyikan buzzer.
  if (phValue > 7.5 || phValue < 6.0) { // Ambang batas bisa disesuaikan
    digitalWrite(BUZZER_PIN, HIGH); // Buzzer ON
    // Serial.println("ARDUINO_LOG: Buzzer ON (pH di luar rentang)"); // Nonaktifkan untuk mengurangi spam serial
  } else {
    digitalWrite(BUZZER_PIN, LOW); // Buzzer OFF
    // Serial.println("ARDUINO_LOG: Buzzer OFF (pH dalam rentang)"); // Nonaktifkan untuk mengurangi spam serial
  }

  // Kontrol Kipas Kelembaban (Pin 8)
  // Jika kelembaban di atas ambang batas, nyalakan kipas.
  if (humidityValue > 60) { // Ambang batas bisa disesuaikan
    digitalWrite(FAN_PIN, HIGH); // Kipas ON
    // Serial.println("ARDUINO_LOG: Kipas ON (Kelembaban > 60%)"); // Nonaktifkan untuk mengurangi spam serial
  } else {
    digitalWrite(FAN_PIN, LOW); // Kipas OFF
    // Serial.println("ARDUINO_LOG: Kipas OFF (Kelembaban <= 60%)"); // Nonaktifkan untuk mengurangi spam serial
  }
}

void sendSensorDataToPython() {
  // Mengirim data dalam format CSV: LIGHT,WATER_LEVEL,PH_WATER,HUMIDITY,TEMPERATURE,PUMP_STATUS
  // Format ini harus sesuai dengan parsing di app.py
  Serial.print("DATA:");
  Serial.print(lightValue);
  Serial.print(",");
  Serial.print(waterValue);
  Serial.print(",");
  Serial.print(phValue, 2); // Kirim dengan 2 angka di belakang koma
  Serial.print(",");
  Serial.print(humidityValue);
  Serial.print(",");
  Serial.print(temperatureValue, 2); // Kirim dengan 2 angka di belakang koma
  Serial.print(",");
  Serial.println(digitalRead(PUMP_PIN) == HIGH ? "ON" : "OFF");
}

void updateLcdDisplay() {
  unsigned long currentMillis = millis();
  if (currentMillis - lastLcdUpdate >= lcdUpdateInterval) {
    lastLcdUpdate = currentMillis;
    lcd.clear();

    switch (lcdScreen) {
      case 0:
        lcd.setCursor(0, 0);
        lcd.print("Selamat Datang!");
        lcd.setCursor(0, 1);
        lcd.print("Hand Pose Control");
        break;
      case 1:
        lcd.setCursor(0, 0);
        lcd.print("Tim Robotic DU");
        lcd.setCursor(0, 1);
        lcd.print("SMK & SMP DU 1");
        break;
      case 2: // Menampilkan data sensor cahaya dan kelembaban
        lcd.setCursor(0, 0);
        lcd.print("Cahaya: ");
        lcd.print(lightValue);
        lcd.setCursor(0, 1);
        lcd.print("Kelembaban: ");
        lcd.print(humidityValue);
        lcd.print("%");
        break;
      case 3: // Menampilkan data sensor pH dan level air
        lcd.setCursor(0, 0);
        lcd.print("pH Air: ");
        lcd.print(phValue, 2);
        lcd.setCursor(0, 1);
        lcd.print("Air: ");
        lcd.print(waterValue);
        lcd.print(" (0-1023)");
        break;
      case 4: // Menampilkan status servo dan aktuator
        lcd.setCursor(0, 0);
        lcd.print("Servo: ");
        lcd.print(servoPosition);
        lcd.print(" deg");
        lcd.setCursor(0, 1);
        lcd.print("LED:"); lcd.print(digitalRead(LED_PIN) == HIGH ? "ON" : "OFF");
        lcd.print(" Pmp:"); lcd.print(digitalRead(PUMP_PIN) == HIGH ? "ON" : "OFF");
        break;
      case 5: // Menampilkan suhu dan status pompa
        lcd.setCursor(0, 0);
        lcd.print("Suhu: ");
        lcd.print(temperatureValue, 1); // Tampilkan suhu dengan 1 desimal
        lcd.print((char)223); // Karakter derajat
        lcd.print("C");
        lcd.setCursor(0, 1);
        lcd.print("Pompa: ");
        lcd.print(digitalRead(PUMP_PIN) == HIGH ? "ON" : "OFF");
        break;
    }
    lcdScreen = (lcdScreen + 1) % totalLcdScreens; // Siklus melalui semua layar
  }
}
