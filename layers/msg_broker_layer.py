"Данный модуль отвечает за работу брокера сообщений RabbitMQ и осуществляет запись и передачу сообщений"

import pika
import json
import threading
from layers.db_layer import DBLayer

class MsgBrokerLayer:
    def __init__(self, db_layer):
        # Передаём DBLayer для работы с базой
        self.db_layer = db_layer
        self.connection = None
        self.channel = None
        # Словарь обработчиков: (функция, ожидает_ли_данные)
        self.command_handlers = {
            "roll": (self.db_layer.record_roll, True),  # Требует данные
            "end_session": (self.db_layer.end_session, False)  # Не требует данные
        }
        self.connect()

    def connect(self):
        # Подключаемся к RabbitMQ
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()
        # Создаём очереди для каждой команды
        for command in self.command_handlers.keys():
            self.channel.queue_declare(queue=f"{command}_queue", durable=True)
        print("MsgBrokerLayer: Connected to RabbitMQ and queues declared")

    def process_request(self, command, data):
        # Отправляем данные в очередь (Producer)
        if command not in self.command_handlers:
            raise ValueError(f"Unknown command: {command}")
        try:
            queue_name = f"{command}_queue"
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(data).encode(),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            print(f"MsgBrokerLayer: Sent to {queue_name}: {data}")
        except Exception as e:
            print(f"MsgBrokerLayer: Error sending to queue {command}: {e}")
            raise

    def callback(self, command):
        # Универсальный обработчик для всех команд
        def _callback(ch, method, properties, body):
            try:
                # Декодируем сообщение
                data = json.loads(body.decode())
                print(f"MsgBrokerLayer: Received from {command}_queue: {data}")
                # Получаем обработчик и флаг ожидания данных
                handler, expects_data = self.command_handlers[command]
                # Если команда ожидает данные, передаём их, иначе вызываем без аргументов
                if expects_data:
                    handler(data)
                else:
                    handler()
                print(f"MsgBrokerLayer: Processed {command} for data: {data}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"MsgBrokerLayer: Error processing {command}: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        return _callback

    def start_consuming(self):
        # Настройка Consumer’ов
        self.channel.basic_qos(prefetch_count=1)
        for command in self.command_handlers.keys():
            queue_name = f"{command}_queue"
            self.channel.basic_consume(queue=queue_name, on_message_callback=self.callback(command))
            print(f"MsgBrokerLayer: Started consuming from '{queue_name}'")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.stop_consuming()

    def stop_consuming(self):
        # Закрытие соединения
        if self.channel:
            self.channel.close()
        if self.connection:
            self.connection.close()
        print("MsgBrokerLayer: Stopped consuming")

    def run(self):
        # Запуск Consumer’а в потоке
        consumer_thread = threading.Thread(target=self.start_consuming)
        consumer_thread.daemon = True
        consumer_thread.start()
        print("MsgBrokerLayer: Consumer thread started")