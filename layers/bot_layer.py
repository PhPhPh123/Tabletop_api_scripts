import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import asyncio
from layers.visualization_layer import VisualizationLayer

class BotLayer:
    def __init__(self, db_layer):
        # Загружаем переменные из .env
        load_dotenv()
        self.token = os.getenv("TOKEN")
        self.name = os.getenv("NAME")
        self.app_id = os.getenv("ID")

        # Проверяем, что все параметры загружены
        if not self.token or not self.name or not self.app_id:
            raise ValueError("Missing required environment variables: TOKEN, NAME, or ID")

        # Сохраняем db_layer для передачи в VisualizationLayer
        self.db_layer = db_layer
        self.viz_layer = VisualizationLayer(db_layer)

        # Настраиваем интенты
        intents = discord.Intents.default()
        intents.message_content = True
        intents.presences = True
        intents.members = True
        self.bot = discord.Client(intents=intents)
        self.tree = app_commands.CommandTree(self.bot)

        # Регистрируем событие on_ready
        @self.bot.event
        async def on_ready():
            print(f"BotLayer: {self.bot.user} (ID: {self.app_id}) has connected to Discord!")
            # Синхронизируем команды с Discord
            await self.tree.sync()
            print("Slash commands synced!")

        # Регистрируем слэш-команду /testcharts
        @self.tree.command(name="testcharts", description="Генерирует все тестовые графики и сохраняет их в папку test_all_charts")
        async def test_charts(interaction: discord.Interaction):
            await interaction.response.send_message("Генерирую тестовые графики...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.viz_layer.save_all_plots)
            await interaction.followup.send("Все тестовые графики сохранены в папке test_all_charts.")

        # Регистрируем слэш-команду /sessionavg
        @self.tree.command(name="sessionavg", description="Показывает линейный график средних значений бросков по сессиям")
        @app_commands.describe(by_players="Разделить график по игрокам? (да/нет)")
        @app_commands.choices(by_players=[
            app_commands.Choice(name="Да", value="yes"),
            app_commands.Choice(name="Нет", value="no")
        ])
        async def session_avg(interaction: discord.Interaction, by_players: str = "no"):
            by_players_bool = by_players == "yes"
            await interaction.response.send_message("Генерирую график средних значений по сессиям...")
            loop = asyncio.get_event_loop()
            filename = await loop.run_in_executor(None, self.viz_layer.plot_average_rolls_by_session, by_players_bool)
            with open(f'charts/{filename}', "rb") as f:
                picture = discord.File(f)
                await interaction.followup.send(file=picture)

        # Регистрируем слэш-команду /playeravg
        @self.tree.command(name="playeravg", description="Показывает столбчатую диаграмму средних значений бросков по игрокам")
        @app_commands.describe(session="Выберите сессию для отображения (или оставьте пустым для всех сессий)")
        @app_commands.choices(session=[
            app_commands.Choice(name="Все сессии", value="all"),
            app_commands.Choice(name="Последняя сессия", value="last")
        ])
        async def player_avg(interaction: discord.Interaction, session: str = "all", session_num: int = None):
            last_session = session == "last"
            session_num_value = session_num if session_num is not None else None
            await interaction.response.send_message("Генерирую график средних значений по игрокам...")
            loop = asyncio.get_event_loop()
            filename = await loop.run_in_executor(None, self.viz_layer.plot_average_rolls_by_player, last_session, session_num_value)
            with open(f'charts/{filename}', "rb") as f:
                picture = discord.File(f)
                await interaction.followup.send(file=picture)

        # Регистрируем слэш-команду /critical
        @self.tree.command(name="critical", description="Показывает столбчатую диаграмму критических бросков по игрокам")
        @app_commands.describe(session="Выберите сессию для отображения (или оставьте пустым для всех сессий)")
        @app_commands.choices(session=[
            app_commands.Choice(name="Все сессии", value="all"),
            app_commands.Choice(name="Последняя сессия", value="last")
        ])
        async def critical_rolls(interaction: discord.Interaction, session: str = "all", session_num: int = None):
            last_session = session == "last"
            session_num_value = session_num if session_num is not None else None
            await interaction.response.send_message("Генерирую график критических бросков...")
            loop = asyncio.get_event_loop()
            filename = await loop.run_in_executor(None, self.viz_layer.plot_critical_rolls_by_player, last_session, session_num_value)
            with open(f'charts/{filename}', "rb") as f:
                picture = discord.File(f)
                await interaction.followup.send(file=picture)

        # Регистрируем слэш-команду /help
        @self.tree.command(name="help", description="Показывает список доступных команд и их параметры")
        async def help_command(interaction: discord.Interaction):
            help_text = """
📊 Команды DiceBot 📊

/testcharts
  - Генерирует все возможные варианты графиков и сохраняет их в папку test_all_charts.
  - Пример: /testcharts

/sessionavg
  - Показывает линейный график средних значений бросков по сессиям.
  - Параметры:
    - by_players: Выберите "Да", чтобы разделить график по игрокам (по умолчанию "Нет").
  - Пример: /sessionavg by_players:Да

/playeravg
  - Показывает столбчатую диаграмму средних значений бросков по игрокам.
  - Параметры:
    - session: Выберите "Последняя сессия" или "Все сессии" (по умолчанию "Все сессии").
    - session_num: Укажите номер сессии (необязательно).
  - Примеры:
    - /playeravg
    - /playeravg session:Последняя сессия
    - /playeravg session_num:1

/critical
  - Показывает столбчатую диаграмму критических удач (3-4) и неудач (17-18) по игрокам.
  - Параметры:
    - session: Выберите "Последняя сессия" или "Все сессии" (по умолчанию "Все сессии").
    - session_num: Укажите номер сессии (необязательно).
  - Примеры:
    - /critical
    - /critical session:Последняя сессия
    - /critical session_num:1

/help
  - Показывает это сообщение со списком команд и их параметров.
  - Пример: /help
            """
            await interaction.response.send_message(help_text)

    def run(self):
        """Запускает бота с использованием токена."""
        self.bot.run(self.token)