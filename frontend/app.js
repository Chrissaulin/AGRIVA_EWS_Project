const API = "http://localhost:8001";
let leafletMap, geojsonLayer, mapData = {};

// ===== TIER 2: FRONTEND LOGIC ENGINEER =====

// ===== NAVIGATION =====
document.querySelectorAll('[data-page]').forEach(link => {
    link.addEventListener('click', (e) => {
        if(link.tagName === 'A' || link.tagName === 'BUTTON') e.preventDefault();
        if(link.hasAttribute('data-page')) {
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
    if(page === 'eda' || page === 'model' || page === 'classification' || page === 'forecasting-eval') {
        const dropdown = document.getElementById('navbarDropdown');
        if(dropdown) dropdown.classList.add('active');
    }

    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    
    if (page === 'map' && !leafletMap) initMap();
    if (page === 'map' && leafletMap) setTimeout(() => leafletMap.invalidateSize(), 200);
    if (page === 'eda') loadEDA();
    if (page === 'model') loadModelDashboard();
    if (page === 'classification' && typeof loadClassificationDashboard === 'function') loadClassificationDashboard();
    if (page === 'forecasting-eval' && typeof loadForecastingEvalDashboard === 'function') loadForecastingEvalDashboard();
}

// ===== INIT =====
document.addEventListener("DOMContentLoaded", () => {
    loadMapFilters();
    loadPredictProvinces();
    loadForecastProvinces();
    setupPredictForm();
    setupForecastControls();


    // Navbar shrink on scroll
    window.addEventListener('scroll', () => {
        const navbar = document.querySelector('.custom-navbar');
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });
});

// ===== MAP =====
const PROVINCE_NAME_MAP = {
    "DI. ACEH": "Nangroe A.D.", "SUMATERA UTARA": "Sumatera Utara", "SUMATERA BARAT": "Sumatera Barat",
    "RIAU": "Riau", "JAMBI": "Jambi", "SUMATERA SELATAN": "Sumatera Selatan", "BENGKULU": "Bengkulu",
    "LAMPUNG": "Lampung", "BANGKA BELITUNG": "Bangka Belitung", 
    "DKI JAKARTA": "Dki Jakarta", "JAWA BARAT": "Jawa Barat", "JAWA TENGAH": "Jawa Tengah",
    "DAERAH ISTIMEWA YOGYAKARTA": "D.I. Yogyakarta", "JAWA TIMUR": "Jawa Timur", "PROBANTEN": "Banten",
    "BALI": "Bali", "NUSATENGGARA BARAT": "Nusatenggara B.", "NUSA TENGGARA TIMUR": "Nusatenggara T.",
    "KALIMANTAN BARAT": "Kalimantan Barat", "KALIMANTAN TENGAH": "Kalimantan T.", "KALIMANTAN SELATAN": "Kalimantan S.",
    "KALIMANTAN TIMUR": "Kalimantan Timur", "SULAWESI UTARA": "Sulawesi Utara", "SULAWESI TENGAH": "Sulawesi Tengah",
    "SULAWESI SELATAN": "Sulawesi Selatan", "SULAWESI TENGGARA": "Sulawesi Tengg.", "GORONTALO": "Gorontalo",
    "MALUKU": "Maluku", "MALUKU UTARA": "Maluku Utara", "IRIAN JAYA BARAT": "Papua Barat", 
    "IRIAN JAYA TENGAH": "Papua", "IRIAN JAYA TIMUR": "Papua"
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
                    layer.on({ 
                        mouseover: e => e.target.setStyle({ weight: 2, fillOpacity: 0.9 }), 
                        mouseout: e => {
                            if(e.target.options.customStyle) e.target.setStyle(e.target.options.customStyle);
                            else geojsonLayer.resetStyle(e.target);
                        } 
                    });
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

        // Calculate totals based on real dataset (33 provinces) instead of the 32 map polygons
        Object.values(mapData).forEach(info => {
            const isRisk = info.warning_code === 1;
            const clusterStr = info.cluster.toString();
            let matchCluster = (filterCluster === 'all' || clusterStr === filterCluster);
            let matchStatus = (filterStatus === 'all' || (filterStatus === 'aman' && !isRisk) || (filterStatus === 'risiko' && isRisk));
            if (matchCluster && matchStatus) {
                if(isRisk) countRisk++;
                else countSafe++;
                sumTemp += info.avg_temperature;
                countTemp++;
            }
        });

        if (geojsonLayer) {
            geojsonLayer.eachLayer(layer => {
                const geoName = layer.feature.properties.Propinsi;
                const apiName = PROVINCE_NAME_MAP[geoName] || geoName;
                const info = mapData[apiName];

                if (info) {
                    const isRisk = info.warning_code === 1;
                    const clusterStr = info.cluster.toString();

                    let matchCluster = (filterCluster === 'all' || clusterStr === filterCluster);
                    let matchStatus = (filterStatus === 'all' || (filterStatus === 'aman' && !isRisk) || (filterStatus === 'risiko' && isRisk));

                    if (matchCluster && matchStatus) {
                        // Fully matched
                        const customStyle = { 
                            fillColor: isRisk ? '#ef4444' : '#16a34a', 
                            color: isRisk ? '#dc2626' : '#15803d', 
                            fillOpacity: 0.8, 
                            weight: 1.5 
                        };
                        layer.setStyle(customStyle);
                        layer.options.customStyle = customStyle;
                        layer.setPopupContent(`<div class="fw-bold mb-1">${geoName}</div><span class="badge ${isRisk ? 'bg-danger' : 'bg-success'} mb-2">${info.warning}</span><div class="small text-muted">Cluster: ${info.cluster}<br>Curah Hujan: ${info.avg_rainfall} mm<br>Suhu: ${info.avg_temperature}°C<br>SPI-3: ${info.avg_spi}</div>`);
                    } else if (matchCluster && !matchStatus) {
                        // Matches cluster, but fails status filter (Show as gray but keep data)
                        const grayStyle = { fillColor: '#9ca3af', color: '#6b7280', fillOpacity: 0.6, weight: 1.5 };
                        layer.setStyle(grayStyle);
                        layer.options.customStyle = grayStyle;
                        layer.setPopupContent(`<div class="fw-bold mb-1">${geoName}</div><span class="badge bg-secondary mb-2">Tidak Masuk Filter Status</span><div class="small text-muted">Status Asli: <strong class="${isRisk ? 'text-danger' : 'text-success'}">${info.warning}</strong><br>Cluster: ${info.cluster}<br>Curah Hujan: ${info.avg_rainfall} mm<br>Suhu: ${info.avg_temperature}°C<br>SPI-3: ${info.avg_spi}</div>`);
                    } else {
                        // Fails cluster filter completely (Make very faint)
                        const hiddenStyle = { fillColor: '#f9fafb', color: '#e5e7eb', fillOpacity: 0.2, weight: 1 };
                        layer.setStyle(hiddenStyle);
                        layer.options.customStyle = hiddenStyle;
                        layer.setPopupContent(`<div class="fw-bold mb-1">${geoName}</div><div class="small text-muted">Berada di luar filter klaster.</div>`);
                    }
                } else {
                    const noDataStyle = { fillColor: '#f3f4f6', color: '#e5e7eb', fillOpacity: 0.3, weight: 1 };
                    layer.setStyle(noDataStyle);
                    layer.options.customStyle = noDataStyle;
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
            month_extracted: 6, // Fallback default
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

// ===== IMPORT CSV LOGIC =====
let parsedCsvData = [];

document.getElementById('csvFileInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    const container = document.getElementById('csvDekadSelectContainer');
    const applyBtn = document.getElementById('btnImportApply');
    
    if (!file) {
        container.classList.add('d-none');
        applyBtn.classList.add('d-none');
        return;
    }
    const reader = new FileReader();
    reader.onload = function(evt) {
        const text = evt.target.result;
        const lines = text.split('\n').map(l => l.trim()).filter(l => l);
        if (lines.length < 2) return alertInvalidCsv();
        
        const headers = lines[0].split(',');
        const requiredHeaders = ["Dekad_Ke", "Tanggal", "Rainfall", "SPI_3_months", "Temperature", "WSI", "Solar_Radiation", "Soil_Moisture", "FPAR", "FPAR_zscore"];
        
        const isValid = requiredHeaders.every((h, i) => headers[i] === h);
        if (!isValid) return alertInvalidCsv();
        
        parsedCsvData = lines.slice(1).map(line => {
            const vals = line.split(',');
            let obj = {};
            requiredHeaders.forEach((h, i) => obj[h] = vals[i]);
            return obj;
        });

        const select = document.getElementById('csvDekadSelect');
        select.innerHTML = parsedCsvData.map((d, i) => `<option value="${i}">Dekad Ke-${d.Dekad_Ke} (Est. ${d.Tanggal})</option>`).join('');
        
        container.classList.remove('d-none');
        applyBtn.classList.remove('d-none');
    };
    reader.readAsText(file);
});

function alertInvalidCsv() {
    alert("Format CSV tidak sesuai! Pastikan Anda menggunakan file CSV hasil Export dari fitur Forecasting tanpa mengubah headernya.");
    document.getElementById('csvFileInput').value = '';
    document.getElementById('csvDekadSelectContainer').classList.add('d-none');
    document.getElementById('btnImportApply').classList.add('d-none');
}

document.getElementById('btnImportApply').addEventListener('click', () => {
    const idx = document.getElementById('csvDekadSelect').value;
    if(idx === "") return;
    const data = parsedCsvData[idx];
    
    const mapInput = {
        'rainfall': 'Rainfall',
        'spi3': 'SPI_3_months',
        'temperature': 'Temperature',
        'wsi': 'WSI',
        'solarRad': 'Solar_Radiation',
        'soilMoisture': 'Soil_Moisture',
        'fpar': 'FPAR',
        'fparZ': 'FPAR_zscore'
    };
    
    for(const [elementId, csvKey] of Object.entries(mapInput)) {
        const el = document.getElementById(elementId);
        if(el && data[csvKey] !== undefined) {
            let val = parseFloat(data[csvKey]);
            if(isNaN(val)) continue;
            
            // Adjust to max/min limits of range input
            if(el.max && val > parseFloat(el.max)) val = parseFloat(el.max);
            if(el.min && val < parseFloat(el.min)) val = parseFloat(el.min);
            
            el.value = val;
            el.dispatchEvent(new Event('input'));
        }
    }
    
    if(data.Tanggal) {
        const d = new Date(data.Tanggal);
        if(!isNaN(d.valueOf())) {
            const selMonth = document.getElementById('monthExt');
            if(selMonth) {
                selMonth.value = d.getMonth() + 1;
            }
        }
    }
    
    const modalEl = document.getElementById('importCsvModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if(modal) modal.hide();
    else {
        // Fallback hide
        modalEl.classList.remove('show');
        modalEl.style.display = 'none';
        document.body.classList.remove('modal-open');
        const bdrop = document.querySelector('.modal-backdrop');
        if(bdrop) bdrop.remove();
    }
    
    document.getElementById('btnPredict').click();
});

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
            // Trigger automatic initial chart load
            setTimeout(() => runForecast(), 500);
        }
    } catch (e) { console.error(e); }
}

function setupForecastControls() {
    const slider = document.getElementById('forecastSteps');
    slider.addEventListener('input', () => { 
        document.getElementById('stepsValue').textContent = `${slider.value} Dekad`; 
    });
    // Auto-update when slider is released
    slider.addEventListener('change', runForecast);
    
    document.getElementById('btnForecast').addEventListener('click', runForecast);
    
    // Listen to changes on province/variable to auto-update
    document.getElementById('forecastProvince').addEventListener('change', runForecast);
    document.getElementById('forecastVariable').addEventListener('change', runForecast);

    // Export to CSV
    document.getElementById('btnExportCSV').addEventListener('click', () => {
        if (!lastForecastData || lastForecastData.length === 0) return alert('Tidak ada data ramalan untuk diekspor.');
        
        const headers = ["Dekad_Ke", "Tanggal", "Rainfall", "SPI_3_months", "Temperature", "WSI", "Solar_Radiation", "Soil_Moisture", "FPAR", "FPAR_zscore"];
        const rows = lastForecastData.map(p => {
            const d = p.predicted;
            return [
                p.step,
                p.date,
                d['Rainfall'] || 0,
                d['SPI - 3 months'] || 0,
                d['Temperature'] || 0,
                d['Water Satisfaction Index (WSI)'] || 0,
                d['Solar Radiation'] || 0,
                d['Soil Moisture (gapfilled historical time series)'] || 0,
                d['FPAR'] || 0,
                d['FPAR - zscore'] || 0
            ].join(',');
        });
        
        const csvContent = "data:text/csv;charset=utf-8," + headers.join(',') + "\n" + rows.join('\n');
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `forecast_results_${document.getElementById('forecastProvince').value}.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove();
    });
}

async function runForecast() {
    const btn = document.getElementById('btnForecast');
    if(!btn) return;
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Memproses...';
    btn.disabled = true;

    const province = document.getElementById('forecastProvince').value;
    const variable = document.getElementById('forecastVariable').value;
    const steps = parseInt(document.getElementById('forecastSteps').value);

    const varSelect = document.getElementById('forecastVariable');
    document.getElementById('forecastChartBadge').textContent = varSelect.options[varSelect.selectedIndex].text;

    try {
        const fRes = await fetch(`${API}/api/forecast/predict?province=${encodeURIComponent(province)}&steps=${steps}`, { method: "POST" });
        if(!fRes.ok) throw new Error("Gagal menjalankan forecast");
        const fData = await fRes.json();

        renderForecastChart(fData, variable);
        renderForecastTable(fData.predictions);
    } catch (e) { 
        console.error("Forecast error:", e); 
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

function renderForecastChart(fData, variable) {
    const ctx = document.getElementById('chartForecast');
    if (forecastChart) forecastChart.destroy();

    const histLabels = fData.historical_dates || [];
    const histActual = (fData.historical_actual && fData.historical_actual[variable]) ? fData.historical_actual[variable] : [];
    const histPred = (fData.historical_pred && fData.historical_pred[variable]) ? fData.historical_pred[variable] : [];
    
    const predLabels = fData.predictions.map(p => p.date || `Dekad ${p.step}`);
    const predValues = fData.predictions.map(p => p.predicted[variable] || 0);

    const allLabels = [...histLabels, ...predLabels];
    
    const actualDataset = [...histActual, ...Array(predLabels.length).fill(null)];
    const modelDataset = [...histPred, ...Array(predLabels.length).fill(null)];
    
    // Connect the future forecast line to the last model prediction point
    const futureDataset = [...Array(histLabels.length - 1).fill(null), histPred[histPred.length - 1], ...predValues];

    forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allLabels,
            datasets: [
                { 
                    label: 'Data Aktual (Training)', 
                    data: actualDataset, 
                    borderColor: '#3b5d50', 
                    backgroundColor: 'rgba(59, 93, 80, 0.1)', 
                    fill: false, 
                    tension: 0.3, 
                    pointRadius: 2, 
                    borderWidth: 2 
                },
                { 
                    label: 'Prediksi Model (Testing)', 
                    data: modelDataset, 
                    borderColor: '#10b981', 
                    backgroundColor: 'transparent', 
                    fill: false, 
                    tension: 0.3, 
                    pointRadius: 0, 
                    borderWidth: 2,
                    borderDash: [5, 5]
                },
                { 
                    label: 'Peramalan Masa Depan', 
                    data: futureDataset, 
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

// ===== CLASSIFICATION DASHBOARD =====
let classLoaded = false;
let classCharts = {};

async function loadClassificationDashboard() {
    if (!classLoaded) {
        document.getElementById('classFilterCluster').addEventListener('change', loadClassificationData);
        classLoaded = true;
    }
    loadClassificationData();
}

async function loadClassificationData() {
    const cluster = document.getElementById('classFilterCluster').value;
    
    try {
        const res = await fetch(`${API}/api/classification/dashboard?cluster=${cluster}`);
        const d = await res.json();
        if(d.error) return alert(d.error);

        // Update KPIs
        document.getElementById('classKpiRecall').textContent = d.kpis.recall;
        document.getElementById('classKpiF1').textContent = d.kpis.f1;
        document.getElementById('classKpiRoc').textContent = d.kpis.roc_auc;
        document.getElementById('classKpiThreshold').textContent = d.kpis.optimal_threshold;

        // Clean up old charts
        Object.values(classCharts).forEach(c => c.destroy());
        classCharts = {};

        // 1. Confusion Matrix (Bubble style approximation for Heatmap)
        const cm = d.confusion_matrix;
        const maxVal = Math.max(...cm.flat());
        classCharts.confusion = new Chart(document.getElementById('classChartConfusion'), {
            type: 'bubble',
            data: {
                datasets: [
                    {
                        label: 'Confusion Matrix',
                        data: [
                            {x: 0, y: 1, r: (cm[1][0]/maxVal)*30 + 5, value: cm[1][0], title: 'False Negative'},
                            {x: 1, y: 1, r: (cm[1][1]/maxVal)*30 + 5, value: cm[1][1], title: 'True Positive'},
                            {x: 0, y: 0, r: (cm[0][0]/maxVal)*30 + 5, value: cm[0][0], title: 'True Negative'},
                            {x: 1, y: 0, r: (cm[0][1]/maxVal)*30 + 5, value: cm[0][1], title: 'False Positive'}
                        ],
                        backgroundColor: (ctx) => {
                            const val = ctx.raw?.value || 0;
                            const t = ctx.raw?.title || '';
                            if (t === 'True Positive' || t === 'True Negative') return `rgba(22, 163, 74, ${Math.max(0.2, val/maxVal)})`;
                            return `rgba(239, 68, 68, ${Math.max(0.2, val/maxVal)})`;
                        }
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.raw.title}: ${ctx.raw.value}`
                        }
                    }
                },
                scales: {
                    x: {
                        min: -0.5, max: 1.5,
                        ticks: { callback: (v) => v === 0 ? 'Pred: Aman' : (v === 1 ? 'Pred: Risiko' : '') }
                    },
                    y: {
                        min: -0.5, max: 1.5,
                        ticks: { callback: (v) => v === 0 ? 'Actual: Aman' : (v === 1 ? 'Actual: Risiko' : '') }
                    }
                }
            }
        });

        // 2. Feature Importance (Horizontal Bar)
        classCharts.feature = new Chart(document.getElementById('classChartFeature'), {
            type: 'bar',
            data: {
                labels: d.feature_importance.labels.map(l => l.length > 20 ? l.substring(0, 20)+'...' : l),
                datasets: [{
                    label: 'Importance',
                    data: d.feature_importance.data,
                    backgroundColor: '#3b5d50',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false, indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: { x: { display: false }, y: { ticks: { font: { size: 10 } } } }
            }
        });

        // 3. Pie Chart (Aman vs Berisiko)
        classCharts.pie = new Chart(document.getElementById('classChartPie'), {
            type: 'doughnut',
            data: {
                labels: ['Aman', 'Berisiko'],
                datasets: [{
                    data: d.class_proportion,
                    backgroundColor: ['#16a34a', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false, cutout: '65%',
                plugins: { legend: { position: 'bottom' } }
            }
        });

        // 4. Precision-Recall Curve
        classCharts.pr = new Chart(document.getElementById('classChartPR'), {
            type: 'line',
            data: {
                datasets: [{
                    label: 'PR Curve',
                    data: d.pr_curve,
                    borderColor: '#f9bf29',
                    backgroundColor: 'rgba(249, 191, 41, 0.2)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { title: { display: true, text: 'Recall' }, min: 0, max: 1 },
                    y: { title: { display: true, text: 'Precision' }, min: 0, max: 1 }
                }
            }
        });

        // 5. Cluster Comparison Table
        const tbody = document.getElementById('classTableBody');
        tbody.innerHTML = d.table.map(r => `
            <tr>
                <td class="fw-bold">${r.cluster}</td>
                <td>${r.precision}</td>
                <td>${r.recall}</td>
                <td>${r.f1}</td>
            </tr>
        `).join('');

    } catch (err) {
        console.error("Classification dashboard error: ", err);
    }
}

let lastForecastData = [];

function renderForecastTable(predictions) {
    lastForecastData = predictions;
    const card = document.getElementById('forecastTableCard');
    card.style.display = 'block';
    const tbody = document.getElementById('forecastTableBody');
    tbody.innerHTML = predictions.map(p => {
        const d = p.predicted;
        return `<tr>
            <td class="fw-bold">Dekad ${p.step}</td>
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
    
    document.getElementById('btnEdaApply').addEventListener('click', loadEdaDashboard);
    document.getElementById('edaDistFeature').addEventListener('change', loadEdaDashboard);
    edaLoaded = true;
    
    loadEdaDashboard();
}

async function loadEdaDashboard() {
    const prov = document.getElementById('edaFilterProvince').value || 'All';
    const year = document.getElementById('edaFilterYear').value || 'All';
    const distF = document.getElementById('edaDistFeature').value || 'Soil Moisture (gapfilled historical time series)';

    try {
        const res = await fetch(`${API}/api/eda/dashboard?province=${encodeURIComponent(prov)}&year=${encodeURIComponent(year)}&dist_feature=${encodeURIComponent(distF)}`);
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

        // 1. Target Doughnut (Highlight minority)
        const isAmanMinority = d.target_proportion.Aman < d.target_proportion.Berisiko;
        edaCharts.target = new Chart(document.getElementById('edaChartTarget'), {
            type: 'doughnut',
            data: { 
                labels: ['Aman', 'Berisiko'], 
                datasets: [{ 
                    data: [d.target_proportion.Aman, d.target_proportion.Berisiko], 
                    backgroundColor: ['#16a34a', '#ef4444'], 
                    borderColor: ['#000000', '#000000'],
                    borderWidth: isAmanMinority ? [3, 0] : [0, 3],
                    offset: isAmanMinority ? [20, 0] : [0, 20]
                }] 
            },
            options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: { position: 'bottom', labels: { usePointStyle: true } } } }
        });

        // 2. Dynamic Histogram
        edaCharts.hist = new Chart(document.getElementById('edaChartHist'), {
            type: 'bar',
            data: { labels: d.feature_dist.labels, datasets: [{ label: 'Frekuensi', data: d.feature_dist.data, backgroundColor: '#3b5d50', borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { grid: { color: '#f3f4f6' } } } }
        });

        // 3. Time Series Line (Theme colors)
        edaCharts.time = new Chart(document.getElementById('edaChartTime'), {
            type: 'line',
            data: { 
                labels: d.time_series.labels, 
                datasets: [
                    { label: 'Curah Hujan (mm)', data: d.time_series.rainfall, borderColor: '#3b5d50', backgroundColor: '#3b5d50', yAxisID: 'y' },
                    { label: 'WSI (%)', data: d.time_series.wsi, borderColor: '#f9bf29', backgroundColor: '#f9bf29', yAxisID: 'y1' }
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
            data: { labels: d.radar.labels, datasets: [{ label: 'Rata-rata', data: d.radar.data, backgroundColor: 'rgba(249, 191, 41, 0.4)', borderColor: '#f9bf29', pointBackgroundColor: '#f9bf29' }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { r: { suggestedMin: 0, suggestedMax: 100 } } }
        });

        // 5. Scatter Plot
        edaCharts.scatter = new Chart(document.getElementById('edaChartScatter'), {
            type: 'scatter',
            data: {
                datasets: [
                    { label: 'Aman', data: d.scatter.aman, backgroundColor: '#16a34a', pointRadius: 4, pointHoverRadius: 6 },
                    { label: 'Berisiko', data: d.scatter.berisiko, backgroundColor: '#ef4444', borderColor: '#000000', borderWidth: 1, pointRadius: 6, pointHoverRadius: 8, pointStyle: 'triangle' }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: { x: { title: { display: true, text: 'Curah Hujan (mm)' } }, y: { title: { display: true, text: 'Kelembaban Tanah' } } }
            }
        });

        // 6. Data Table Update
        const tbody = document.getElementById('edaDataTable');
        tbody.innerHTML = d.table_data.map(row => `
            <tr>
                <td class="fw-bold text-dark">${row.Kategori}</td>
                <td>${row['Rainfall'] ?? '-'}</td>
                <td>${row['Temperature'] ?? '-'}</td>
                <td>${row['SPI - 3 months'] ?? '-'}</td>
                <td>${row['Water Satisfaction Index (WSI)'] ?? '-'}</td>
                <td>${row['Soil Moisture (gapfilled historical time series)'] ?? '-'}</td>
                <td>${row['Solar Radiation'] ?? '-'}</td>
                <td>${row['FPAR'] ?? '-'}</td>
                <td>${row['FPAR - zscore'] ?? '-'}</td>
                <td class="fw-bold text-danger">${row['target_biner']}</td>
            </tr>
        `).join('');

    } catch (e) { console.error("Dashboard error:", e); }
}

// ===== EWS MODEL EXPERIMENT DASHBOARD =====
let modelLoaded = false;
let modelCharts = {};

function loadModelDashboard() {
    if (modelLoaded) return;
    
    // Data for Evaluation Chart
    const silhouetteData = {
        label: 'Silhouette Score',
        data: [0.380, 0.3916, 0.352, 0.315, 0.280, 0.265],
        pointBackgroundColor: ['#3b5d50', '#f9bf29', '#3b5d50', '#3b5d50', '#3b5d50', '#3b5d50']
    };
    const elbowData = {
        label: 'Inertia (Elbow Method)',
        data: [24000, 15000, 12000, 10000, 8500, 7500],
        pointBackgroundColor: ['#3b5d50', '#f9bf29', '#3b5d50', '#3b5d50', '#3b5d50', '#3b5d50']
    };

    // 1. CLUSTERING: Evaluation Chart
    modelCharts.cluster = new Chart(document.getElementById('modelChartCluster'), {
        type: 'line',
        data: {
            labels: ['k=2', 'k=3', 'k=4', 'k=5', 'k=6', 'k=7'],
            datasets: [{
                label: silhouetteData.label,
                data: silhouetteData.data,
                borderColor: '#3b5d50',
                backgroundColor: 'rgba(59, 93, 80, 0.1)',
                borderWidth: 3,
                pointBackgroundColor: silhouetteData.pointBackgroundColor,
                pointRadius: [4, 8, 4, 4, 4, 4],
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { padding: 10 } },
            scales: { y: { beginAtZero: false, grid: { color: '#f3f4f6' } }, x: { grid: { display: false } } }
        }
    });

    // Dropdown Logic for Evaluation Chart
    document.getElementById('clusterEvalSelect').addEventListener('change', (e) => {
        const val = e.target.value;
        const dataset = modelCharts.cluster.data.datasets[0];
        if(val === 'silhouette') {
            dataset.label = silhouetteData.label;
            dataset.data = silhouetteData.data;
        } else {
            dataset.label = elbowData.label;
            dataset.data = elbowData.data;
        }
        modelCharts.cluster.update();
    });

    // 2. PIE CHART: Cluster Proportion
    modelCharts.pie = new Chart(document.getElementById('modelChartPie'), {
        type: 'doughnut',
        data: {
            labels: ['Klaster 0', 'Klaster 1', 'Klaster 2'],
            datasets: [{
                data: [18, 9, 6],
                backgroundColor: ['#0dcaf0', '#198754', '#ffc107'],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            cutout: '60%',
            plugins: { 
                legend: { position: 'right', labels: { boxWidth: 12, font: { size: 10 } } } 
            }
        }
    });

    // 3. SCATTER PLOT: Rainfall vs Temperature with Province Names
    const c0_provs = ["Banten", "Dki Jakarta", "Jawa Barat", "Jawa Tengah", "Kalimantan Barat", "Kalimantan S.", "Kalimantan T.", "Kalimantan Timur", "Kepulauan-riau", "Lampung", "Maluku", "Nangroe A.D.", "Papua Barat", "Riau", "Sulawesi Barat", "Sulawesi Selatan", "Sulawesi Tengg.", "Sumatera Selatan"];
    const c1_provs = ["Bali", "Bangka Belitung", "D.I. Yogyakarta", "Gorontalo", "Jawa Timur", "Maluku Utara", "Nusatenggara B.", "Nusatenggara T.", "Papua"];
    const c2_provs = ["Bengkulu", "Jambi", "Sulawesi Tengah", "Sulawesi Utara", "Sumatera Barat", "Sumatera Utara"];

    modelCharts.scatter = new Chart(document.getElementById('modelChartScatter'), {
        type: 'scatter',
        data: {
            datasets: [
                {
                    label: 'Klaster 0 (Basah)',
                    data: c0_provs.map(p => ({x: 71.58 + (Math.random()*15-7.5), y: 25.95 + (Math.random()*2-1), prov: p})),
                    backgroundColor: 'rgba(13, 202, 240, 0.7)',
                    borderColor: '#0dcaf0',
                    pointRadius: 5,
                    pointHoverRadius: 8
                },
                {
                    label: 'Klaster 1 (Kering)',
                    data: c1_provs.map(p => ({x: 56.48 + (Math.random()*15-7.5), y: 25.38 + (Math.random()*2-1), prov: p})),
                    backgroundColor: 'rgba(25, 135, 84, 0.7)',
                    borderColor: '#198754',
                    pointRadius: 5,
                    pointHoverRadius: 8
                },
                {
                    label: 'Klaster 2 (Super Basah)',
                    data: c2_provs.map(p => ({x: 72.27 + (Math.random()*15-7.5), y: 23.22 + (Math.random()*2-1), prov: p})),
                    backgroundColor: 'rgba(255, 193, 7, 0.7)',
                    borderColor: '#ffc107',
                    pointRadius: 5,
                    pointHoverRadius: 8
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { 
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.raw.prov;
                        }
                    }
                }
            },
            scales: {
                x: { title: { display: true, text: 'Curah Hujan (mm)' }, grid: { color: '#f3f4f6' } },
                y: { title: { display: true, text: 'Suhu Udara (°C)' }, grid: { color: '#f3f4f6' } }
            }
        }
    });

    modelLoaded = true;
}

// ===== FORECASTING EVALUATION DASHBOARD =====
let forecastEvalLoaded = false;
let forecastEvalCharts = {};

function loadForecastingEvalDashboard() {
    if (!forecastEvalLoaded) {
        document.getElementById('forecastEvalFilterTarget').addEventListener('change', loadForecastingEvalData);
        document.getElementById('forecastEvalFilterCluster').addEventListener('change', loadForecastingEvalData);
        forecastEvalLoaded = true;
    }
    loadForecastingEvalData();
}

async function loadForecastingEvalData() {
    const target = document.getElementById('forecastEvalFilterTarget').value;
    const cluster = document.getElementById('forecastEvalFilterCluster').value;
    
    try {
        const res = await fetch(`${API}/api/forecast/dashboard?cluster=${cluster}&target=${encodeURIComponent(target)}`);
        const d = await res.json();
        if(d.error) return alert(d.error);

        // Update KPIs
        document.getElementById('forecastKpiMae').textContent = d.kpis.mae;
        document.getElementById('forecastKpiRmse').textContent = d.kpis.rmse;
        document.getElementById('forecastKpiMape').textContent = `${d.kpis.mape}%`;
        document.getElementById('forecastKpiSafety').textContent = `± ${d.kpis.safety}`;

        // Render Table logic removed as per user request

        // Destroy old charts
        Object.values(forecastEvalCharts).forEach(c => {
            if(c) c.destroy();
        });
        forecastEvalCharts = {};

        // 1. Line Chart (Actual vs Predicted)
        forecastEvalCharts.line = new Chart(document.getElementById('forecastChartLine'), {
            type: 'line',
            data: {
                labels: d.charts.labels || [],
                datasets: [
                    { label: 'Aktual', data: d.charts.actual || [], borderColor: '#198754', tension: 0.3, pointRadius: 2 },
                    { label: 'Prediksi', data: d.charts.predicted || [], borderColor: '#ffc107', tension: 0.3, pointRadius: 2, borderDash: [5, 5] }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        // 3. Histogram
        forecastEvalCharts.hist = new Chart(document.getElementById('forecastChartHist'), {
            type: 'bar',
            data: {
                labels: d.charts.hist_labels || [],
                datasets: [{
                    label: 'Frekuensi Error',
                    data: d.charts.hist_data || [],
                    backgroundColor: '#ef4444'
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

    } catch (err) {
        console.error("Forecasting dashboard error: ", err);
    }
}
