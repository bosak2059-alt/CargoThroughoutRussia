import json
import os
import sys
import csv
import io
from datetime import datetime
import webview

# Определяем путь к файлу данных (работает и из .py, и из .exe)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(BASE_DIR, "data.json")

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "orders": [],
            "settings": {
                "tariff_per_km": 15.0,
                "company_name": "ООО Логистик-Про",
                "company_inn": "1234567890"
            }
        }
        save_data(default_data)
        return default_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class API:
    """Методы, вызываемые из JavaScript через window.pywebview.api"""
    
    def get_orders(self):
        return load_data().get("orders", [])

    def add_order(self, order):
        data = load_data()
        order["id"] = len(data["orders"]) + 1
        order["date"] = datetime.now().strftime("%d.%m.%Y")
        data["orders"].append(order)
        save_data(data)
        return {"success": True}

    def update_status(self, order_id, new_status):
        data = load_data()
        for o in data["orders"]:
            if o["id"] == order_id:
                o["status"] = new_status
                save_data(data)
                return {"success": True}
        return {"success": False}

    def calculate_cost(self, distance_km):
        settings = load_data().get("settings", {})
        tariff = float(settings.get("tariff_per_km", 15))
        return {"cost": round(distance_km * tariff, 2), "tariff": tariff}

    def export_csv(self):
        orders = load_data().get("orders", [])
        if not orders:
            return ""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Дата", "Заказчик", "Маршрут", "Вес (кг)", "Статус", "Стоимость (₽)"])
        for o in orders:
            writer.writerow([
                o["id"], o["date"], o["client"], o["route"],
                o["weight"], o["status"], o.get("cost", 0)
            ])
        return output.getvalue()

    def update_settings(self, new_settings):
        data = load_data()
        data.setdefault("settings", {}).update(new_settings)
        save_data(data)
        return {"success": True}
    
    def delete_order(self, order_id):
        """Полное удаление заявки по ID"""
        data = load_data()
        original_len = len(data["orders"])
        
        # Фильтруем массив, оставляя всё, кроме удаляемого ID
        data["orders"] = [o for o in data["orders"] if o["id"] != order_id]
        
        if len(data["orders"]) < original_len:
            save_data(data)
            return {"success": True}
        return {"success": False, "message": "Заявка не найдена"}

    def get_stats(self):
        orders = load_data().get("orders", [])
        total = len(orders)
        weight = sum(float(o.get("weight", 0)) for o in orders)
        statuses = {"новый": 0, "в пути": 0, "доставлен": 0}
        for o in orders:
            st = o.get("status", "новый").lower()
            if st in statuses:
                statuses[st] += 1
        return {"total": total, "weight": round(weight, 1), "statuses": statuses}

if __name__ == "__main__":
    api = API()
    window = webview.create_window(
        title="Логистика v2.0",
        url="frontend/index.html",
        js_api=api,
        width=1200,
        height=800,
        resizable=True
    )
    webview.start()