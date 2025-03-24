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

    def get_average_rolls_by_session(self, by_players=None):
        if by_players:
            self.cursor.execute("""
                SELECT s.id AS session_id, u.user_name, AVG(r.total_result) AS avg_result
                FROM sessions s
                LEFT JOIN rolls r ON s.id = r.session_id
                LEFT JOIN users u ON r.user_id = u.id
                GROUP BY s.id, u.user_name
                ORDER BY s.id, u.user_name
            """)
        else:
            self.cursor.execute("""
                SELECT s.id AS session_id, AVG(r.total_result) AS avg_result
                FROM sessions s
                LEFT JOIN rolls r ON s.id = r.session_id
                GROUP BY s.id
                ORDER BY s.id
            """)
        return self.cursor.fetchall()

    def get_average_rolls_by_player(self, last_session=None, session_num=None):
        if last_session:
            self.cursor.execute("""
                SELECT u.user_name, AVG(r.total_result) AS avg_result
                FROM rolls r
                JOIN users u ON r.user_id = u.id
                WHERE r.session_id = (SELECT MAX(id) FROM sessions)
                GROUP BY u.user_name
                ORDER BY avg_result
            """)
        elif session_num is not None:
            self.cursor.execute("""
                SELECT u.user_name, AVG(r.total_result) AS avg_result
                FROM rolls r
                JOIN users u ON r.user_id = u.id
                WHERE r.session_id = %s
                GROUP BY u.user_name
                ORDER BY avg_result
            """, (session_num,))
        else:
            self.cursor.execute("""
                SELECT u.user_name, AVG(r.total_result) AS avg_result
                FROM rolls r
                JOIN users u ON r.user_id = u.id
                GROUP BY u.user_name
                ORDER BY avg_result
            """)
        return self.cursor.fetchall()

    def get_critical_rolls_by_player(self, last_session=None, session_num=None):
        """Возвращает количество критических удач (3-4) и неудач (17-18) по игрокам."""
        if last_session:
            self.cursor.execute("""
                SELECT u.user_name,
                       SUM(CASE WHEN r.total_result BETWEEN 3 AND 4 THEN 1 ELSE 0 END) AS critical_success,
                       SUM(CASE WHEN r.total_result BETWEEN 17 AND 18 THEN 1 ELSE 0 END) AS critical_failure
                FROM rolls r
                JOIN users u ON r.user_id = u.id
                WHERE r.session_id = (SELECT MAX(id) FROM sessions)
                GROUP BY u.user_name
            """)
        elif session_num is not None:
            self.cursor.execute("""
                SELECT u.user_name,
                       SUM(CASE WHEN r.total_result BETWEEN 3 AND 4 THEN 1 ELSE 0 END) AS critical_success,
                       SUM(CASE WHEN r.total_result BETWEEN 17 AND 18 THEN 1 ELSE 0 END) AS critical_failure
                FROM rolls r
                JOIN users u ON r.user_id = u.id
                WHERE r.session_id = %s
                GROUP BY u.user_name
            """, (session_num,))
        else:
            self.cursor.execute("""
                SELECT u.user_name,
                       SUM(CASE WHEN r.total_result BETWEEN 3 AND 4 THEN 1 ELSE 0 END) AS critical_success,
                       SUM(CASE WHEN r.total_result BETWEEN 17 AND 18 THEN 1 ELSE 0 END) AS critical_failure
                FROM rolls r
                JOIN users u ON r.user_id = u.id
                GROUP BY u.user_name
            """)
        return self.cursor.fetchall()