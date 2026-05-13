let chartInstance = null, currentOrders = [], currentVehicles = [];

document.addEventListener("DOMContentLoaded", async () => {
    // await initTheme();
    if (window.pywebview){
        initTheme()
    }

    await loadAll();
    setupTabs();
    setupForm();
    setupCalc();
    setupFilters();
    setupVehicleForm();
    setupEdit();
    setupSettings();
    setupImportExport();
    setupPrint();
    setupPDF();
});

async function loadAll() {
    try {
        currentOrders = await window.pywebview.api.get_orders();
        currentVehicles = await window.pywebview.api.get_vehicles();
        renderVehicleSelect();
        renderVehiclesTable();
        renderLogs();
        applyFilters();
        const stats = await window.pywebview.api.get_stats();
        renderStats(stats);
        renderChart(stats.statuses);
        await loadSettingsUI();
    } catch (e) { showToast("Ошибка загрузки", "error"); }
}

// === Тема ===
async function initTheme() {
    const s = await window.pywebview.api.get_settings();
    const theme = s.theme || "light";
    document.documentElement.setAttribute("data-theme", theme);
    document.getElementById("themeBtn").textContent = theme === "dark" ? "☀️" : "🌙";
    document.getElementById("themeBtn").onclick = async () => {
        const next = theme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        document.getElementById("themeBtn").textContent = next === "dark" ? "☀️" : "🌙";
        await window.pywebview.api.update_theme(next);
        showToast(`Тема: ${next}`, "info");
    };
}

// === Табы ===
function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.onclick = () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
}

// === Заявки ===
function renderVehicleSelect() {
    const sel = document.getElementById("vehicleSelect");
    sel.innerHTML = `<option value="">-- Выберите ТС --</option>` + 
        currentVehicles.map(v => `<option value="${v.id}">${v.name} (${v.capacity}кг)</option>`).join('');
}

function setupForm() {
    document.getElementById("vehicleSelect").onchange = updateDeliveryTime;
    document.getElementById("weight").oninput = updateDeliveryTime;
    document.getElementById("orderForm").onsubmit = async (e) => {
        e.preventDefault();
        const order = {
            client: document.getElementById("client").value.trim(),
            route: document.getElementById("route").value.trim(),
            weight: parseFloat(document.getElementById("weight").value),
            vehicle_id: parseInt(document.getElementById("vehicleSelect").value) || 0,
            cost: parseFloat(document.getElementById("cost").value) || 0,
            status: "новый"
        };
        const res = await window.pywebview.api.add_order(order);
        if (res.success) { e.target.reset(); loadAll(); showToast("Заявка сохранена", "success"); }
        else showToast(res.message, "error");
    };
}

async function updateDeliveryTime() {
    const dist = parseFloat(document.getElementById("calcDist").value);
    const vid = parseInt(document.getElementById("vehicleSelect").value);
    if (dist && vid) {
        const t = await window.pywebview.api.calculate_time(dist, vid);
        document.getElementById("deliveryTime").value = t.days ? `${t.days}д ${t.hours}ч` : `${t.hours}ч`;
    }
}

function applyFilters() {
    const search = document.getElementById("searchInput").value.toLowerCase();
    const status = document.getElementById("statusFilter").value;
    const dStart = document.getElementById("dateStart").value;
    const dEnd = document.getElementById("dateEnd").value;

    const parseRu = d => { if(!d)return null; const [dd,mm,yyyy]=d.split('.'); return new Date(`${yyyy}-${mm}-${dd}`); };
    let filtered = currentOrders.filter(o => 
        o.client.toLowerCase().includes(search) && 
        (status === "all" || o.status === status)
    );
    if (dStart) filtered = filtered.filter(o => parseRu(o.date) >= new Date(dStart));
    if (dEnd) filtered = filtered.filter(o => parseRu(o.date) <= new Date(dEnd));
    renderTable(filtered);
}

function renderTable(orders) {
    const tbody = document.getElementById("ordersBody"); tbody.innerHTML = "";
    if (!orders.length) { tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;color:#64748b">Нет данных</td></tr>`; return; }
    const vMap = Object.fromEntries(currentVehicles.map(v=>[v.id, v.name]));
    orders.forEach(o => {
        const cls = o.status==="новый"?"status-new":o.status==="в пути"?"status-transit":"status-done";
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${o.id}</td><td>${o.date}</td><td>${escapeHtml(o.client)}</td><td>${vMap[o.vehicle_id]||"-"}</td>
            <td>${o.weight} кг</td>
            <td><select class="status-select ${cls}" onchange="changeStatus(${o.id},this.value)">
                <option value="новый" ${o.status==="новый"?"selected":""}>Новый</option>
                <option value="в пути" ${o.status==="в пути"?"selected":""}>В пути</option>
                <option value="доставлен" ${o.status==="доставлен"?"selected":""}>Доставлен</option>
            </select></td>
            <td>${o.cost?o.cost+" ₽":"-"}</td>
            <td>
                <button class="btn-pdf" onclick="genPDF(${o.id})">📄 PDF</button>
                <button class="btn-edit" onclick="openEdit(${o.id})">✏️</button>
                <button class="btn-delete" onclick="deleteOrder(${o.id})">🗑️</button>
            </td>`;
        tbody.appendChild(tr);
    });
}

// === Калькулятор ===
function setupCalc() {
    document.getElementById("calcBtn").onclick = async () => {
        const d = parseFloat(document.getElementById("calcDist").value);
        if (!d) return showToast("Введите расстояние", "error");
        const res = await window.pywebview.api.calculate_cost(d);
        document.getElementById("calcResult").textContent = `Тариф: ${res.tariff} ₽/км | Итого: ${res.cost.toFixed(2)} ₽`;
        document.getElementById("calcResult").classList.remove("hidden");
        document.getElementById("cost").value = res.cost.toFixed(2);
        updateDeliveryTime();
    };
}

// === Фильтры ===
function setupFilters() {
    document.getElementById("searchInput").oninput = applyFilters;
    document.getElementById("statusFilter").onchange = applyFilters;
    document.getElementById("dateStart").onchange = applyFilters;
    document.getElementById("dateEnd").onchange = applyFilters;
}

// === Транспорт ===
function renderVehiclesTable() {
    const tbody = document.getElementById("vehiclesBody"); tbody.innerHTML = "";
    currentVehicles.forEach(v => {
        tbody.innerHTML += `<tr><td>${v.id}</td><td>${v.name}</td><td>${v.capacity} кг</td><td>${v.avg_speed} км/ч</td><td><button class="btn-delete" onclick="delVehicle(${v.id})">Удалить</button></td></tr>`;
    });
}
function setupVehicleForm() {
    document.getElementById("vehicleForm").onsubmit = async (e) => {
        e.preventDefault();
        const v = { name: document.getElementById("vName").value, capacity: parseInt(document.getElementById("vCap").value), avg_speed: parseInt(document.getElementById("vSpeed").value) };
        await window.pywebview.api.add_vehicle(v); loadAll(); showToast("ТС добавлено", "success"); e.target.reset();
    };
}
async function delVehicle(id) { await window.pywebview.api.delete_vehicle(id); loadAll(); showToast("Удалено", "info"); }

// === Журнал ===
async function renderLogs() {
    const logs = await window.pywebview.api.get_logs();
    const tbody = document.getElementById("logsBody"); tbody.innerHTML = "";
    logs.slice().reverse().forEach(l => {
        tbody.innerHTML += `<tr><td>${l.timestamp}</td><td>${l.action}</td><td>#${l.order_id||"-"}</td><td>${l.details}</td></tr>`;
    });
}

// === Настройки & Бэкапы ===
async function loadSettingsUI() {
    const s = await window.pywebview.api.get_settings();
    document.getElementById("setTariff").value = s.tariff_per_km;
}
function setupSettings() {
    document.getElementById("saveSettings").onclick = async () => {
        const t = parseFloat(document.getElementById("setTariff").value);
        if (isNaN(t) || t <= 0) return showToast("Неверный тариф", "error");
        await window.pywebview.api.update_tariff(t); showToast("Тариф обновлён", "success");
    };
    document.getElementById("createBackup").onclick = async () => {
        const r = await window.pywebview.api.create_backup();
        showToast(`Бэкап: ${r.file}`, "success"); loadBackups();
    };
    loadBackups();
}
async function loadBackups() {
    const files = await window.pywebview.api.list_backups();
    const sel = document.getElementById("backupSelect"); sel.innerHTML = files.map(f => `<option value="${f}">${f.replace('data_','').replace('.json','')}</option>`).join('');
    document.getElementById("restoreBackup").onclick = async () => {
        const file = sel.value; if (!file) return;
        await window.pywebview.api.restore_backup(file);
        showToast("Восстановлено. Перезапустите приложение.", "info");
    };
}

// === Редактирование ===
function setupEdit() {
    document.getElementById("closeEdit").onclick = () => document.getElementById("editModal").classList.add("hidden");
    document.getElementById("saveEdit").onclick = async () => {
        const id = Number(document.getElementById("editId").value);
        const upd = { client: document.getElementById("editClient").value, route: document.getElementById("editRoute").value, weight: parseFloat(document.getElementById("editWeight").value), cost: parseFloat(document.getElementById("editCost").value)||0 };
        if (!upd.client || !upd.route) return showToast("Заполните поля", "error");
        const r = await window.pywebview.api.update_order(id, upd);
        if (r.success) { document.getElementById("editModal").classList.add("hidden"); loadAll(); showToast("Обновлено", "success"); }
        else showToast("Ошибка", "error");
    };
}
async function openEdit(id) {
    const o = currentOrders.find(x => x.id === id); if (!o) return;
    document.getElementById("editId").value = o.id; document.getElementById("editClient").value = o.client;
    document.getElementById("editRoute").value = o.route; document.getElementById("editWeight").value = o.weight;
    document.getElementById("editCost").value = o.cost || 0;
    document.getElementById("editModal").classList.remove("hidden");
}

// === Утилиты ===
async function changeStatus(id, s) { await window.pywebview.api.update_order(id, {status:s}); loadAll(); }
async function deleteOrder(id) { if(!confirm("Удалить?"))return; const r=await window.pywebview.api.delete_order(id); r.success?loadAll():showToast(r.message,"error"); }

function setupPrint() { document.getElementById("printBtn").onclick = () => window.print(); }

function setupPDF() { window.genPDF = async (id) => {
    const o = currentOrders.find(x => x.id === id);
    const s = await window.pywebview.api.get_settings();
    const doc = new jspdf.jsPDF();
    doc.setFontSize(16); doc.text(s.company_name || "Логистик-Про", 20, 20);
    doc.setFontSize(12); doc.text(`Накладная №${o.id} от ${o.date}`, 20, 30);
    doc.autoTable({ startY: 40, body: [["Заказчик", o.client], ["Маршрут", o.route], ["Вес", `${o.weight} кг`], ["Стоимость", `${o.cost||0} ₽`], ["Статус", o.status]] });
    doc.save(`nakladnaya_${o.id}.pdf`); showToast("PDF сохранён", "success");
}};

function setupImportExport() {
    document.getElementById("exportBtn").onclick = async () => {
        const csv = await window.pywebview.api.export_csv();
        if (!csv) return showToast("Нет данных", "error");
        const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["\ufeff"+csv], {type:"text/csv"}));
        a.download = `logistics_${Date.now()}.csv`; a.click(); showToast("Экспортировано", "success");
    };
    document.getElementById("importBtn").onclick = () => document.getElementById("importInput").click();
    document.getElementById("importInput").onchange = async (e) => {
        const f = e.target.files[0]; if (!f) return;
        try {
            let orders = [];
            if (f.name.endsWith(".json")) orders = JSON.parse(await f.text());
            else if (f.name.endsWith(".csv")) {
                const lines = (await f.text()).trim().split("\n");
                for (let i=1; i<lines.length; i++) { const [id,date,client,route,weight,status,cost]=lines[i].split(","); orders.push({id:Number(id),date,client,route,weight:Number(weight),status,cost:Number(cost)}); }
            }
            await window.pywebview.api.import_orders(orders); loadAll(); showToast("Импортировано", "success");
        } catch(err) { showToast("Ошибка импорта", "error"); }
        e.target.value="";
    };
}

function renderStats(s) { document.getElementById("statTotal").textContent=s.total; document.getElementById("statWeight").textContent=s.weight+" кг"; }
function renderChart(st) {
    const ctx = document.getElementById("statusChart").getContext("2d");
    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(ctx, { type: "doughnut", data: { labels: ["Новые","В пути","Доставлены"], datasets: [{ data: [st["новый"], st["в пути"], st["доставлен"]], backgroundColor: ["#f59e0b","#3b82f6","#10b981"], borderWidth: 0 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } } });
}

function showToast(msg, type="info") {
    const c = document.getElementById("toastContainer"), t = document.createElement("div");
    t.className = `toast ${type}`; t.textContent = msg; c.appendChild(t);
    setTimeout(() => { t.style.opacity="0"; t.style.transform="translateX(100%)"; setTimeout(()=>t.remove(), 300); }, 3000);
}
function escapeHtml(t) { const d=document.createElement("div"); d.textContent=t; return d.innerHTML; }