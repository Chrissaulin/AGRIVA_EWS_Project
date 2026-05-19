const API = "http://localhost:8001";
let leafletMap, geojsonLayer, mapData = {};

// ===== NAVIGATION =====
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const page = link.dataset.page;
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById('page-' + page).classList.add('active');
        if (page === 'map' && !leafletMap) initMap();
        if (page === 'map' && leafletMap) leafletMap.invalidateSize();
    });
});

// ===== INIT =====
document.addEventListener("DOMContentLoaded", () => {
    loadEDA();
    loadMapFilters();
    loadPredictProvinces();
    loadForecastProvinces();
    setupPredictForm();
    setupForecastControls();
});

// ===== HOME / EDA =====
async function loadEDA() {
    try {
        const res = await fetch(API + "/api/eda/summary");
        const d = await res.json();
        document.getElementById('statRows').textContent = d.dataset.rows.toLocaleString();
        document.getElementById('statCols').textContent = d.dataset.columns;
        document.getElementById('statProvinces').textContent = d.dataset.total_provinces;
        document.getElementById('statYears').textContent = d.dataset.year_range;
        renderTargetChart(d.target_distribution);
        renderClusterChart(d.cluster_distribution);
        renderMonthlyChart(d.monthly_risk);
        renderProvinceChart(d.province_risk);
        renderFeatureTable(d.feature_stats);
        renderModelInfo(d.model_info);
    } catch (e) { console.error("EDA error:", e); }
}

function renderTargetChart(data) {
    new Chart(document.getElementById('chartTarget'), {
        type: 'doughnut',
        data: { labels: ['Aman', 'Berisiko'], datasets: [{ data: [data.Aman, data.Berisiko], backgroundColor: ['#16a34a', '#ef4444'], borderWidth: 0, borderRadius: 4 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, font: { family: 'Inter', size: 12 } } } } }
    });
}

function renderClusterChart(data) {
    new Chart(document.getElementById('chartCluster'), {
        type: 'bar',
        data: { labels: Object.keys(data), datasets: [{ data: Object.values(data), backgroundColor: ['#3b82f6', '#16a34a', '#f59e0b'], borderRadius: 6, barThickness: 40 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#f3f4f6' } }, x: { grid: { display: false } } } }
    });
}

function renderMonthlyChart(data) {
    const months = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'];
    const values = months.map((_, i) => data[i + 1] || 0);
    new Chart(document.getElementById('chartMonthly'), {
        type: 'bar',
        data: { labels: months, datasets: [{ label: 'Jumlah Berisiko', data: values, backgroundColor: 'rgba(239,68,68,0.7)', borderRadius: 4, barThickness: 28 }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#f3f4f6' } }, x: { grid: { display: false } } } }
    });
}

function renderProvinceChart(data) {
    const entries = Object.entries(data).slice(0, 20);
    new Chart(document.getElementById('chartProvince'), {
        type: 'bar',
        data: { labels: entries.map(e => e[0]), datasets: [{ label: 'Jumlah Berisiko', data: entries.map(e => e[1]), backgroundColor: 'rgba(239,68,68,0.65)', borderRadius: 4, barThickness: 14 }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, grid: { color: '#f3f4f6' } }, y: { grid: { display: false }, ticks: { font: { size: 11 } } } } }
    });
}

function renderFeatureTable(stats) {
    const tbody = document.getElementById('featureTableBody');
    tbody.innerHTML = Object.entries(stats).map(([k, v]) =>
        `<tr><td><strong>${k}</strong></td><td>${v.min}</td><td>${v.max}</td><td>${v.mean}</td><td>${v.std}</td></tr>`
    ).join('');
}

function renderModelInfo(info) {
    const grid = document.getElementById('modelInfoGrid');
    const items = [
        ['Algoritma', info.algorithm], ['Pipeline', info.pipeline],
        ['Jumlah Cluster', info.clusters], ['Target', info.target],
        ['Fitur', info.features_used.length + ' fitur']
    ];
    grid.innerHTML = items.map(([l, v]) =>
        `<div class="model-info-item"><div class="info-label">${l}</div><div class="info-value">${v}</div></div>`
    ).join('');
}

// ===== MAP =====
const PROVINCE_NAME_MAP = {
    "Aceh": "Nangroe A.D.", "Sumatera Utara": "Sumatera Utara", "Sumatera Barat": "Sumatera Barat",
    "Riau": "Riau", "Jambi": "Jambi", "Sumatera Selatan": "Sumatera Selatan", "Bengkulu": "Bengkulu",
    "Lampung": "Lampung", "Kepulauan Bangka Belitung": "Bangka Belitung", "Kepulauan Riau": "Kepulauan-riau",
    "DKI Jakarta": "Dki Jakarta", "Jawa Barat": "Jawa Barat", "Jawa Tengah": "Jawa Tengah",
    "DI Yogyakarta": "D.I. Yogyakarta", "Jawa Timur": "Jawa Timur", "Banten": "Banten", "Bali": "Bali",
    "Nusa Tenggara Barat": "Nusatenggara B.", "Nusa Tenggara Timur": "Nusatenggara T.",
    "Kalimantan Barat": "Kalimantan Barat", "Kalimantan Tengah": "Kalimantan T.",
    "Kalimantan Selatan": "Kalimantan S.", "Kalimantan Timur": "Kalimantan Timur",
    "Sulawesi Utara": "Sulawesi Utara", "Sulawesi Tengah": "Sulawesi Tengah",
    "Sulawesi Selatan": "Sulawesi Selatan", "Sulawesi Tenggara": "Sulawesi Tengg.",
    "Gorontalo": "Gorontalo", "Sulawesi Barat": "Sulawesi Barat",
    "Maluku": "Maluku", "Maluku Utara": "Maluku Utara", "Papua": "Papua", "Papua Barat": "Papua Barat"
};

async function loadMapFilters() {
    try {
        const res = await fetch(API + "/api/map/filters");
        const d = await res.json();
        const sel = document.getElementById('filterYear');
        sel.innerHTML = d.years.map(y => `<option value="${y}">${y}</option>`).join('');
        sel.value = d.years[d.years.length - 1];
    } catch (e) { console.error("Map filters error:", e); }
}

function initMap() {
    leafletMap = L.map('map').setView([-2.5, 118], 5);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO', subdomains: 'abcd', maxZoom: 19
    }).addTo(leafletMap);

    fetch('https://raw.githubusercontent.com/superpikar/indonesia-geojson/master/indonesia-province-simple.json')
        .then(r => r.json())
        .then(data => {
            geojsonLayer = L.geoJSON(data, {
                style: () => ({ color: '#9ca3af', weight: 1, opacity: 0.6, fillOpacity: 0.15, fillColor: '#d1d5db' }),
                onEachFeature: (f, layer) => {
                    layer.bindPopup(`<div class="popup-title">${f.properties.Propinsi}</div><div class="popup-detail">Pilih tahun & bulan untuk melihat status.</div>`);
                    layer.on({ mouseover: e => e.target.setStyle({ weight: 2, fillOpacity: 0.4 }), mouseout: e => geojsonLayer.resetStyle(e.target) });
                }
            }).addTo(leafletMap);
        }).catch(e => console.error("GeoJSON error:", e));

    document.getElementById('btnApplyFilter').addEventListener('click', loadMapData);
}

async function loadMapData() {
    const year = document.getElementById('filterYear').value;
    const month = document.getElementById('filterMonth').value;
    try {
        const res = await fetch(`${API}/api/map/data?year=${year}&month=${month}`);
        const d = await res.json();
        mapData = {};
        (d.provinces || []).forEach(p => { mapData[p.province] = p; });

        if (geojsonLayer) {
            geojsonLayer.eachLayer(layer => {
                const geoName = layer.feature.properties.Propinsi;
                const apiName = PROVINCE_NAME_MAP[geoName] || geoName;
                const info = mapData[apiName];
                if (info) {
                    const isRisk = info.warning_code === 1;
                    layer.setStyle({ fillColor: isRisk ? '#ef4444' : '#16a34a', color: isRisk ? '#dc2626' : '#15803d', fillOpacity: 0.5, weight: 1.5 });
                    layer.setPopupContent(`<div class="popup-title">${geoName}</div><span class="popup-status ${isRisk ? 'danger' : 'safe'}">${info.warning}</span><div class="popup-detail">Cluster: ${info.cluster}<br>Curah Hujan: ${info.avg_rainfall} mm<br>Suhu: ${info.avg_temperature}°C<br>SPI-3: ${info.avg_spi}</div>`);
                } else {
                    layer.setStyle({ fillColor: '#d1d5db', color: '#9ca3af', fillOpacity: 0.15, weight: 1 });
                    layer.setPopupContent(`<div class="popup-title">${geoName}</div><div class="popup-detail">Tidak ada data untuk periode ini.</div>`);
                }
            });
        }
        const panel = document.getElementById('mapInfoPanel');
        const safe = (d.provinces || []).filter(p => p.warning_code === 0).length;
        const risk = (d.provinces || []).filter(p => p.warning_code === 1).length;
        panel.innerHTML = `<p class="map-info-text"><strong>Periode:</strong> ${month}/${year}<br><strong style="color:#16a34a">Aman:</strong> ${safe} provinsi | <strong style="color:#ef4444">Berisiko:</strong> ${risk} provinsi</p>`;
    } catch (e) { console.error("Map data error:", e); }
}

// ===== PREDIKSI =====
async function loadPredictProvinces() {
    try {
        const res = await fetch(API + "/api/predict/provinces");
        const d = await res.json();
        const sel = document.getElementById('predictProvince');
        d.provinces.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.name; opt.textContent = `${p.name} (Cluster ${p.cluster})`;
            opt.dataset.cluster = p.cluster;
            sel.appendChild(opt);
        });
        sel.addEventListener('change', () => {
            const opt = sel.options[sel.selectedIndex];
            document.getElementById('clusterHint').textContent = opt.dataset.cluster !== undefined ? `Cluster ${opt.dataset.cluster} terdeteksi` : '';
        });
    } catch (e) { console.error(e); }
}

function setupPredictForm() {
    document.getElementById('ewsForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('btnPredict');
        const loader = document.getElementById('predictLoader');
        btn.disabled = true; loader.style.display = 'block';
        btn.querySelector('span').textContent = 'Memproses...';

        const form = e.target;
        const body = {
            province: form.province.value,
            Rainfall: parseFloat(form.Rainfall.value),
            SPI_3_months: parseFloat(form.SPI_3_months.value),
            Temperature: parseFloat(form.Temperature.value),
            WSI: parseFloat(form.WSI.value),
            Solar_Radiation: parseFloat(form.Solar_Radiation.value),
            Soil_Moisture: parseFloat(form.Soil_Moisture.value),
            FPAR: parseFloat(form.FPAR.value),
            FPAR_zscore: parseFloat(form.FPAR_zscore.value),
            month_extracted: parseInt(form.month_extracted.value),
        };

        try {
            const res = await fetch(API + "/api/predict/ews", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
            if (!res.ok) { const err = await res.json(); throw new Error(err.detail || "Server error"); }
            const result = await res.json();
            showPredictResult(result);
        } catch (err) {
            alert("Error: " + err.message);
        } finally {
            btn.disabled = false; loader.style.display = 'none';
            btn.querySelector('span').textContent = 'Analisis Prediksi';
        }
    });
}

function showPredictResult(r) {
    document.getElementById('resultPlaceholder').style.display = 'none';
    const content = document.getElementById('resultContent');
    content.classList.remove('hidden');

    const badge = document.getElementById('resultBadge');
    badge.className = 'result-badge ' + (r.prediction === 1 ? 'danger' : 'safe');
    badge.textContent = r.status;

    document.getElementById('resultDetails').innerHTML = `
        <div class="result-detail-row"><span class="label">Provinsi</span><span class="value">${r.province}</span></div>
        <div class="result-detail-row"><span class="label">Cluster</span><span class="value">${r.cluster}</span></div>`;

    document.getElementById('resultProbability').innerHTML = `
        <div class="prob-bar-wrapper"><div class="prob-label"><span style="color:#16a34a">Aman</span><span>${(r.probability.aman * 100).toFixed(1)}%</span></div><div class="prob-bar"><div class="prob-fill safe" style="width:${r.probability.aman * 100}%"></div></div></div>
        <div class="prob-bar-wrapper"><div class="prob-label"><span style="color:#ef4444">Berisiko</span><span>${(r.probability.berisiko * 100).toFixed(1)}%</span></div><div class="prob-bar"><div class="prob-fill danger" style="width:${r.probability.berisiko * 100}%"></div></div></div>`;
}

// ===== FORECASTING =====
let forecastChart = null;

async function loadForecastProvinces() {
    try {
        const res = await fetch(API + "/api/forecast/provinces");
        const d = await res.json();
        const sel = document.getElementById('forecastProvince');
        sel.innerHTML = d.provinces.map(p => `<option value="${p}">${p}</option>`).join('');
    } catch (e) { console.error(e); }
}

function setupForecastControls() {
    const slider = document.getElementById('forecastSteps');
    slider.addEventListener('input', () => { document.getElementById('stepsValue').textContent = slider.value; });
    document.getElementById('btnForecast').addEventListener('click', runForecast);
}

async function runForecast() {
    const province = document.getElementById('forecastProvince').value;
    const variable = document.getElementById('forecastVariable').value;
    const steps = parseInt(document.getElementById('forecastSteps').value);

    document.getElementById('forecastChartBadge').textContent = variable;

    try {
        // Load history
        const hRes = await fetch(`${API}/api/forecast/history?province=${encodeURIComponent(province)}&variable=${encodeURIComponent(variable)}`);
        const hData = await hRes.json();

        // Run forecast
        const fRes = await fetch(`${API}/api/forecast/predict?province=${encodeURIComponent(province)}&steps=${steps}`, { method: "POST" });
        const fData = await fRes.json();

        renderForecastChart(hData.data, fData.predictions, variable);
        renderForecastTable(fData.predictions);
    } catch (e) { console.error("Forecast error:", e); alert("Error: " + e.message); }
}

function renderForecastChart(history, predictions, variable) {
    const ctx = document.getElementById('chartForecast');
    if (forecastChart) forecastChart.destroy();

    const histLabels = history.map(h => h.date);
    const histValues = history.map(h => h.value);
    const predLabels = predictions.map(p => p.date);
    const predValues = predictions.map(p => p.predicted[variable] || 0);

    const allLabels = [...histLabels, ...predLabels];
    const histDataset = [...histValues, ...Array(predLabels.length).fill(null)];
    const predDataset = [...Array(histLabels.length - 1).fill(null), histValues[histValues.length - 1], ...predValues];

    forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allLabels,
            datasets: [
                { label: 'Historis', data: histDataset, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.08)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 },
                { label: 'Forecast', data: predDataset, borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)', fill: true, tension: 0.3, pointRadius: 3, borderWidth: 2, borderDash: [6, 3] }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { legend: { position: 'top', labels: { usePointStyle: true, font: { family: 'Inter', size: 12 } } } },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 15, font: { size: 10 } } },
                y: { grid: { color: '#f3f4f6' }, ticks: { font: { size: 11 } } }
            }
        }
    });
}

function renderForecastTable(predictions) {
    const card = document.getElementById('forecastTableCard');
    card.style.display = 'block';
    const tbody = document.getElementById('forecastTableBody');
    tbody.innerHTML = predictions.map(p => {
        const d = p.predicted;
        return `<tr>
            <td><strong>${p.step}</strong></td><td>${p.date}</td>
            <td>${d['Rainfall']?.toFixed(2) || '-'}</td>
            <td>${d['SPI - 3 months']?.toFixed(3) || '-'}</td>
            <td>${d['Temperature']?.toFixed(2) || '-'}</td>
            <td>${d['Water Satisfaction Index (WSI)']?.toFixed(2) || '-'}</td>
            <td>${d['Solar Radiation']?.toFixed(0) || '-'}</td>
            <td>${d['Soil Moisture (gapfilled historical time series)']?.toFixed(4) || '-'}</td>
            <td>${d['FPAR']?.toFixed(2) || '-'}</td>
            <td>${d['FPAR - zscore']?.toFixed(3) || '-'}</td>
        </tr>`;
    }).join('');
}
