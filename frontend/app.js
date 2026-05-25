const API = "http://localhost:8001";
let leafletMap, geojsonLayer, mapData = {};

// ===== TIER 2: FRONTEND LOGIC ENGINEER =====

// ===== NAVIGATION =====
document.querySelectorAll('.nav-link, .nav-page-link, .hero-buttons a, .benefit-section a, .footer-links a').forEach(link => {
    link.addEventListener('click', (e) => {
        if(link.hasAttribute('data-page')) {
            e.preventDefault();
            switchPage(link.dataset.page);
        }
    });
});

window.switchPage = function(page) {
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    
    // Find nav link corresponding to the page and set active
    const navLink = document.querySelector(`.nav-link[data-page="${page}"]`);
    if(navLink) navLink.classList.add('active');

    // Handle dropdown active state
    if(page === 'eda' || page === 'model' || page === 'database') {
        const dropdown = document.getElementById('navbarDropdown');
        if(dropdown) dropdown.classList.add('active');
    }

    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    
    if (page === 'map' && !leafletMap) initMap();
    if (page === 'map' && leafletMap) setTimeout(() => leafletMap.invalidateSize(), 200);
    if (page === 'eda') loadEDA();
}

// ===== INIT =====
document.addEventListener("DOMContentLoaded", () => {
    loadMapFilters();
    loadPredictProvinces();
    loadForecastProvinces();
    setupPredictForm();
    setupForecastControls();
    
    // Mock features toggle
    document.querySelectorAll('.feature-toggle').forEach(t => {
        t.addEventListener('change', () => {
            const checkedCount = document.querySelectorAll('.feature-toggle:checked').length;
            const mockRecall = 85.4 - ((8 - checkedCount) * 2.3);
            document.getElementById('mockRecall').textContent = Math.max(0, mockRecall).toFixed(1) + "%";
        });
    });
});

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
        if(d.years) {
            sel.innerHTML = d.years.map(y => `<option value="${y}">${y}</option>`).join('');
            sel.value = d.years[d.years.length - 1];
        }
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
                    layer.bindPopup(`<div class="fw-bold mb-1">${f.properties.Propinsi}</div><div class="small text-muted">Klik terapkan filter untuk melihat status.</div>`);
                    layer.on({ mouseover: e => e.target.setStyle({ weight: 2, fillOpacity: 0.4 }), mouseout: e => geojsonLayer.resetStyle(e.target) });
                }
            }).addTo(leafletMap);
            loadMapData(); // Auto load when map init
        }).catch(e => console.error("GeoJSON error:", e));

    document.getElementById('btnApplyFilter').addEventListener('click', loadMapData);
}

// ===== TIER 3: INTEGRATION ARCHITECT =====

async function loadMapData() {
    const btn = document.getElementById('btnApplyFilter');
    if(!btn) return;
    const originalText = btn.textContent;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Memuat...';
    btn.disabled = true;

    const year = document.getElementById('filterYear').value;
    const month = document.getElementById('filterMonth').value;
    const filterCluster = document.getElementById('filterCluster').value;
    const filterStatus = document.getElementById('filterStatus').value;

    try {
        const res = await fetch(`${API}/api/map/data?year=${year}&month=${month}`);
        const d = await res.json();
        mapData = {};
        (d.provinces || []).forEach(p => { mapData[p.province] = p; });

        let countSafe = 0, countRisk = 0;
        let sumTemp = 0, countTemp = 0;

        if (geojsonLayer) {
            geojsonLayer.eachLayer(layer => {
                const geoName = layer.feature.properties.Propinsi;
                const apiName = PROVINCE_NAME_MAP[geoName] || geoName;
                const info = mapData[apiName];
                
                let showLayer = true;

                if (info) {
                    const isRisk = info.warning_code === 1;
                    const clusterStr = info.cluster.toString();

                    // Apply Controls Filter
                    if(filterCluster !== 'all' && clusterStr !== filterCluster) showLayer = false;
                    if(filterStatus === 'aman' && isRisk) showLayer = false;
                    if(filterStatus === 'risiko' && !isRisk) showLayer = false;

                    if(showLayer) {
                        layer.setStyle({ 
                            fillColor: isRisk ? '#ef4444' : '#16a34a', 
                            color: isRisk ? '#dc2626' : '#15803d', 
                            fillOpacity: 0.8, // Make it look more choropleth
                            weight: 1.5 
                        });
                        layer.setPopupContent(`<div class="fw-bold mb-1">${geoName}</div><span class="badge ${isRisk ? 'bg-danger' : 'bg-success'} mb-2">${info.warning}</span><div class="small text-muted">Cluster: ${info.cluster}<br>Curah Hujan: ${info.avg_rainfall} mm<br>Suhu: ${info.avg_temperature}°C<br>SPI-3: ${info.avg_spi}</div>`);
                        
                        if(isRisk) countRisk++;
                        else countSafe++;

                        sumTemp += info.avg_temperature;
                        countTemp++;
                    } else {
                        // Hidden by filter
                        layer.setStyle({ fillColor: '#e5e7eb', color: '#d1d5db', fillOpacity: 0.2, weight: 1 });
                        layer.setPopupContent(`<div class="fw-bold mb-1">${geoName}</div><div class="small text-muted">Dikecualikan oleh filter.</div>`);
                    }
                } else {
                    layer.setStyle({ fillColor: '#f3f4f6', color: '#e5e7eb', fillOpacity: 0.3, weight: 1 });
                    layer.setPopupContent(`<div class="fw-bold mb-1">${geoName}</div><div class="small text-muted">Tidak ada data untuk periode ini.</div>`);
                }
            });
        }
        
        // Update Stats UI
        document.getElementById('statMapSafe').textContent = countSafe;
        document.getElementById('statMapRisk').textContent = countRisk;
        document.getElementById('statMapTemp').textContent = countTemp > 0 ? (sumTemp/countTemp).toFixed(2) + "°C" : "-";

    } catch (e) { 
        console.error("Map data error:", e);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ===== PREDIKSI / SIMULATOR =====
let predictGaugeChart = null;

async function loadPredictProvinces() {
    try {
        const res = await fetch(API + "/api/predict/provinces");
        const d = await res.json();
        const sel = document.getElementById('predictProvince');
        if(d.provinces) {
            d.provinces.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.name; opt.textContent = `${p.name}`;
                opt.dataset.cluster = p.cluster;
                sel.appendChild(opt);
            });
        }
    } catch (e) { console.error(e); }
}

function setupPredictForm() {
    const sliders = ['rainfall', 'spi3', 'temperature', 'wsi', 'solarRad', 'soilMoisture', 'fpar', 'fparZ'];
    sliders.forEach(id => {
        const el = document.getElementById(id);
        const valEl = document.getElementById(id + 'Val');
        if(el && valEl) {
            el.addEventListener('input', (e) => {
                valEl.textContent = e.target.value;
            });
        }
    });

    document.getElementById('ewsForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('btnPredict');
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>MEMPROSES...';

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
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles me-2"></i>JALANKAN SIMULASI DETEKSI >';
        }
    });
}

function showPredictResult(r) {
    document.getElementById('resultPlaceholder').classList.add('d-none');
    const content = document.getElementById('resultContent');
    content.classList.remove('d-none');

    const isRisk = r.prediction === 1;
    const badge = document.getElementById('resultBadge');
    
    // Set Badge
    badge.className = 'd-inline-block px-5 py-2 rounded-3 fs-3 fw-bold shadow-sm mb-4 border border-2 ';
    if(isRisk) {
        badge.className += 'bg-danger text-white border-danger';
        badge.textContent = 'AWAS: BERISIKO';
    } else {
        badge.className += 'bg-success text-white border-success';
        badge.textContent = 'AMAN';
    }

    document.getElementById('resProv').textContent = r.province;
    document.getElementById('resCluster').textContent = `Cluster ${r.cluster}`;

    // Render Gauge Chart for Berisiko Probability
    const probRisk = r.probability.berisiko * 100;
    renderGaugeChart(probRisk);
    
    // Description text
    const desc = document.getElementById('resDescription');
    const probTextSpan = document.getElementById('resProbText');
    
    if(isRisk) {
        desc.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-danger me-1"></i> Indikator berada dalam zona <strong>RAWAN</strong>. Peluang bahaya mencapai <strong>${probRisk.toFixed(1)}%</strong>, melampaui ambang batas model. Disarankan segera merencanakan mitigasi kekeringan dan pengaturan pengairan di wilayah ini.`;
    } else {
        desc.innerHTML = `<i class="fa-solid fa-circle-check text-success me-1"></i> Indikator berada dalam zona <strong>STABIL</strong>. Peluang bahaya (<strong>${probRisk.toFixed(1)}%</strong>) berada di bawah ambang batas bahaya (Threshold). Kondisi diprediksi mendukung pertumbuhan pangan dengan baik.`;
    }
}

function renderGaugeChart(probabilityValue) {
    const ctx = document.getElementById('gaugeChart');
    if(predictGaugeChart) predictGaugeChart.destroy();
    
    const valueEl = document.getElementById('gaugeValue');
    valueEl.textContent = probabilityValue.toFixed(1) + '%';
    
    if(probabilityValue > 50) valueEl.className = 'fw-bold mb-0 text-danger';
    else valueEl.className = 'fw-bold mb-0 text-success';

    predictGaugeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Peluang Bahaya', 'Aman'],
            datasets: [{
                data: [probabilityValue, 100 - probabilityValue],
                backgroundColor: [
                    probabilityValue > 50 ? '#ef4444' : '#10b981', 
                    '#e5e7eb'
                ],
                borderWidth: 0,
                circumference: 180,
                rotation: 270
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '80%',
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            animation: { animateRotate: true, animateScale: false }
        }
    });
}

// ===== FORECASTING =====
let forecastChart = null;

async function loadForecastProvinces() {
    try {
        const res = await fetch(API + "/api/forecast/provinces");
        const d = await res.json();
        const sel = document.getElementById('forecastProvince');
        if(d.provinces) {
            sel.innerHTML = d.provinces.map(p => `<option value="${p}">${p}</option>`).join('');
        }
    } catch (e) { console.error(e); }
}

function setupForecastControls() {
    const slider = document.getElementById('forecastSteps');
    slider.addEventListener('input', () => { 
        document.getElementById('stepsValue').textContent = `${slider.value} Bulan`; 
    });
    document.getElementById('btnForecast').addEventListener('click', runForecast);
}

async function runForecast() {
    const btn = document.getElementById('btnForecast');
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Memproses...';
    btn.disabled = true;

    const province = document.getElementById('forecastProvince').value;
    const variable = document.getElementById('forecastVariable').value;
    const steps = parseInt(document.getElementById('forecastSteps').value);

    const varSelect = document.getElementById('forecastVariable');
    document.getElementById('forecastChartBadge').textContent = varSelect.options[varSelect.selectedIndex].text;

    try {
        const hRes = await fetch(`${API}/api/forecast/history?province=${encodeURIComponent(province)}&variable=${encodeURIComponent(variable)}`);
        if(!hRes.ok) throw new Error("Gagal mengambil data historis");
        const hData = await hRes.json();

        const fRes = await fetch(`${API}/api/forecast/predict?province=${encodeURIComponent(province)}&steps=${steps}`, { method: "POST" });
        if(!fRes.ok) throw new Error("Gagal menjalankan forecast");
        const fData = await fRes.json();

        renderForecastChart(hData.data, fData.predictions, variable);
        renderForecastTable(fData.predictions);
    } catch (e) { 
        console.error("Forecast error:", e); 
        alert("Error: " + e.message); 
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

function renderForecastChart(history, predictions, variable) {
    const ctx = document.getElementById('chartForecast');
    if (forecastChart) forecastChart.destroy();

    const histLabels = history.map(h => h.date);
    const histValues = history.map(h => h.value);
    const predLabels = predictions.map(p => p.date || `Bulan ${p.step}`);
    const predValues = predictions.map(p => p.predicted[variable] || 0);

    const allLabels = [...histLabels, ...predLabels];
    const histDataset = [...histValues, ...Array(predLabels.length).fill(null)];
    const predDataset = [...Array(histLabels.length - 1).fill(null), histValues[histValues.length - 1], ...predValues];

    forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allLabels,
            datasets: [
                { 
                    label: 'Data Historis', 
                    data: histDataset, 
                    borderColor: '#3b5d50', 
                    backgroundColor: 'rgba(59, 93, 80, 0.1)', 
                    fill: true, 
                    tension: 0.3, 
                    pointRadius: 0, 
                    borderWidth: 2 
                },
                { 
                    label: 'Proyeksi AI (Forecast)', 
                    data: predDataset, 
                    borderColor: '#f9bf29', 
                    backgroundColor: 'rgba(249, 191, 41, 0.1)', 
                    fill: true, 
                    tension: 0.3, 
                    pointRadius: 4, 
                    pointBackgroundColor: '#ffffff',
                    borderWidth: 3, 
                    borderDash: [6, 4] 
                }
            ]
        },
        options: {
            responsive: true, 
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: { 
                legend: { position: 'top', labels: { usePointStyle: true, font: { family: 'Inter', size: 13, weight: 'bold' } } },
                tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', titleFont: { size: 13, family: 'Inter' }, bodyFont: { size: 13, family: 'Inter' }, padding: 10, cornerRadius: 8 }
            },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 12, font: { size: 11 } } },
                y: { grid: { color: '#e5e7eb' }, ticks: { font: { size: 12 } } }
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
            <td class="fw-bold">Bulan ${p.step}</td>
            <td>${p.date || '-'}</td>
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

// ===== EDA (Informasi Sistem) =====
let edaLoaded = false;
let edaCharts = {};
let edaMap = null;
let edaGeojson = null;

async function loadEDA() {
    if(edaLoaded) return;
    
    // Init Map
    edaMap = L.map('edaMap').setView([-2.5, 118], 5);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(edaMap);

    fetch('https://raw.githubusercontent.com/superpikar/indonesia-geojson/master/indonesia-province-simple.json')
        .then(r => r.json())
        .then(data => {
            edaGeojson = L.geoJSON(data, {
                style: () => ({ color: '#9ca3af', weight: 1, opacity: 0.6, fillOpacity: 0.3, fillColor: '#3b82f6' }),
                onEachFeature: (f, layer) => {
                    layer.bindPopup(`<div class="fw-bold">${f.properties.Propinsi}</div>`);
                }
            }).addTo(edaMap);
            loadEdaDashboard(); 
        });

    document.getElementById('btnEdaApply').addEventListener('click', loadEdaDashboard);
    edaLoaded = true;
}

async function loadEdaDashboard() {
    const prov = document.getElementById('edaFilterProvince').value || 'All';
    const year = document.getElementById('edaFilterYear').value || 'All';

    try {
        const res = await fetch(`${API}/api/eda/dashboard?province=${encodeURIComponent(prov)}&year=${encodeURIComponent(year)}`);
        const d = await res.json();
        
        if(d.error) return alert(d.error);

        // Populate filters if empty
        const provSel = document.getElementById('edaFilterProvince');
        if(provSel.options.length <= 1) {
            d.provinces.forEach(p => provSel.insertAdjacentHTML('beforeend', `<option value="${p}">${p}</option>`));
            d.years.forEach(y => document.getElementById('edaFilterYear').insertAdjacentHTML('beforeend', `<option value="${y}">${y}</option>`));
        }

        // KPIs
        document.getElementById('edaKpiRain').textContent = d.kpis.avg_rainfall + " mm";
        document.getElementById('edaKpiTemp').textContent = d.kpis.avg_temperature + " °C";
        document.getElementById('edaKpiStatus').textContent = d.kpis.dominant_status;
        document.getElementById('edaKpiAnomaly').textContent = d.kpis.max_temp + " °C";

        // Destroy old charts
        Object.values(edaCharts).forEach(c => c.destroy());
        edaCharts = {};

        // 1. Target Doughnut
        edaCharts.target = new Chart(document.getElementById('edaChartTarget'), {
            type: 'doughnut',
            data: { labels: ['Aman', 'Berisiko'], datasets: [{ data: [d.target_proportion.Aman, d.target_proportion.Berisiko], backgroundColor: ['#16a34a', '#ef4444'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: { position: 'bottom', labels: { usePointStyle: true } } } }
        });

        // 2. Soil Moisture Histogram
        edaCharts.hist = new Chart(document.getElementById('edaChartHist'), {
            type: 'bar',
            data: { labels: d.soil_moisture_dist.labels, datasets: [{ label: 'Frekuensi', data: d.soil_moisture_dist.data, backgroundColor: '#3b82f6', borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { grid: { color: '#f3f4f6' } } } }
        });

        // 3. Time Series Line
        edaCharts.time = new Chart(document.getElementById('edaChartTime'), {
            type: 'line',
            data: { 
                labels: d.time_series.labels, 
                datasets: [
                    { label: 'Curah Hujan (mm)', data: d.time_series.rainfall, borderColor: '#3b82f6', backgroundColor: '#3b82f6', yAxisID: 'y' },
                    { label: 'WSI (%)', data: d.time_series.wsi, borderColor: '#16a34a', backgroundColor: '#16a34a', yAxisID: 'y1' }
                ] 
            },
            options: { 
                responsive: true, maintainAspectRatio: false, 
                scales: { 
                    y: { type: 'linear', position: 'left', title: {display: true, text: 'Curah Hujan'} },
                    y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: {display: true, text: 'WSI'} }
                }
            }
        });

        // 4. Radar Chart
        edaCharts.radar = new Chart(document.getElementById('edaChartRadar'), {
            type: 'radar',
            data: { labels: d.radar.labels, datasets: [{ label: 'Rata-rata (Scaled)', data: d.radar.data, backgroundColor: 'rgba(249, 191, 41, 0.4)', borderColor: '#f9bf29', pointBackgroundColor: '#f9bf29' }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { r: { suggestedMin: 0, suggestedMax: 100 } } }
        });

        // 5. Correlation Table
        const thead = document.getElementById('edaCorrHead');
        const tbody = document.getElementById('edaCorrBody');
        const cols = Object.keys(d.correlation);
        
        thead.innerHTML = '<th>Var</th>' + cols.map(c => `<th>${c.substring(0,6)}</th>`).join('');
        tbody.innerHTML = cols.map(c => {
            return `<tr><td class="fw-bold">${c.substring(0,8)}</td>` + cols.map(c2 => {
                let val = d.correlation[c][c2];
                let bg = val > 0.5 ? '#fca5a5' : (val < -0.5 ? '#bfdbfe' : '#f3f4f6');
                return `<td style="background-color: ${val === 1 ? '#e5e7eb' : bg}">${val}</td>`;
            }).join('') + '</tr>';
        }).join('');

        // 6. Map Update
        if(edaGeojson) {
            edaGeojson.eachLayer(layer => {
                const geoName = layer.feature.properties.Propinsi;
                const apiName = PROVINCE_NAME_MAP[geoName] || geoName;
                const clusterId = CLUSTER_MAP[apiName];
                let cColor = '#d1d5db';
                if(clusterId === 0) cColor = '#3b82f6';
                if(clusterId === 1) cColor = '#16a34a';
                if(clusterId === 2) cColor = '#f59e0b';
                
                layer.setStyle({ fillColor: cColor, fillOpacity: 0.6, color: '#ffffff', weight: 1 });
                layer.setPopupContent(`<div class="fw-bold mb-1">${geoName}</div><div class="small">Cluster: ${clusterId}</div>`);
            });
        }

    } catch (e) { console.error("Dashboard error:", e); }
}
