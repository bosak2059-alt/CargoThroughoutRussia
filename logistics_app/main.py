import json, os, sys, csv, io, shutil
from datetime import datetime
import webview

# --- Настройка путей ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)

HTML_PATH = os.path.join(BASE_DIR, "frontend", "index.html")
DATA_FILE = os.path.join(BASE_DIR, "data.json")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

# --- Работа с данными ---
def load_data():
    if not os.path.exists(DATA_FILE):
        default = {
            "orders": [],
            "settings": {"tariff_per_km": 15.0, "company_name": "ООО Логистик-Про", "theme": "light"},
            "vehicles": [
                {"id": 1, "name": "Газель", "capacity": 1500, "avg_speed": 70},
                {"id": 2, "name": "Фура 20т", "capacity": 20000, "avg_speed": 60}
            ],
            "logs": []
        }
        save_data(default)
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return load_data() # Сброс при ошибке чтения

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_action(action, order_id, details):
    data = load_data()
    data["logs"].append({
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "action": action,
        "order_id": order_id,
        "details": details
    })
    if len(data["logs"]) > 500:
        data["logs"] = data["logs"][-500:]
    save_data(data)

# --- API Класс ---
class API:
    def get_orders(self): 
        return load_data().get("orders", [])
    
    def get_vehicles(self): 
        return load_data().get("vehicles", [])
    
    def get_logs(self): 
        return load_data().get("logs", [])
    
    def get_settings(self): 
        return load_data().get("settings", {})

    # === ВОТ ЭТОГО МЕТОДА НЕ ХВАТАЛО ===
    def get_stats(self):
        orders = load_data().get("orders", [])
        statuses = {"новый": 0, "в пути": 0, "доставлен": 0}
        total_weight = 0
        for o in orders:
            st = o.get("status", "новый")
            if st in statuses:
                statuses[st] += 1
            total_weight += float(o.get("weight", 0))
        return {
            "total": len(orders), 
            "weight": total_weight, 
            "statuses": statuses
        }

    def add_order(self, order):
        data = load_data()
        order["id"] = len(data["orders"]) + 1
        order["date"] = datetime.now().strftime("%d.%m.%Y")
        
        # Проверка веса
        vehicle = next((v for v in data["vehicles"] if v["id"] == order.get("vehicle_id")), None)
        if vehicle and order["weight"] > vehicle["capacity"]:
            return {"success": False, "message": f"Вес превышает грузоподъёмность ({vehicle['capacity']} кг)"}
            
        data["orders"].append(order)
        save_data(data)
        log_action("Создание", order["id"], f"{order['client']} | {order['weight']}кг")
        return {"success": True}

    def update_order(self, order_id, updated):
        data = load_data()
        for o in data["orders"]:
            if o["id"] == order_id:
                o.update(updated)
                save_data(data)
                log_action("Обновление", order_id, f"Изменено: {list(updated.keys())}")
                return {"success": True}
        return {"success": False}

    def delete_order(self, order_id):
        data = load_data()
        before = len(data["orders"])
        data["orders"] = [o for o in data["orders"] if o["id"] != order_id]
        if len(data["orders"]) < before:
            save_data(data)
            log_action("Удаление", order_id, "Заявка удалена")
            return {"success": True}
        return {"success": False}

    def add_vehicle(self, v):
        data = load_data()
        v["id"] = len(data["vehicles"]) + 1
        data["vehicles"].append(v)
        save_data(data)
        log_action("ТС добавлено", 0, v["name"])
        return {"success": True}

    def delete_vehicle(self, vid):
        data = load_data()
        data["vehicles"] = [v for v in data["vehicles"] if v["id"] != vid]
        save_data(data)
        return {"success": True}

    def calculate_time(self, distance, vehicle_id):
        data = load_data()
        vehicle = next((v for v in data["vehicles"] if v["id"] == vehicle_id), None)
        if not vehicle: return {"error": "Выберите ТС"}
        hours = distance / vehicle["avg_speed"]
        return {"days": int(hours // 24), "hours": int(hours % 24), "total": round(hours, 1)}

    def calculate_cost(self, dist):
        t = load_data().get("settings", {}).get("tariff_per_km", 15)
        return {"cost": round(dist * t, 2), "tariff": t}

    def update_theme(self, theme):
        d = load_data()
        d.setdefault("settings", {})["theme"] = theme
        save_data(d)
        return {"success": True}

    def update_tariff(self, tariff):
        d = load_data()
        d.setdefault("settings", {})["tariff_per_km"] = float(tariff)
        save_data(d)
        return {"success": True}

    def create_backup(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(BACKUP_DIR, f"data_{ts}.json")
        shutil.copy2(DATA_FILE, dest)
        return {"success": True, "file": os.path.basename(dest)}

    def list_backups(self):
        if not os.path.exists(BACKUP_DIR): return []
        return sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")], reverse=True)

    def restore_backup(self, filename):
        src = os.path.join(BACKUP_DIR, filename)
        if os.path.exists(src):
            shutil.copy2(src, DATA_FILE)
            log_action("Восстановление", 0, f"Бэкап: {filename}")
            return {"success": True}
        return {"success": False}

    def export_csv(self):
        orders = load_data().get("orders", [])
        if not orders: return ""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["ID", "Дата", "Заказчик", "Маршрут", "Вес", "Статус", "Стоимость"])
        for o in orders:
            w.writerow([o["id"], o["date"], o["client"], o["route"], o["weight"], o["status"], o.get("cost", 0)])
        return out.getvalue()

    def import_orders(self, orders):
        data = load_data()
        max_id = max([o.get("id", 0) for o in data["orders"]], default=0)
        for o in orders:
            max_id += 1
            o["id"] = max_id
            if "date" not in o: o["date"] = datetime.now().strftime("%d.%m.%Y")
            data["orders"].append(o)
        save_data(data)
        log_action("Импорт", 0, f"Добавлено {len(orders)} заявок")
        return {"success": True}

if __name__ == "__main__":
    if not os.path.exists(HTML_PATH):
        print(f"Ошибка: index.html не найден в {HTML_PATH}")
    else:
        api = API()
        window = webview.create_window(title="Логистика v3.0", url=HTML_PATH, js_api=api, width=1250, height=850)
        webview.start()