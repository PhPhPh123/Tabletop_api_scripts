import psycopg2
from datetime import datetime
from dotenv import load_dotenv
import os

class DBLayer:
    def __init__(self):
        load_dotenv()
        db_password = os.getenv("pass")
        connection_string = f"postgresql://postgres.gojpkijnnapcvwfsbuzw:{db_password}@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
        self.conn = psycopg2.connect(connection_string)
        self.cursor = self.conn.cursor()

    def start_session(self):
        self.cursor.execute(
            "INSERT INTO sessions (session_start) VALUES (%s) RETURNING id",
            (datetime.now(),)
        )
        session_id = self.cursor.fetchone()[0]
        self.conn.commit()
        print(f"DBLayer: Session created with id: {session_id}")
        return session_id

    def get_or_create_user(self, username):
        self.cursor.execute(
            """
            INSERT INTO users (user_name)
            VALUES (%s)
            ON CONFLICT (user_name) DO UPDATE SET user_name = EXCLUDED.user_name
            RETURNING id
            """,
            (username,)
        )
        user_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return user_id

    def record_roll(self, roll_data):
        user_id = self.get_or_create_user(roll_data['player'])
        self.cursor.execute(
            """
            INSERT INTO rolls (user_id, session_id, total_result, roll_timestamp)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (user_id, roll_data['session_id'], roll_data['total'], datetime.now())
        )
        roll_id = self.cursor.fetchone()[0]

        for result in roll_data['results']:
            self.cursor.execute(
                "INSERT INTO dice_results (roll_id, dice_result) VALUES (%s, %s)",
                (roll_id, result)
            )
        self.conn.commit()
        print(f"DBLayer: Roll recorded for player {roll_data['player']}")

    def close(self):
        self.cursor.close()
        self.conn.close()