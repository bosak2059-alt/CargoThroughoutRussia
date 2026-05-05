let chartInstance = null;
let currentOrders = [];

document.addEventListener("DOMContentLoaded", () => {
    loadData();
    setupForm();
    setupFilters();
    setupCalc();
    setupSettings();
    setupExport();
});

// === Загрузка и рендер ===
async function loadData() {
    try {
        currentOrders = await window.pywebview.api.get_orders();
        applyFilters();
        const stats = await window.pywebview.api.get_stats();
        renderStats(stats);
        renderChart(stats.statuses);
        loadSettingsUI();
    } catch (err) { console.error("Ошибка загрузки:", err); }
}

function applyFilters() {
    const search = document.getElementById("searchInput").value.toLowerCase();
    const status = document.getElementById("statusFilter").value;
    const filtered = currentOrders.filter(o => 
        o.client.toLowerCase().includes(search) && 
        (status === "all" || o.status === status)
    );
    renderTable(filtered);
}

function renderTable(orders) {
    const tbody = document.getElementById("ordersBody");
    tbody.innerHTML = "";
    if (!orders.length) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:#64748b;">Нет данных</td></tr>`;
        return;
    }
    orders.forEach(o => {
        const cls = o.status === "новый" ? "status-new" : o.status === "в пути" ? "status-transit" : "status-done";
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${o.id}</td><td>${o.date}</td><td>${escapeHtml(o.client)}</td><td>${escapeHtml(o.route)}</td>
            <td>${o.weight} кг</td>
            <td><select class="status-select ${cls}" onchange="changeStatus(${o.id}, this.value)">
                <option value="новый" ${o.status==="новый"?"selected":""}>Новый</option>
                <option value="в пути" ${o.status==="в пути"?"selected":""}>В пути</option>
                <option value="доставлен" ${o.status==="доставлен"?"selected":""}>Доставлен</option>
            </select></td>
            <td>${o.cost ? o.cost + " ₽" : "-"}</td>
            <td><button class="btn-delete" onclick="deleteOrder(${o.id})">Удалить</button></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderStats(stats) {
    document.getElementById("statTotal").textContent = stats.total;
    document.getElementById("statWeight").textContent = stats.weight + " кг";
}

function renderChart(statuses) {
    const ctx = document.getElementById("statusChart").getContext("2d");
    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Новые", "В пути", "Доставлены"],
            datasets: [{
                data: [statuses["новый"], statuses["в пути"], statuses["доставлен"]],
                backgroundColor: ["#f59e0b", "#3b82f6", "#10b981"], borderWidth: 0
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } }
    });
}

// === Форма и действия ===
function setupForm() {
    document.getElementById("orderForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const order = {
            client: document.getElementById("client").value.trim(),
            route: document.getElementById("route").value.trim(),
            weight: parseFloat(document.getElementById("weight").value),
            cost: parseFloat(document.getElementById("cost").value) || 0,
            status: "новый"
        };
        const res = await window.pywebview.api.add_order(order);
        if (res.success) { e.target.reset(); loadData(); }
    });
}

async function changeStatus(id, status) {
    await window.pywebview.api.update_status(id, status);
    loadData();
}

async function deleteOrder(id) {
    if (!confirm("Удалить заявку #" + id + "?")) return;
    try {
        const res = await window.pywebview.api.delete_order(id);
        if (res.success) {
            loadData(); // Обновит таблицу, статистику и график
        } else {
            alert("Ошибка: " + (res.message || "Не удалось удалить заявку"));
        }
    } catch (err) {
        alert("Ошибка удаления: " + err.message);
    }
}

// === Фильтры ===
function setupFilters() {
    document.getElementById("searchInput").addEventListener("input", applyFilters);
    document.getElementById("statusFilter").addEventListener("change", applyFilters);
}

// === Калькулятор ===
function setupCalc() {
    document.getElementById("calcBtn").addEventListener("click", async () => {
        const dist = parseFloat(document.getElementById("calcDistance").value);
        if (!dist || dist <= 0) return alert("Введите расстояние");
        const res = await window.pywebview.api.calculate_cost(dist);
        document.getElementById("calcTariff").textContent = res.tariff;
        document.getElementById("calcCost").textContent = res.cost.toFixed(2);
        document.getElementById("calcResult").classList.remove("hidden");
        document.getElementById("cost").value = res.cost.toFixed(2);
    });
}

// === Настройки ===
function setupSettings() {
    document.getElementById("settingsBtn").onclick = () => document.getElementById("settingsModal").classList.remove("hidden");
    document.getElementById("closeSettings").onclick = () => document.getElementById("settingsModal").classList.add("hidden");
    document.getElementById("saveSettings").onclick = async () => {
        const tariff = parseFloat(document.getElementById("setTariff").value);
        const company = document.getElementById("setCompany").value.trim();
        if (isNaN(tariff) || tariff <= 0) return alert("Некорректный тариф");
        await window.pywebview.api.update_settings({ tariff_per_km: tariff, company_name: company });
        document.getElementById("settingsModal").classList.add("hidden");
        alert("Настройки сохранены");
    };
}

function loadSettingsUI() {
    // Загружаем настройки из Python (можно вынести в отдельный метод, сейчас берём из расчёта)
    // Для простоты оставляем дефолт. В реальном проекте добавить api.get_settings()
}

// === Экспорт CSV ===
function setupExport() {
    document.getElementById("exportBtn").addEventListener("click", async () => {
        const csv = await window.pywebview.api.export_csv();
        if (!csv) return alert("Нет данных для экспорта");
        const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = `logistics_export_${new Date().toISOString().slice(0,10)}.csv`;
        a.click(); URL.revokeObjectURL(url);
    });
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}