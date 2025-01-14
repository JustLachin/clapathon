// DOM Elements
const cameraToggle = document.getElementById('cameraToggle');
const settingsBtn = document.getElementById('settingsBtn');
const helpBtn = document.getElementById('helpBtn');
const volumeControl = document.getElementById('volumeControl');
const volumeValue = document.getElementById('volumeValue');
const cameraStatus = document.getElementById('cameraStatus');
const statusText = document.getElementById('statusText');
const gestureText = document.getElementById('gestureText');
const settingsModal = document.getElementById('settingsModal');
const saveSettings = document.getElementById('saveSettings');
const gestureCount = document.getElementById('gestureCount');
const screenshotCount = document.getElementById('screenshotCount');
const uptime = document.getElementById('uptime');
const cameraSelect = document.getElementById('cameraSelect');

// PyQt Bridge object will be injected as 'bridge'
let gestures = 0;
let screenshots = 0;
let startTime = new Date();

// Event Listeners
cameraToggle.addEventListener('click', () => {
    if (cameraSelect.value) {
        bridge.toggleCamera();
    } else {
        updateGestureText('Lütfen önce bir kamera seçin!');
        settingsModal.style.display = 'flex';
    }
});

cameraSelect.addEventListener('change', () => {
    if (cameraSelect.value) {
        bridge.selectCamera(parseInt(cameraSelect.value));
    }
});

settingsBtn.addEventListener('click', () => {
    settingsModal.style.display = 'flex';
});

helpBtn.addEventListener('click', () => {
    bridge.showHelp();
});

volumeControl.addEventListener('input', (e) => {
    const value = e.target.value;
    volumeValue.textContent = `${value}%`;
    bridge.setVolume(value);
});

saveSettings.addEventListener('click', () => {
    const settings = {
        resolution: document.getElementById('resolution').value,
        fpsLimit: parseInt(document.getElementById('fpsLimit').value),
        sensitivity: parseInt(document.getElementById('sensitivity').value),
        confidenceThreshold: parseInt(document.getElementById('confidenceThreshold').value),
        imageQuality: document.getElementById('imageQuality').value,
        imageFilter: document.getElementById('imageFilter').value
    };
    bridge.saveSettings(JSON.stringify(settings));
    settingsModal.style.display = 'none';
});

// Close modal when clicking outside
settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) {
        settingsModal.style.display = 'none';
    }
});

// Update camera list
function updateCameraList(cameras) {
    console.log('Kamera listesi güncelleniyor:', cameras);
    
    // Mevcut seçili kamerayı kaydet
    const currentCamera = cameraSelect.value;
    
    // Listeyi temizle
    cameraSelect.innerHTML = '<option value="">Kamera Seç...</option>';
    
    // Kameraları ekle
    if (cameras && cameras.length > 0) {
        cameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = camera.id;
            option.textContent = `${camera.name} (${camera.resolution.width}x${camera.resolution.height})`;
            cameraSelect.appendChild(option);
        });
        
        // Önceki kamerayı seç (eğer hala listede varsa)
        if (currentCamera && cameras.some(c => c.id.toString() === currentCamera)) {
            cameraSelect.value = currentCamera;
        }
        
        updateGestureText(`${cameras.length} kamera bulundu`);
    } else {
        updateGestureText('Kamera bulunamadı! Lütfen kamera bağlantınızı kontrol edin.');
    }
}

// Update camera status
function updateCameraStatus(isActive) {
    cameraStatus.style.color = isActive ? '#4CAF50' : '#F44336';
    statusText.textContent = isActive ? 'Kamera Aktif' : 'Kamera Kapalı';
    cameraToggle.innerHTML = `<i class="fas fa-video${isActive ? '-slash' : ''}"></i>
                             <span>Kamera${isActive ? 'yı Kapat' : 'yı Aç'}</span>`;
    
    // Overlay'i güncelle
    const overlay = document.getElementById('gestureOverlay');
    if (isActive) {
        overlay.classList.remove('active');
    } else {
        overlay.classList.add('active');
    }
}

// Update gesture text
function updateGestureText(text) {
    const overlay = document.getElementById('gestureOverlay');
    gestureText.textContent = text;
    
    // Önemli mesajlar için overlay'i göster
    if (text.includes('algılandı') || text.includes('hata') || text.includes('bulunamadı')) {
        overlay.classList.add('active');
        setTimeout(() => overlay.classList.remove('active'), 3000);
        
        if (text.includes('algılandı')) {
            gestures++;
            gestureCount.textContent = gestures;
        }
    }
}

// Update screenshot count
function updateScreenshotCount() {
    screenshots++;
    screenshotCount.textContent = screenshots;
    
    // Screenshot alındığında overlay'i göster
    const overlay = document.getElementById('gestureOverlay');
    overlay.classList.add('active');
    setTimeout(() => overlay.classList.remove('active'), 2000);
}

// Update uptime
function updateUptime() {
    const now = new Date();
    const diff = now - startTime;
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    uptime.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

// Start uptime counter
setInterval(updateUptime, 1000);

// Expose functions for PyQt bridge
window.updateCameraStatus = updateCameraStatus;
window.updateGestureText = updateGestureText;
window.updateScreenshotCount = updateScreenshotCount;
window.updateCameraList = updateCameraList; 