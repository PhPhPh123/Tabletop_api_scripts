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


class APILayer:
    def __init__(self, db_layer):
        self.app = Flask(__name__)
        self.db_layer = db_layer
        self.current_session_id = 0
        self.setup_swagger()
        self.setup_routes()
        self.setup_ngrok()

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
            license_path = os.path.join(os.path.dirname(__file__), "LICENSE.md")
            if not os.path.exists(license_path):
                return "<h1>Error</h1><p>License file not found!</p>", 404

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
            print("APILayer: Received /start_session request")
            session_id = self.db_layer.start_session()
            self.current_session_id = session_id
            print(f"APILayer: Session started, session_id: {session_id}")
            return {"status": "success"}, 200

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
            print("APILayer: Received /roll request")
            if not self.current_session_id:
                print("APILayer: Error: No active session! Please start a session with 'start'.")
                return {"error": "No active session"}, 400

            raw_body = request.get_data(as_text=True)
            print(f"APILayer: Raw request body: {raw_body}")
            decoded_body = urllib.parse.unquote(raw_body)
            print(f"APILayer: Decoded body: {decoded_body}")
            try:
                data = json.loads(decoded_body)
            except json.JSONDecodeError as e:
                print(f"APILayer: Error decoding JSON: {e}")
                return {"error": "Invalid JSON"}, 400

            roll_data = {
                "player": data['player'],
                "results": data['results'],
                "total": data['total'],
                "session_id": self.current_session_id
            }
            self.db_layer.record_roll(roll_data)

            print(
                f"APILayer: Roll received: player={data['player']}, results={data['results']}, total={data['total']}, session_id={self.current_session_id}")
            return {"status": "success"}, 200

    def setup_ngrok(self):
        load_dotenv()
        self.NGROK_TOKEN = os.getenv("ngrok")
        self.NGROK_PATH = os.path.join(os.path.dirname(__file__), "ngrok.exe")
        self.PORT = 5000
        self.STATIC_DOMAIN = "relieved-firm-titmouse.ngrok-free.app"

    def start_ngrok(self):
        if not os.path.exists(self.NGROK_PATH):
            print(f"APILayer: Error: {self.NGROK_PATH} not found!")
            return None
        if not self.NGROK_TOKEN:
            print("APILayer: Error: NGROK_TOKEN not found in .env!")
            return None
        print(f"APILayer: Starting ngrok with token at {self.NGROK_PATH}...")
        with open("ngrok.log", "w") as log_file:
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
                    return public_url
            except requests.ConnectionError:
                time.sleep(1)
        print("APILayer: Failed to get ngrok URL after 15 seconds. Check ngrok.log.")
        return None

    def run(self):
        self.app.run(host="0.0.0.0", port=self.PORT)