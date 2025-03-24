import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

class BotLayer:
    def __init__(self):
        # Загружаем переменные из .env
        load_dotenv()
        self.token = os.getenv("TOKEN")
        self.name = os.getenv("NAME")
        self.app_id = os.getenv("ID")

        # Проверяем, что все параметры загружены
        if not self.token or not self.name or not self.app_id:
            raise ValueError("Missing required environment variables: TOKEN, NAME, or ID")

        # Настраиваем префикс команд и интенты
        intents = discord.Intents.default()
        intents.message_content = True  # Для обработки команд через сообщения
        self.bot = commands.Bot(command_prefix="!", intents=intents)

        # Регистрируем событие on_ready
        @self.bot.event
        async def on_ready():
            print(f"BotLayer: {self.bot.user} (ID: {self.app_id}) has connected to Discord!")

    def run(self):
        """Запускает бота с использованием токена."""
        self.bot.run(self.token)