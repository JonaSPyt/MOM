import pika
import json
import threading
import time

class MOMClient:
    def __init__(self, username, host="localhost"):
        self.username = username
        self.host = host
        self.connection = None
        self.channel = None
        self.game_state_callback = None
        self.chat_message_callback = None
        self.user_queue = f"user_queue_{username}"
        self.connected = False

    def connect(self):
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.user_queue, durable=True)
            
            # Subscribe to game state updates topic
            self.channel.exchange_declare(exchange='game_state_updates', exchange_type='fanout', durable=True)
            result = self.channel.queue_declare(queue="", exclusive=True)
            game_state_queue = result.method.queue
            self.channel.queue_bind(exchange='game_state_updates', queue=game_state_queue)
            self.channel.basic_consume(queue=game_state_queue, on_message_callback=self._process_message, auto_ack=True)
            
            # Subscribe to chat messages topic
            self.channel.exchange_declare(exchange='chat_messages', exchange_type='fanout', durable=True)
            result = self.channel.queue_declare(queue="", exclusive=True)
            chat_queue = result.method.queue
            self.channel.queue_bind(exchange='chat_messages', queue=chat_queue)
            self.channel.basic_consume(queue=chat_queue, on_message_callback=self._process_message, auto_ack=True)
            
            self.connected = True
            print(f"Cliente {self.username} conectado ao broker MOM.")
            return True
        except Exception as e:
            print(f"Erro ao conectar o cliente {self.username} ao broker MOM: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
            self.connected = False
            print(f"Cliente {self.username} desconectado do broker MOM.")

    def send_message_to_user(self, target_queue, message_content):
        if not self.connected:
            print("Cliente não conectado ao broker.")
            return
        try:
            self.channel.basic_publish(
                exchange="",
                routing_key=target_queue,
                body=message_content,
                properties=pika.BasicProperties(delivery_mode=2) # make message persistent
            )
            print(f"Mensagem direta de {self.username} para {target_queue} enviada.")
        except Exception as e:
            print(f"Erro ao enviar mensagem direta: {e}")

    def publish_to_topic(self, topic_name, message_content):
        if not self.connected:
            print("Cliente não conectado ao broker.")
            return
        try:
            message = {
                "sender": self.username,
                "type": "topic_message",
                "content": message_content
            }
            self.channel.basic_publish(
                exchange=topic_name,
                routing_key="",
                body=json.dumps(message)
            )
            print(f"Mensagem de {self.username} para o tópico {topic_name} publicada.")
        except Exception as e:
            print(f"Erro ao publicar em tópico: {e}")

    def subscribe_to_topic(self, topic_name, callback):
        if not self.connected:
            print("Cliente não conectado ao broker.")
            return
        try:
            result = self.channel.queue_declare(queue="", exclusive=True)
            queue_name = result.method.queue
            self.channel.queue_bind(exchange=topic_name, queue=queue_name)
            self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            print(f"Cliente {self.username} inscrito no tópico {topic_name}.")
        except Exception as e:
            print(f"Erro ao assinar tópico: {e}")

    def start_consuming_user_queue(self, callback):
        if not self.connected:
            print("Cliente não conectado ao broker.")
            return
        try:
            self.channel.basic_consume(queue=self.user_queue, on_message_callback=callback, auto_ack=True)
            print(f"Cliente {self.username} começando a consumir da fila {self.user_queue}.")
        except Exception as e:
            print(f"Erro ao iniciar consumo da fila do usuário: {e}")

    def set_game_state_callback(self, callback):
        self.game_state_callback = callback

    def set_chat_message_callback(self, callback):
        self.chat_message_callback = callback

    def _process_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            msg_type = message.get("type")
            if msg_type == "game_state":
                if self.game_state_callback:
                    self.game_state_callback(message.get("content"))
            elif msg_type == "chat_message":
                if self.chat_message_callback:
                    self.chat_message_callback(message.get("sender"), message.get("content"))
            elif msg_type == "direct_message":
                print(f"Mensagem direta de {message.get('sender')}: {message.get('content')}")
                if self.chat_message_callback:
                    self.chat_message_callback(message.get('sender'), message.get('content'))
            elif msg_type == "topic_message":
                print(f"Mensagem de tópico de {message.get('sender')}: {message.get('content')}")
                if self.chat_message_callback:
                    self.chat_message_callback(message.get('sender'), message.get('content'))
            else:
                print(f"Mensagem desconhecida recebida: {message}")
        except json.JSONDecodeError:
            print(f"Erro ao decodificar JSON: {body.decode()}")
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")

    def start_listening(self):
        if not self.connected:
            print("Cliente não conectado ao broker.")
            return
        try:
            # Consumir da fila do usuário para mensagens diretas e de controle
            self.channel.basic_consume(queue=self.user_queue, on_message_callback=self._process_message, auto_ack=True)
            print(f"Começando a escutar mensagens na fila {self.user_queue}...")
            self.channel.start_consuming()
        except Exception as e:
            print(f"Erro ao iniciar escuta: {e}")

if __name__ == "__main__":
    # Exemplo de uso
    client1 = MOMClient("usuario_teste1")
    client2 = MOMClient("usuario_teste2")

    if client1.connect() and client2.connect():
        # Definir callbacks para chat
        def chat_callback1(sender, content):
            print(f"[Chat - {client1.username}] De {sender}: {content}")

        def chat_callback2(sender, content):
            print(f"[Chat - {client2.username}] De {sender}: {content}")

        client1.set_chat_message_callback(chat_callback1)
        client2.set_chat_message_callback(chat_callback2)

        # Iniciar consumo das filas de usuário em threads separadas
        threading.Thread(target=client1.start_listening, daemon=True).start()
        threading.Thread(target=client2.start_listening, daemon=True).start()

        time.sleep(2) # Dar um tempo para as conexões e consumos se estabelecerem

        # Testar envio de mensagem direta
        client1.send_message_to_user("user_queue_usuario_teste2", json.dumps({"type": "direct_message", "sender": client1.username, "content": "Olá, usuário 2! Esta é uma mensagem direta."}))
        time.sleep(1)

        # Testar publicação em tópico
        client1.publish_to_topic("topico_geral", "Mensagem para o tópico geral!")
        time.sleep(1)

        # Assinar tópico
        client2.subscribe_to_topic("topico_geral", lambda ch, method, properties, body: chat_callback2("Tópico", json.loads(body).get('content')))
        time.sleep(1)

        client1.publish_to_topic("topico_geral", "Outra mensagem para o tópico geral!")
        time.sleep(1)

        # Manter o programa rodando para receber mensagens
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Encerrando clientes.")
        finally:
            client1.disconnect()
            client2.disconnect()

