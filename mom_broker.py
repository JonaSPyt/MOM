import pika
import json
#ss
class MOMBroker:
    def __init__(self, host='localhost'):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        self.channel = self.connection.channel()
        self.users = {}

    def add_queue(self, queue_name):
        try:
            self.channel.queue_declare(queue=queue_name, durable=True)
            print(f"Fila '{queue_name}' adicionada com sucesso.")
            return True
        except Exception as e:
            print(f"Erro ao adicionar fila '{queue_name}': {e}")
            return False

    def remove_queue(self, queue_name):
        try:
            self.channel.queue_delete(queue=queue_name)
            print(f"Fila '{queue_name}' removida com sucesso.")
            return True
        except Exception as e:
            print(f"Erro ao remover fila '{queue_name}': {e}")
            return False

    def add_topic(self, topic_name):
        try:
            self.channel.exchange_declare(exchange=topic_name, exchange_type='fanout', durable=True)
            print(f"Tópico '{topic_name}' adicionado com sucesso.")
            return True
        except Exception as e:
            print(f"Erro ao adicionar tópico '{topic_name}': {e}")
            return False

    def remove_topic(self, topic_name):
        try:
            self.channel.exchange_delete(exchange=topic_name)
            print(f"Tópico '{topic_name}' removido com sucesso.")
            return True
        except Exception as e:
            print(f"Erro ao remover tópico '{topic_name}': {e}")
            return False

    def list_queues_and_topics(self):
        # Pika's BlockingConnection does not directly support listing all queues/exchanges.
        # This functionality usually requires RabbitMQ Management Plugin API.
        # For this project, we'll simulate by keeping track of created queues/topics or
        # by attempting to declare them (which is idempotent).
        print("Funcionalidade de listar filas e tópicos requer a API de gerenciamento do RabbitMQ.")
        print("Para fins de demonstração, você pode tentar declarar uma fila/tópico para verificar sua existência.")
        # In a real scenario, you would use: 
        # import requests
        # response = requests.get('http://localhost:15672/api/queues', auth=('guest', 'guest'))
        # print(response.json())

    def get_queue_message_count(self, queue_name):
        try:
            # queue_declare with passive=True checks if a queue exists without creating it
            # and returns its properties, including message_count.
            result = self.channel.queue_declare(queue=queue_name, passive=True)
            message_count = result.method.message_count
            print(f"Fila '{queue_name}' tem {message_count} mensagens.")
            return message_count
        except Exception as e:
            print(f"Erro ao obter contagem de mensagens da fila '{queue_name}': {e}")
            return -1

    def instantiate_user_application(self, username):
        if username in self.users:
            print(f"Erro: Usuário '{username}' já existe.")
            return False
        try:
            user_queue_name = f"user_queue_{username}"
            self.add_queue(user_queue_name)
            self.users[username] = {'queue': user_queue_name}
            print(f"Usuário '{username}' instanciado e fila '{user_queue_name}' criada automaticamente.")
            return True
        except Exception as e:
            print(f"Erro ao instanciar usuário '{username}': {e}")
            return False

    def close(self):
        self.connection.close()

if __name__ == '__main__':
    broker = MOMBroker()

    # Testando funcionalidades
    print("\n--- Teste de Filas ---")
    broker.add_queue("fila_teste")
    broker.get_queue_message_count("fila_teste")

    print("\n--- Teste de Tópicos ---")
    broker.add_topic("topico_teste")

    print("\n--- Teste de Usuários ---")
    broker.instantiate_user_application("usuario1")
    broker.instantiate_user_application("usuario2")
    broker.instantiate_user_application("usuario1") # Tentativa de duplicidade

    print("\n--- Listando (simulado) ---")
    broker.list_queues_and_topics()

    print("\n--- Removendo ---")
    broker.remove_queue("fila_teste")
    broker.remove_topic("topico_teste")
    broker.remove_queue("user_queue_usuario1")
    broker.remove_queue("user_queue_usuario2")

    broker.close()


