# main_manager.py
import logging
from api_layer import APILayer
from db_layer import DatabaseLayer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

class MainManager:
    def __init__(self):
        self.logger = logging.getLogger("MainManager")
        self.api_layer = None
        self.db_layer = None

    def initialize_db_layer(self):
        self.logger.info("Initializing Database layer...")
        try:
            self.db_layer = DatabaseLayer()
        except Exception as e:
            self.logger.error(f"Failed to initialize Database layer: {e}")
            raise
        return self

    def initialize_api_layer(self):
        self.logger.info("Initializing API layer...")
        try:
            self.api_layer = APILayer(self.db_layer)
        except Exception as e:
            self.logger.error(f"Failed to initialize API layer: {e}")
            raise
        return self

    def start_ngrok(self):
        self.logger.info("Starting ngrok...")
        try:
            self.api_layer.start_ngrok()
        except Exception as e:
            self.logger.error(f"Failed to start ngrok: {e}")
            raise
        return self

    def run_api(self):
        self.logger.info("Starting API layer...")
        try:
            self.api_layer.run()
        except Exception as e:
            self.logger.error(f"Failed to run API layer: {e}")
            raise
        return self

    def run(self):
        self.logger.info("Starting application...")
        self.initialize_db_layer()\
            .initialize_api_layer()\
            .start_ngrok()\
            .run_api()

    def shutdown(self):
        if self.db_layer:
            self.db_layer.close()
        self.logger.info("Application shutdown.")

if __name__ == "__main__":
    manager = MainManager()
    try:
        manager.run()
    except Exception as e:
        manager.logger.error(f"Application failed: {e}")
        manager.shutdown()