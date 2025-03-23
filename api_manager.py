from flask import Flask, request, send_from_directory
import subprocess
import time
import requests
import os
from dotenv import load_dotenv
import urllib.parse
import json
from flasgger import Swagger
import flasgger
import markdown

app = Flask(__name__)

# Настройка Swagger
swagger_config = {
    "title": "Tabletop Simulator API by Djo",
    "description": "API for recording dice rolls in Tabletop Simulator",
    "version": "1.0.0",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "headers": [],
    "static_url_path": "/flasgger_static",  # Путь для статических файлов
    "static_dir": os.path.join(os.path.dirname(flasgger.__file__), "static"),  # Путь к встроенным файлам flasgger
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/apispec_1.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ]
}

swagger = Swagger(app, config=swagger_config)

# Настройки ngrok
load_dotenv()
NGROK_TOKEN = os.getenv("ngrok")
NGROK_PATH = os.path.join(os.path.dirname(__file__), "ngrok.exe")
PORT = 5000
STATIC_DOMAIN = "relieved-firm-titmouse.ngrok-free.app"

# Переменная для имитации текущего session_id
current_session_id = 0


# Маршрут для Terms of Service
@app.route('/tos')
def terms_of_service():
    # Читаем файл LICENSE.md
    license_path = os.path.join(os.path.dirname(__file__), "LICENSE.md")

    with open(license_path, "r", encoding="utf-8") as f:
        license_text = f.read()

        # Преобразуем Markdown в HTML
        license_html = markdown.markdown(license_text)

        # Оборачиваем в базовый HTML
        html_content = f"""
        <h1>Terms of Service</h1>
        {license_html}
        """
        return html_content

# Маршрут для favicon, чтобы убрать ошибку 404
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(os.path.dirname(flasgger.__file__), "static"),
        "favicon-32x32.png",
        mimetype="image/png"
    )

def start_ngrok():
    if not os.path.exists(NGROK_PATH):
        print(f"Error: {NGROK_PATH} not found!")
        return None
    if not NGROK_TOKEN:
        print("Error: NGROK_TOKEN not found in .env!")
        return None
    print(f"Starting ngrok with token at {NGROK_PATH}...")
    with open("ngrok.log", "w") as log_file:
        subprocess.Popen(
            [NGROK_PATH, "http", str(PORT), "--authtoken", NGROK_TOKEN, "--url", STATIC_DOMAIN],
            stdout=log_file,
            stderr=log_file,
            text=True
        )
    for i in range(15):
        try:
            response = requests.get("http://127.0.0.1:4040/api/tunnels")
            tunnels = response.json().get("tunnels", [])
            if tunnels:
                public_url = tunnels[0]["public_url"]
                print(f"Ngrok tunnel started: {public_url}")
                return public_url
        except requests.ConnectionError:
            time.sleep(1)
    print("Failed to get ngrok URL after 15 seconds. Check ngrok.log.")
    return None

@app.route('/start_session', methods=['POST'])
def start_session():
    """
    Start a new session
    ---
    tags:
      - Session
    responses:
      200:
        description: Session started successfully
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
    """
    global current_session_id
    current_session_id += 1
    print(f"New session created: ID {current_session_id}")
    return {"status": "success"}, 200

@app.route('/roll', methods=['POST'])
def roll():
    """
    Record a roll
    ---
    tags:
      - Roll
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            player:
              type: string
              example: WTF BOOM
            results:
              type: array
              items:
                type: integer
              example: [4, 5, 3]
            total:
              type: integer
              example: 12
    responses:
      200:
        description: Roll recorded successfully
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
      400:
        description: No active session
        schema:
          type: object
          properties:
            error:
              type: string
              example: No active session
    """
    global current_session_id
    raw_body = request.get_data(as_text=True)
    decoded_body = urllib.parse.unquote(raw_body)
    data = json.loads(decoded_body)
    data['session_id'] = current_session_id if current_session_id > 0 else None
    if not data['session_id']:
        print("Error: No active session! Please start a session with 'start'.")
        return {"error": "No active session"}, 400
    print(f"Roll received: player={data['player']}, results={data['results']}, total={data['total']}, session_id={data['session_id']}")
    return {"status": "success"}, 200

if __name__ == "__main__":
    ngrok_url = start_ngrok()
    if ngrok_url:
        print(f"Use this endpoint in TTS: {ngrok_url}/roll")
        print(f"Swagger UI available at: {ngrok_url}/apidocs")
    app.run(host="0.0.0.0", port=PORT)