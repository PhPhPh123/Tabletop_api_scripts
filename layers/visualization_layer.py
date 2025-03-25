import matplotlib
matplotlib.use("Agg")  # Устанавливаем бэкенд Agg (потокобезопасный)
import pandas as pd
import matplotlib.pyplot as plt
import os

class VisualizationLayer:
    def __init__(self, db_layer):
        self.db_layer = db_layer

    def plot_average_rolls_by_session(self, by_players=None, filename="average_rolls_by_session.png"):
        """Линейный график средних значений бросков по сессиям."""
        plt.figure(figsize=(8, 6))
        data = self.db_layer.get_average_rolls_by_session(by_players)

        if by_players:
            df = pd.DataFrame(data, columns=["session_id", "user_name", "avg_result"])
            for user in df["user_name"].unique():
                user_data = df[df["user_name"] == user]
                plt.plot(user_data["session_id"], user_data["avg_result"], marker="o", label=user)
            plt.legend(title="Players")
        else:
            df = pd.DataFrame(data, columns=["session_id", "avg_result"])
            plt.plot(df["session_id"], df["avg_result"], marker="o")

        plt.xlabel("Session ID")
        plt.ylabel("Average Roll Result")
        plt.title("Average Roll Result by Session")
        plt.grid(True)
        plt.savefig(f'charts/{filename}')
        plt.close()

        return filename

    def plot_average_rolls_by_player(self, last_session=None, session_num=None, filename="average_rolls_by_player.png"):
        """Bar-диаграмма средних значений бросков по игрокам."""
        plt.figure(figsize=(8, 6))
        data = self.db_layer.get_average_rolls_by_player(last_session, session_num)
        df = pd.DataFrame(data, columns=["user_name", "avg_result"])

        plt.bar(df["user_name"], df["avg_result"])
        plt.xlabel("Player")
        plt.ylabel("Average Roll Result")
        plt.title("Average Roll Result by Player" +
                  (" (Last Session)" if last_session else f" (Session {session_num})" if session_num is not None else ""))
        plt.xticks(rotation=45)
        plt.savefig(f'charts/{filename}')
        plt.close()

        return filename

    def plot_critical_rolls_by_player(self, last_session=None, session_num=None, filename="critical_rolls_by_player.png"):
        """Bar-диаграмма критических удач и неудач по игрокам."""
        plt.figure(figsize=(8, 6))
        data = self.db_layer.get_critical_rolls_by_player(last_session, session_num)
        df = pd.DataFrame(data, columns=["user_name", "critical_success", "critical_failure"])

        bar_width = 0.35
        x = range(len(df["user_name"]))
        plt.bar(x, df["critical_success"], bar_width, label="Critical Success (3-4)", color="green")
        plt.bar([i + bar_width for i in x], df["critical_failure"], bar_width, label="Critical Failure (17-18)", color="red")
        plt.xlabel("Player")
        plt.ylabel("Count")
        plt.title("Critical Rolls by Player" +
                  (" (Last Session)" if last_session else f" (Session {session_num})" if session_num is not None else ""))
        plt.xticks([i + bar_width / 2 for i in x], df["user_name"], rotation=45)
        plt.legend()
        plt.savefig(f'charts/{filename}')
        plt.close()

        return filename

    def plot_session_durations(self, by_week=False, filename="session_durations.png"):
        plt.figure(figsize=(10, 6))

        if by_week:
            # Вариант 2: по неделям
            data = self.db_layer.get_weekly_session_durations()
            df = pd.DataFrame(data, columns=["week_start", "total_hours"])
            plt.plot(df["week_start"], df["total_hours"], marker="o")
            plt.xlabel("Неделя")
            plt.ylabel("Общая длительность (часы)")
            plt.title("Длительность игровых сессий по неделям")
            plt.xticks(rotation=45)
        else:
            # Вариант 1: по сессиям
            data = self.db_layer.get_session_durations()
            df = pd.DataFrame(data, columns=["session_id", "duration_hours"])
            plt.plot(df["session_id"], df["duration_hours"], marker="o")
            plt.xlabel("номер сессии")
            plt.ylabel("Длительность (часы)")
            plt.title("Длительность игровых сессий")

        # Добавляем форматирование оси Y для отображения только целых чисел
        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(integer=True))

        plt.grid(True)
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        return filename

    def save_all_plots(self):
        """Сохраняет все вариации графиков в папку test_all_charts."""
        os.makedirs("../test_all_charts", exist_ok=True)

        self.plot_average_rolls_by_session(filename="../test_all_charts/average_rolls_by_session.png")
        self.plot_average_rolls_by_session(by_players=True, filename="../test_all_charts/average_rolls_by_session_by_players.png")
        self.plot_average_rolls_by_player(filename="../test_all_charts/average_rolls_by_player.png")
        self.plot_average_rolls_by_player(last_session=True, filename="../test_all_charts/average_rolls_by_player_last_session.png")
        self.plot_average_rolls_by_player(session_num=1, filename="../test_all_charts/average_rolls_by_player_session_1.png")
        self.plot_critical_rolls_by_player(filename="../test_all_charts/critical_rolls_by_player.png")
        self.plot_critical_rolls_by_player(last_session=True, filename="../test_all_charts/critical_rolls_by_player_last_session.png")
        self.plot_critical_rolls_by_player(session_num=1, filename="../test_all_charts/critical_rolls_by_player_session_1.png")
        print("All plots saved in test_all_charts directory.")