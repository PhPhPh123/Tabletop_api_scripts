import psycopg2
from dotenv import load_dotenv
import os

class DatabaseLayer:
    def __init__(self):
        # Загружаем переменные окружения
        load_dotenv()
        db_password = os.getenv("pass")
        if not db_password:
            raise ValueError("Error: 'pass' not found in .env file!")

        # Формируем строку подключения
        db_connection_string = f"postgresql://postgres.gojpkijnnapcvwfsbuzw:{db_password}@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

        # Подключение к базе данных
        try:
            self.conn = psycopg2.connect(db_connection_string)
            self.cursor = self.conn.cursor()
            print("DatabaseLayer: Successfully connected to the database!")
        except Exception as e:
            print(f"DatabaseLayer: Error connecting to the database: {e}")
            raise

    def start_session(self):
        """Создаёт новую сессию в базе данных."""
        try:
            self.cursor.execute("INSERT INTO sessions (session_start) VALUES (CURRENT_TIMESTAMP) RETURNING id")
            session_id = self.cursor.fetchone()[0]
            self.conn.commit()
            print(f"DatabaseLayer: New session created: ID {session_id}")
            return session_id
        except Exception as e:
            self.conn.rollback()
            print(f"DatabaseLayer: Error starting session: {e}")
            raise

    def record_roll(self, roll_data):
        """Записывает данные о броске в базу данных."""
        try:
            player = roll_data['player']
            results = roll_data['results']
            total = roll_data['total']
            session_id = roll_data['session_id']

            # Проверяем/добавляем пользователя
            self.cursor.execute(
                "INSERT INTO users (user_name) VALUES (%s) ON CONFLICT (user_name) DO NOTHING RETURNING id",
                (player,)
            )
            user_id = self.cursor.fetchone()
            if user_id:
                user_id = user_id[0]
            else:
                self.cursor.execute("SELECT id FROM users WHERE user_name = %s", (player,))
                user_id = self.cursor.fetchone()[0]

            # Вставляем бросок
            self.cursor.execute(
                "INSERT INTO rolls (total_result, session_id, user_id, roll_timestamp) VALUES (%s, %s, %s, CURRENT_TIMESTAMP) RETURNING id",
                (total, session_id, user_id)
            )
            roll_id = self.cursor.fetchone()[0]

            # Вставляем результаты кубиков
            for result in results:
                self.cursor.execute(
                    "INSERT INTO dice_results (roll_id, dice_result) VALUES (%s, %s)",
                    (roll_id, result)
                )

            self.conn.commit()
            print(f"DatabaseLayer: Roll recorded: player={player}, results={results}, total={total}, session_id={session_id}")
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"DatabaseLayer: Error recording roll: {e}")
            raise

    def close(self):
        """Закрывает соединение с базой данных."""
        self.cursor.close()
        self.conn.close()
        print("DatabaseLayer: Database connection closed.")