import pika
import json
from message_utils import get_rabbitmq_connection, close_rabbitmq_connection

class BrokerManager:
    def __init__(self):
        self.users = {}  # Dicionário para armazenar usuários
        self.queues = set()  # Conjunto de filas
        self.topics = set()  # Conjunto de tópicos
        
    def add_queue(self, queue_name):
        """Adiciona uma nova fila"""
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            self.queues.add(queue_name)
            close_rabbitmq_connection(connection)
            print(f"Fila '{queue_name}' adicionada com sucesso.")
            return True
        except Exception as e:
            print(f"Erro ao adicionar fila '{queue_name}': {e}")
            return False
    
    def remove_queue(self, queue_name):
        """Remove uma fila"""
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.queue_delete(queue=queue_name)
            self.queues.discard(queue_name)
            close_rabbitmq_connection(connection)
            print(f"Fila '{queue_name}' removida com sucesso.")
            return True
        except Exception as e:
            print(f"Erro ao remover fila '{queue_name}': {e}")
            return False
    
    def add_topic(self, topic_name):
        """Adiciona um novo tópico (exchange)"""
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.exchange_declare(exchange=topic_name, exchange_type='fanout', durable=True)
            self.topics.add(topic_name)
            close_rabbitmq_connection(connection)
            print(f"Tópico '{topic_name}' adicionado com sucesso.")
            return True
        except Exception as e:
            print(f"Erro ao adicionar tópico '{topic_name}': {e}")
            return False
    
    def remove_topic(self, topic_name):
        """Remove um tópico (exchange)"""
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.exchange_delete(exchange=topic_name)
            self.topics.discard(topic_name)
            close_rabbitmq_connection(connection)
            print(f"Tópico '{topic_name}' removido com sucesso.")
            return True
        except Exception as e:
            print(f"Erro ao remover tópico '{topic_name}': {e}")
            return False
    
    def list_queues(self):
        """Lista todas as filas"""
        print("Filas disponíveis:")
        for queue in self.queues:
            print(f"  - {queue}")
        return list(self.queues)
    
    def list_topics(self):
        """Lista todos os tópicos"""
        print("Tópicos disponíveis:")
        for topic in self.topics:
            print(f"  - {topic}")
        return list(self.topics)
    
    def get_queue_message_count(self, queue_name):
        """Obtém a quantidade de mensagens em uma fila"""
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            method = channel.queue_declare(queue=queue_name, passive=True)
            message_count = method.method.message_count
            close_rabbitmq_connection(connection)
            print(f"Fila '{queue_name}' tem {message_count} mensagens.")
            return message_count
        except Exception as e:
            print(f"Erro ao obter contagem de mensagens da fila '{queue_name}': {e}")
            return -1
    
    def create_user(self, username):
        """Cria um novo usuário e sua fila dedicada"""
        if username in self.users:
            print(f"Usuário '{username}' já existe.")
            return False
        
        user_queue = f"user_{username}"
        if self.add_queue(user_queue):
            self.users[username] = {
                'queue': user_queue,
                'subscribed_topics': set()
            }
            print(f"Usuário '{username}' criado com fila dedicada '{user_queue}'.")
            return True
        else:
            print(f"Erro ao criar usuário '{username}'.")
            return False
    
    def remove_user(self, username):
        """Remove um usuário e sua fila dedicada"""
        if username not in self.users:
            print(f"Usuário '{username}' não existe.")
            return False
        
        user_queue = self.users[username]['queue']
        if self.remove_queue(user_queue):
            del self.users[username]
            print(f"Usuário '{username}' removido.")
            return True
        else:
            print(f"Erro ao remover usuário '{username}'.")
            return False
    
    def list_users(self):
        """Lista todos os usuários"""
        print("Usuários registrados:")
        for username, user_info in self.users.items():
            print(f"  - {username} (fila: {user_info['queue']})")
        return list(self.users.keys())
    
    def get_user_queue(self, username):
        """Obtém a fila de um usuário"""
        if username in self.users:
            return self.users[username]['queue']
        return None
    
    def subscribe_user_to_topic(self, username, topic_name):
        """Inscreve um usuário em um tópico"""
        if username not in self.users:
            print(f"Usuário '{username}' não existe.")
            return False
        
        if topic_name not in self.topics:
            print(f"Tópico '{topic_name}' não existe.")
            return False
        
        self.users[username]['subscribed_topics'].add(topic_name)
        print(f"Usuário '{username}' inscrito no tópico '{topic_name}'.")
        return True
    
    def unsubscribe_user_from_topic(self, username, topic_name):
        """Desinscreve um usuário de um tópico"""
        if username not in self.users:
            print(f"Usuário '{username}' não existe.")
            return False
        
        self.users[username]['subscribed_topics'].discard(topic_name)
        print(f"Usuário '{username}' desinscrito do tópico '{topic_name}'.")
        return True
    
    def get_user_subscribed_topics(self, username):
        """Obtém os tópicos inscritos por um usuário"""
        if username in self.users:
            return list(self.users[username]['subscribed_topics'])
        return []

