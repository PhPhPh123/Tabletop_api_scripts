'''
Данный модуль управляет приёмом сообщений из Tabletop Simulator через endpoint созданный на Flask-сервере,
проброшенный NGROK на статический адрес. Регистрационные данные находятся в файле .env
'''


from flask import Flask, request, send_from_directory
import subprocess
import time
import requests
import os
from dotenv import load_dotenv
import json
from flasgger import Swagger
import flasgger
import markdown
from urllib.parse import unquote
import pika

class APILayer:
    def __init__(self, db_layer, broker_layer):
        self.app = Flask(__name__)
        self.db_layer = db_layer
        self.current_session_id = 0
        self.setup_swagger()
        self.setup_routes()
        self.setup_ngrok()
        self.broker_layer = broker_layer

    def connect_to_rabbitmq(self):
        # Устанавливаем соединение с RabbitMQ один раз при инициализации
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='game_data', durable=True)

    def setup_swagger(self):
        swagger_config = {
            "title": "Dice Roll API",
            "description": "API for recording dice rolls in Tabletop Simulator",
            "version": "1.0.0",
            "swagger_ui": True,
            "specs_route": "/apidocs/",
            "termsOfService": "/tos",
            "headers": [],
            "static_url_path": "/flasgger_static",
            "static_dir": os.path.join(os.path.dirname(flasgger.__file__), "static"),
            "specs": [
                {
                    "endpoint": "apispec_1",
                    "route": "/apispec_1.json",
                    "rule_filter": lambda rule: True,
                    "model_filter": lambda tag: True,
                }
            ]
        }
        Swagger(self.app, config=swagger_config)

    def setup_routes(self):
        @self.app.route('/favicon.ico')
        def favicon():
            return send_from_directory(
                os.path.join(os.path.dirname(flasgger.__file__), "static"),
                "favicon-32x32.png",
                mimetype="image/png"
            )

        @self.app.route('/tos')
        def terms_of_service():
            license_path = os.path.join(os.path.dirname(__file__), "..", "LICENSE.md")
            with open(license_path, "r", encoding="utf-8") as f:
                license_text = f.read()

            license_html = markdown.markdown(license_text)
            html_content = f"""
            <h1>Terms of Service</h1>
            {license_html}
            """
            return html_content

        @self.app.route('/start_session', methods=['POST'])
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
            try:
                # Синхронный вызов DBLayer.start_session
                session_id = self.db_layer.start_session()
                self.current_session_id = session_id
                print(f"APILayer: Session started with ID: {session_id}")
                return {"status": "success", "session_id": session_id}, 200
            except Exception as e:
                print(f"APILayer: Error starting session: {e}")
                return {"error": "Failed to start session"}, 500

        @self.app.route('/end_session', methods=['POST'])
        def end_session():
            """
            End current session
            ---
            tags:
              - Session
            responses:
              200:
                description: Session ended successfully
                schema:
                  type: object
                  properties:
                    status:
                      type: string
                      example: success
            """
            try:
                self.broker_layer.process_request("end_session", {})
                print("APILayer: End session request sent")
                return {"status": "Session end queued"}, 200
            except Exception as e:
                print(f"APILayer: Error ending session: {e}")
                return {"error": "Failed to end session"}, 500

        @self.app.route('/roll', methods=['POST'])
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
            if not self.current_session_id:
                print("APILayer: Error: No active session! Please start a session with 'start'.")
                return {"error": "No active session"}, 400

                # Получаем сырые данные как строку
            raw_data = request.get_data(as_text=True)
            if not raw_data:
                print("APILayer: Error: No data received")
                return {"error": "No data provided"}, 400

            # Декодируем URL-encoded строку
            decoded_data = unquote(raw_data)
            print("APILayer: Decoded data: " + decoded_data)

            # Проверяем, что данные — это валидный JSON
            try:
                data = json.loads(decoded_data)
            except json.JSONDecodeError:
                print("APILayer: Error: Decoded data is not valid JSON: " + decoded_data)
                return {"error": "Invalid JSON"}, 400

            # Проверяем наличие обязательных полей
            if not all(key in data for key in ["player", "results", "total"]):
                print("APILayer: Error: Missing required fields in JSON: " + decoded_data)
                return {"error": "Missing required fields (player, results, total)"}, 400

            roll_data = {
                "player": data['player'],
                "results": data['results'],
                "total": data['total'],
                "session_id": self.current_session_id
            }
            self.db_layer.record_roll(roll_data)

            try:
                self.broker_layer.process_request("roll", roll_data)
                print(f"APILayer: Roll data sent: {roll_data}")
                return {"status": "success"}, 200
            except Exception as e:
                print(f"APILayer: Error processing roll: {e}")
                return {"error": "Failed to process roll data"}, 500


    def setup_ngrok(self):
        load_dotenv()
        self.NGROK_TOKEN = os.getenv("ngrok")
        # Путь к ngrok.exe в папке ngrok_files
        self.NGROK_PATH = os.path.join(os.path.dirname(__file__), "..", "ngrok_files", "ngrok.exe")
        # Проверяем, существует ли ngrok.exe
        if not os.path.exists(self.NGROK_PATH):
            print(f"Error: ngrok.exe not found at {self.NGROK_PATH}. Please ensure it is placed in the ngrok_files directory.")
            self.NGROK_PATH = None
        self.PORT = 5000
        self.STATIC_DOMAIN = "relieved-firm-titmouse.ngrok-free.app"

    def start_ngrok(self):
        if not self.NGROK_PATH:
            print("APILayer: Cannot start ngrok because ngrok.exe is missing.")
            return None

        # Путь к ngrok.log в папке ngrok_files
        log_file_path = os.path.join(os.path.dirname(__file__), "..", "ngrok_files", "ngrok.log")
        with open(log_file_path, "w") as log_file:
            subprocess.Popen(
                [self.NGROK_PATH, "http", str(self.PORT), "--authtoken", self.NGROK_TOKEN, "--url", self.STATIC_DOMAIN],
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
                    print(f"APILayer: Ngrok tunnel started: {public_url}")
                    print(f"APILayer: Use this endpoint in TTS: {public_url}/roll")
                    print(f"APILayer: Swagger UI available at: {public_url}/apidocs")
                    print(f"APILayer: RabbitMQ at http://localhost:15672")
                    return public_url
            except requests.ConnectionError:
                time.sleep(1)
        print(f"APILayer: Failed to get ngrok URL after 15 seconds. Check {log_file_path} for details.")
        return None

    def run(self):
        self.app.run(host="0.0.0.0", port=self.PORT)
