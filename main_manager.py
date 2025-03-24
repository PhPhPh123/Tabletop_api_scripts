from db_layer import DBLayer
from api_layer import APILayer
from bot_layer import BotLayer
import threading

def main():
    # Инициализация слоёв
    db_layer = DBLayer()
    api_layer = APILayer(db_layer)
    bot_layer = BotLayer()

    # Запуск бота в отдельном потоке
    bot_thread = threading.Thread(target=bot_layer.run)
    bot_thread.daemon = True  # Поток завершится, когда завершится основной процесс
    bot_thread.start()

    # Запуск ngrok
    public_url = api_layer.start_ngrok()
    if not public_url:
        db_layer.close()
        return

    # Запуск Flask-сервера
    try:
        api_layer.run()
    finally:
        db_layer.close()

if __name__ == "__main__":
    main()