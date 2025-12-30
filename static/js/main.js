// Socket.IO bağlantısı
const socket = io({
    transports: ['websocket', 'polling'] // WebSocket öncelikli
});

socket.on('connect', () => {
    console.log('Socket Connected!', socket.id);
    document.getElementById('systemStatus').textContent = 'Sistem Bağlı';
    document.getElementById('systemStatus').style.color = '#22c55e';
});

socket.on('connect_error', (error) => {
    console.error('Connection Error:', error);
    document.getElementById('systemStatus').textContent = 'Bağlantı Hatası!';
    document.getElementById('systemStatus').style.color = '#ef4444';
});

let chart = null;

// Sayfa yüklendiğinde
document.addEventListener('DOMContentLoaded', function () {
    console.log('DOM Loaded, Initializing...');
    initializeChart();
    loadStatistics();
    loadRecentDetections();
    loadHourlyData();

    // Butonlar
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');

    // Buton eventlerini manuel bağlayalım (Garanti olsun)
    const btnStart = document.getElementById('startBtn');
    if (btnStart) {
        btnStart.onclick = function (e) {
            e.preventDefault(); // Varsayılan davranışı engelle
            startDetection();
        };
    }

    const btnStop = document.getElementById('stopBtn');
    if (btnStop) {
        btnStop.onclick = function (e) {
            e.preventDefault();
            stopDetection();
        };
    }

    // Otomatik yenileme
    setInterval(loadStatistics, 10000); // Her 10 saniyede
    setInterval(loadRecentDetections, 15000); // Her 15 saniyede
});

// Socket.IO events (Canlı Sayaç)
socket.on('detection_update', function (data) {
    const counterElement = document.getElementById('currentCount');
    if (counterElement) {
        counterElement.textContent = data.person_count;

        // Basit animasyon efekti
        counterElement.style.transform = "scale(1.2)";
        setTimeout(() => {
            counterElement.style.transform = "scale(1)";
        }, 200);
    }
});

socket.on('status_response', function (data) {
    console.log('Status update:', data);
    // UI bildirimi eklenebilir
});

function startDetection() {
    console.log('Sending start command via Socket...');
    socket.emit('start_detection');
    const videoFeed = document.getElementById('videoFeed');
    if (videoFeed) videoFeed.style.opacity = '1';
}

function stopDetection() {
    console.log('Sending stop command via Socket...');
    socket.emit('stop_detection');
    const videoFeed = document.getElementById('videoFeed');
    if (videoFeed) videoFeed.style.opacity = '0.5';
}

function loadStatistics() {
    fetch('/api/statistics?hours=24')
        .then(response => response.json())
        .then(data => {
            updateElement('totalDetections', data.total_detections);
            updateElement('avgPersons', data.avg_persons);
            updateElement('maxPersons', data.max_persons);
            // minPersons artık UI'da yok, ama API dönüyor olabilir
        });
}

function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function loadRecentDetections() {
    fetch('/api/recent_detections?limit=10')
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('detectionsTable');
            if (!tbody) return;

            tbody.innerHTML = '';

            data.forEach(det => {
                const row = tbody.insertRow();
                const date = new Date(det.timestamp);

                // Güven skoru renklendirme
                const confidence = det.confidence ? det.confidence.toFixed(2) : 0;
                let confColor = '#ef4444'; // Red
                if (confidence > 0.7) confColor = '#22c55e'; // Green
                else if (confidence > 0.4) confColor = '#f97316'; // Orange

                row.innerHTML = `
                    <td>${date.toLocaleString('tr-TR')}</td>
                    <td style="font-weight: bold;">${det.person_count}</td>
                    <td><span style="color: ${confColor}; font-weight: 500;">%${(confidence * 100).toFixed(0)}</span></td>
                `;
            });
        });
}

function loadHourlyData() {
    fetch('/api/hourly_data?hours=24')
        .then(response => response.json())
        .then(data => {
            const labels = data.map(d => new Date(d.hour).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }));
            const avgCounts = data.map(d => d.avg_count);
            const maxCounts = data.map(d => d.max_count);

            updateChart(labels, avgCounts, maxCounts);
        });
}

function initializeChart() {
    const ctx = document.getElementById('hourlyChart').getContext('2d');

    // Dark Theme Colors
    const gridColor = 'rgba(255, 255, 255, 0.1)';
    const textColor = 'rgba(148, 163, 184, 1)'; // Slate 400

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Ortalama',
                data: [],
                borderColor: '#3b82f6', // Blue 500
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }, {
                label: 'Maksimum',
                data: [],
                borderColor: '#f97316', // Orange 500
                backgroundColor: 'rgba(249, 115, 22, 0.0)',
                borderWidth: 2,
                borderDash: [5, 5],
                tension: 0.4,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: textColor }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: gridColor },
                    ticks: { color: textColor }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: textColor }
                }
            }
        }
    });
}

function updateChart(labels, avgData, maxData) {
    if (chart) {
        chart.data.labels = labels;
        chart.data.datasets[0].data = avgData;
        chart.data.datasets[1].data = maxData;
        chart.update();
    }
}