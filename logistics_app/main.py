import json, os, sys, csv, io, shutil
from datetime import datetime
import webview
import base64

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)

HTML_PATH = os.path.join(BASE_DIR, "frontend", "index.html")
DATA_FILE = os.path.join(BASE_DIR, "data.json")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
#New
EXPORTS_DIR = os.path.join(BASE_DIR, "saves_exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        default = {
            "orders": [],
            "settings": {
                "tariff_per_km": 15.0,
                "company_name": "ООО Логистик-Про",
                "theme": "light"
            },
            "vehicles": [
                {"id": 1,  "type": "Фура реф",        "brand": "DAF XF",         "plate": "У743КС161", "capacity": 20000, "avg_speed": 60},
                {"id": 2,  "type": "Тент",             "brand": "MAN TGX",        "plate": "А123БВ77",  "capacity": 22000, "avg_speed": 65},
                {"id": 3,  "type": "Изотерм",          "brand": "Volvo FH",       "plate": "М456НО78",  "capacity": 20000, "avg_speed": 60},
                {"id": 4,  "type": "Контейнеровоз",    "brand": "Scania R",       "plate": "К789РС16",  "capacity": 24000, "avg_speed": 55},
                {"id": 5,  "type": "Бортовой",         "brand": "КамАЗ 65117",    "plate": "О321ТУ61",  "capacity": 15000, "avg_speed": 50},
                {"id": 6,  "type": "Реф",              "brand": "Mercedes Actros","plate": "Р654УМ19",  "capacity": 18000, "avg_speed": 62},
                {"id": 7,  "type": "Тент",             "brand": "Iveco S-Way",    "plate": "С987ВН50",  "capacity": 21000, "avg_speed": 64},
                {"id": 8,  "type": "Цистерна",         "brand": "МАЗ 6317",       "plate": "Т246КЕ02",  "capacity": 12000, "avg_speed": 55},
                {"id": 9,  "type": "Малотоннажный",    "brand": "ГАЗель Next",    "plate": "В135ОП77",  "capacity": 1500,  "avg_speed": 70},
                {"id": 10, "type": "Лесовоз",          "brand": "Volvo FMX",      "plate": "Л879ИР64",  "capacity": 30000, "avg_speed": 45}
            ],
            "logs": []
        }
        save_data(default)
        return default
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Ошибка чтения {DATA_FILE}: {e}. Загружаю резервные данные.")
        # Здесь был рекурсивный вызов load_data(), который при повреждённом файле
        # уходил в бесконечный цикл. Безопаснее вернуть дефолт или вызвать конструктор.
        return load_data.__defaults__[0] if hasattr(load_data, '__defaults__') else default

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_action(action, order_id, details):
    data = load_data()
    data["logs"].append({
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "action": action, "order_id": order_id, "details": details
    })
    if len(data["logs"]) > 500:
        data["logs"] = data["logs"][-500:]
    save_data(data)

class API:
    def get_orders(self): return load_data().get("orders", [])
    def get_vehicles(self): return load_data().get("vehicles", [])
    def get_logs(self): return load_data().get("logs", [])
    def get_settings(self): return load_data().get("settings", {})

    def get_stats(self):
        orders = load_data().get("orders", [])
        statuses = {"новый": 0, "в пути": 0, "доставлен": 0}
        total_weight = 0
        for o in orders:
            st = o.get("status", "новый")
            if st in statuses: statuses[st] += 1
            total_weight += float(o.get("weight", 0))
        return {"total": len(orders), "weight": total_weight, "statuses": statuses}

    def add_order(self, order):
        data = load_data()
        order["id"] = len(data["orders"]) + 1
        order["date"] = datetime.now().strftime("%d.%m.%Y")
        
        vehicle = next((v for v in data["vehicles"] if v["id"] == order.get("vehicle_id")), None)
        if vehicle and float(order.get("weight", 0)) > vehicle["capacity"]:
            return {"success": False, "message": f"Вес превышает грузоподъёмность ({vehicle['capacity']} кг)"}
            
        data["orders"].append(order)
        save_data(data)
        log_action("Создание", order["id"], f"{order.get('client')} | {order.get('weight')}кг")
        return {"success": True}

    def update_order(self, order_id, updated):
        data = load_data()
        for o in data["orders"]:
            if o["id"] == order_id:
                # Валидация веса при изменении ТС или массы
                vid = updated.get("vehicle_id", o.get("vehicle_id", 0))
                w = updated.get("weight", o.get("weight", 0))
                vehicle = next((v for v in data["vehicles"] if v["id"] == vid), None)
                
                if vehicle and float(w) > vehicle["capacity"]:
                    return {"success": False, "message": f"Вес превышает грузоподъёмность ТС ({vehicle['capacity']} кг)"}
                    
                o.update(updated) # Обновляет только переданные поля, остальные остаются
                save_data(data)
                log_action("Обновление", order_id, f"Изменено: {', '.join(updated.keys())}")
                return {"success": True}
        return {"success": False, "message": "Заявка не найдена"}

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
        log_action("ТС добавлено", 0, f"{v.get('type')} {v.get('brand')}")
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
        w.writerow(["ID", "Дата", "Заказчик", "Маршрут", "Вес", "Перевозчик", "Дата погр.", "Водитель", "ТС", "Статус", "Стоимость"])
        for o in orders:
            w.writerow([
                o["id"], o["date"], o["client"], o["route"], o["weight"],
                o.get("carrier", "-"), o.get("loading_date", "-"), o.get("driver", "-"),
                o.get("vehicle_id", "-"), o["status"], o.get("cost", 0)
            ])
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
    
    def save_csv_export(self, csv_data, filename):
        """Сохраняет CSV в фиксированную папку без диалогов ОС"""
        filepath = os.path.join(EXPORTS_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(csv_data)
        return {"success": True, "filepath": filepath}

    def save_pdf_export(self, base64_pdf, filename):
        """Принимает base64 от jsPDF и сохраняет бинарный PDF на диск"""
        if base64_pdf.startswith("data:"):
            base64_pdf = base64_pdf.split(",")[1]
        pdf_bytes = base64.b64decode(base64_pdf)
        filepath = os.path.join(EXPORTS_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        return {"success": True, "filepath": filepath}

if __name__ == "__main__":
    if not os.path.exists(HTML_PATH):
        print(f"❌ Ошибка: index.html не найден по пути {HTML_PATH}")
        sys.exit(1)
    api = API()
    window = webview.create_window(title="Цифровая Логистика v3.1", url=HTML_PATH, js_api=api, width=1250, height=850, resizable=True)
    webview.start()