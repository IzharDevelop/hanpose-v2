const socket = io.connect('http://127.0.0.1:5000');

// --- Elemen UI ---
const configSection = document.getElementById('configSection');
const operationalSection = document.getElementById('operationalSection');
const serialPortSelect = document.getElementById('serialPortSelect');
const baudRateInput = document.getElementById('baudRateInput');
const cameraSelect = document.getElementById('cameraSelect');
const previewCameraFeed = document.getElementById('previewCameraFeed');
const submitConfigBtn = document.getElementById('submitConfigBtn');
const mainVideoFeed = document.getElementById('mainVideoFeed');
const handStatusDisplay = document.getElementById('handStatusDisplay');
        const lightValue = document.getElementById('lightValue');
        const phValue = document.getElementById('phValue');
        const waterLevelValue = document.getElementById('waterLevelValue'); // New
        const pumpStatus = document.getElementById('pumpStatus'); // New
        const humValue = document.getElementById('humValue'); // Existing, but moved for clarity
        const tempValue = document.getElementById('tempValue'); // New
const arduinoConsole = document.getElementById('arduinoConsole');
const tempGauge = document.getElementById('tempGauge');
const humGauge = document.getElementById('humGauge');
const arduinoStatusIndicator = document.getElementById('arduinoStatusIndicator');
const serialWrapper = document.getElementById('serial-wrapper');
const cameraWrapper = document.getElementById('camera-wrapper');

// --- Fungsi UI Helper ---

/** Membuat notifikasi toast */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-times-circle' : 'fa-info-circle'}"></i> ${message}`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.5s forwards';
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

/** Mengupdate gauge visual */
function updateGauge(element, value, max = 100) {
    const percentage = Math.min(Math.max(value, 0), max) / max;
    const deg = percentage * 360;
    element.style.background = `conic-gradient(var(--primary-accent) ${deg}deg, var(--bg-input) ${deg}deg)`;
}

/** Mengisi dropdown port serial */
function populateSerialPorts(ports) {
    serialWrapper.classList.remove('loading');
    serialPortSelect.innerHTML = '';
    if (ports.length === 0) {
        serialPortSelect.innerHTML = `<option value="">${translations.no_port}</option>`;
    } else {
        ports.forEach(port => {
            const option = document.createElement('option');
            option.value = port.port;
            option.innerText = `${port.port} (${port.description || 'N/A'})`;
            serialPortSelect.appendChild(option);
        });
    }
}

/** Mengisi dropdown kamera */
function populateCameras(cameras) {
    cameraWrapper.classList.remove('loading');
    cameraSelect.innerHTML = '';
    if (cameras.length === 0) {
        cameraSelect.innerHTML = `<option value="">${translations.no_camera}</option>`;
    } else {
        cameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = camera.id;
            option.innerText = camera.name;
            cameraSelect.appendChild(option);
        });
        if (cameras.length > 0) {
            previewCameraFeed.src = `/preview_camera/${cameras[0].id}`;
        }
    }
}

/** Menampilkan bagian konfigurasi */
function showConfigSection() {
    configSection.classList.remove('hidden');
    operationalSection.classList.add('hidden');
}

/** Menampilkan bagian operasional */
function showOperationalSection() {
    configSection.classList.add('hidden');
    operationalSection.classList.remove('hidden');
}

// --- Event Listeners ---
cameraSelect.addEventListener('change', () => {
    if (cameraSelect.value) {
        previewCameraFeed.src = `/preview_camera/${cameraSelect.value}`;
    }
});

submitConfigBtn.addEventListener('click', () => {
    const selectedPort = serialPortSelect.value;
    const baudRate = parseInt(baudRateInput.value);
    const selectedCameraId = cameraSelect.value;

    if (!selectedPort || !selectedCameraId) {
        showToast(translations.select_port_camera_first, 'error');
        return;
    }
    showToast(translations.initializing_system, 'info');
    socket.emit('start_system', {
        'port': selectedPort,
        'baudRate': baudRate,
        'cameraId': selectedCameraId
    });
});

// --- Socket.IO Handlers ---
socket.on('connect', () => {
    showToast(translations.connected_to_server, 'success');
    serialWrapper.classList.add('loading');
    cameraWrapper.classList.add('loading');
});
socket.on('disconnect', () => {
    showToast(translations.disconnected_from_server, 'error');
    showConfigSection();
    arduinoStatusIndicator.classList.remove('connected', 'error');
});
socket.on('connect_error', () => showToast(translations.failed_to_connect_to_python_server, 'error'));

socket.on('available_ports', populateSerialPorts);
socket.on('available_cameras', populateCameras);

socket.on('arduino_status', data => {
    showToast(data.message, data.success ? 'success' : 'error');
    arduinoStatusIndicator.classList.toggle('connected', data.success);
    arduinoStatusIndicator.classList.toggle('error', !data.success);
});

socket.on('camera_status', data => {
    showToast(data.message, data.success ? 'success' : 'error');
    if (!data.success) mainVideoFeed.src = '';
});

socket.on('system_started', data => {
    if (data.success) {
        showOperationalSection();
        showToast(translations.system_started_successfully, 'success');

    } else {
        showToast(translations.failed_to_start_system, 'error');
    }
});

socket.on('video_frame', data => mainVideoFeed.src = data.image);
socket.on('hand_status', data => {
    let statusText = data.status;
    if (statusText.includes('Terbuka')) {
        statusText = statusText.replace('Terbuka', translations.open);
    } else if (statusText.includes('Tertutup')) {
        statusText = statusText.replace('Tertutup', translations.closed);
    } else if (statusText.includes('Tidak ada tangan terdeteksi.')) {
        statusText = translations.not_detected;
    }
    handStatusDisplay.innerText = statusText;
});

        socket.on('sensor_data', data => {
            const light = parseFloat(data.light) || 0;
            const water = parseFloat(data.water_level) || 0;
            const ph = parseFloat(data.ph_water) || 0;
            const humidity = parseFloat(data.humidity) || 0;
            const temperature = parseFloat(data.temperature) || 0;
            const pump_status = data.pump_status; // String 'ON' or 'OFF'
            
            lightValue.innerText = `${data.light} Lux`;
            waterLevelValue.innerText = `${data.water_level} (0-1023)`;
            phValue.innerText = `${data.ph_water}`;
            humValue.innerText = `${data.humidity}%`; // Updated to humValue
            tempValue.innerText = `${data.temperature}°C`; // New
            pumpStatus.innerText = pump_status; // New

            // Update gauge untuk kelembaban
            updateGauge(humGauge, humidity, 100); // Asumsi kelembaban maks 100%
            // Update gauge untuk suhu
            updateGauge(tempGauge, temperature, 50); // Asumsi suhu maks 50°C, sesuaikan jika perlu
        });

socket.on('arduino_log_line', data => {
    const logLine = document.createElement('div');
    logLine.innerText = data.line;
    arduinoConsole.appendChild(logLine);
    arduinoConsole.scrollTop = arduinoConsole.scrollHeight;
});

// --- Inisialisasi ---
showConfigSection();
