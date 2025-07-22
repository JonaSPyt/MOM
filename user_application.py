import pika
import json
import threading
import time
from message_utils import get_rabbitmq_connection, close_rabbitmq_connection

class UserApplication:
    def __init__(self, username, broker_manager=None):
        self.username = username
        self.broker_manager = broker_manager
        self.user_queue = f"user_{username}"
        self.subscribed_topics = set()
        self.listening = False
        self.listener_thread = None
        
    def send_message_to_user(self, target_username, message):
        """Envia mensagem diretamente para outro usuário (produtor)"""
        target_queue = f"user_{target_username}"
        return self._send_message_to_queue(target_queue, message)
    
    def send_message_to_queue(self, queue_name, message):
        """Envia mensagem para uma fila específica"""
        return self._send_message_to_queue(queue_name, message)
    
    def _send_message_to_queue(self, queue_name, message):
        """Método interno para enviar mensagem para fila"""
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            
            # Declara a fila para garantir que existe
            channel.queue_declare(queue=queue_name, durable=True)
            
            # Prepara a mensagem
            message_body = json.dumps({
                'from': self.username,
                'message': message,
                'timestamp': time.time()
            })
            
            # Envia a mensagem
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message_body,
                properties=pika.BasicProperties(delivery_mode=2)  # Torna a mensagem persistente
            )
            
            close_rabbitmq_connection(connection)
            print(f"[{self.username}] Mensagem enviada para fila '{queue_name}': {message}")
            return True
            
        except Exception as e:
            print(f"[{self.username}] Erro ao enviar mensagem para fila '{queue_name}': {e}")
            return False
    
    def receive_message_from_queue(self, queue_name, timeout=5):
        """Recebe uma mensagem de uma fila específica (consumidor)"""
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            
            # Declara a fila para garantir que existe
            channel.queue_declare(queue=queue_name, durable=True)
            
            # Tenta receber uma mensagem
            method_frame, header_frame, body = channel.basic_get(queue=queue_name, auto_ack=True)
            
            if method_frame:
                message_data = json.loads(body.decode())
                print(f"[{self.username}] Mensagem recebida da fila '{queue_name}': {message_data['message']} (de: {message_data['from']})")
                close_rabbitmq_connection(connection)
                return message_data
            else:
                print(f"[{self.username}] Nenhuma mensagem disponível na fila '{queue_name}'.")
                close_rabbitmq_connection(connection)
                return None
                
        except Exception as e:
            print(f"[{self.username}] Erro ao receber mensagem da fila '{queue_name}': {e}")
            return None
    
    def receive_messages_from_user_queue(self, timeout=5):
        """Recebe mensagens da própria fila do usuário"""
        return self.receive_message_from_queue(self.user_queue, timeout)
    
    def publish_message_to_topic(self, topic_name, message):
        """Publica mensagem em um tópico (publisher)"""
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            
            # Declara o exchange (tópico) para garantir que existe
            channel.exchange_declare(exchange=topic_name, exchange_type='fanout', durable=True)
            
            # Prepara a mensagem
            message_body = json.dumps({
                'from': self.username,
                'message': message,
                'timestamp': time.time()
            })
            
            # Publica a mensagem
            channel.basic_publish(
                exchange=topic_name,
                routing_key='',
                body=message_body,
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            close_rabbitmq_connection(connection)
            print(f"[{self.username}] Mensagem publicada no tópico '{topic_name}': {message}")
            return True
            
        except Exception as e:
            print(f"[{self.username}] Erro ao publicar mensagem no tópico '{topic_name}': {e}")
            return False
    
    def subscribe_to_topic(self, topic_name):
        """Inscreve-se em um tópico (subscriber)"""
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            
            # Declara o exchange (tópico)
            channel.exchange_declare(exchange=topic_name, exchange_type='fanout', durable=True)
            
            # Cria uma fila temporária exclusiva para este subscriber
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            
            # Vincula a fila ao exchange
            channel.queue_bind(exchange=topic_name, queue=queue_name)
            
            self.subscribed_topics.add(topic_name)
            
            # Atualiza no broker manager se disponível
            if self.broker_manager:
                self.broker_manager.subscribe_user_to_topic(self.username, topic_name)
            
            close_rabbitmq_connection(connection)
            print(f"[{self.username}] Inscrito no tópico '{topic_name}'.")
            return True
            
        except Exception as e:
            print(f"[{self.username}] Erro ao se inscrever no tópico '{topic_name}': {e}")
            return False
    
    def unsubscribe_from_topic(self, topic_name):
        """Desinscreve-se de um tópico"""
        self.subscribed_topics.discard(topic_name)
        
        # Atualiza no broker manager se disponível
        if self.broker_manager:
            self.broker_manager.unsubscribe_user_from_topic(self.username, topic_name)
        
        print(f"[{self.username}] Desinscrito do tópico '{topic_name}'.")
        return True
    
    def start_topic_listener(self, topic_name):
        """Inicia um listener para um tópico específico"""
        def listen_to_topic():
            try:
                connection = get_rabbitmq_connection()
                channel = connection.channel()
                
                # Declara o exchange
                channel.exchange_declare(exchange=topic_name, exchange_type='fanout', durable=True)
                
                # Cria uma fila temporária exclusiva
                result = channel.queue_declare(queue='', exclusive=True)
                queue_name = result.method.queue
                
                # Vincula a fila ao exchange
                channel.queue_bind(exchange=topic_name, queue=queue_name)
                
                def callback(ch, method, properties, body):
                    try:
                        message_data = json.loads(body.decode())
                        if message_data['from'] != self.username:  # Não processa suas próprias mensagens
                            print(f"[{self.username}] Mensagem recebida do tópico '{topic_name}': {message_data['message']} (de: {message_data['from']})")
                    except Exception as e:
                        print(f"[{self.username}] Erro ao processar mensagem do tópico: {e}")
                
                channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
                
                print(f"[{self.username}] Ouvindo tópico '{topic_name}'. Para parar, pressione CTRL+C")
                channel.start_consuming()
                
            except Exception as e:
                print(f"[{self.username}] Erro no listener do tópico '{topic_name}': {e}")
        
        self.listener_thread = threading.Thread(target=listen_to_topic, daemon=True)
        self.listener_thread.start()
        self.listening = True
    
    def stop_topic_listener(self):
        """Para o listener de tópicos"""
        self.listening = False
        if self.listener_thread and self.listener_thread.is_alive():
            print(f"[{self.username}] Parando listener de tópicos...")
    
    def start_queue_listener(self, queue_name=None):
        """Inicia um listener para uma fila específica (padrão: fila do usuário)"""
        if queue_name is None:
            queue_name = self.user_queue
            
        def listen_to_queue():
            try:
                connection = get_rabbitmq_connection()
                channel = connection.channel()
                
                # Declara a fila
                channel.queue_declare(queue=queue_name, durable=True)
                
                def callback(ch, method, properties, body):
                    try:
                        message_data = json.loads(body.decode())
                        print(f"[{self.username}] Mensagem recebida da fila '{queue_name}': {message_data['message']} (de: {message_data['from']})")
                    except Exception as e:
                        print(f"[{self.username}] Erro ao processar mensagem da fila: {e}")
                
                channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
                
                print(f"[{self.username}] Ouvindo fila '{queue_name}'. Para parar, pressione CTRL+C")
                channel.start_consuming()
                
            except Exception as e:
                print(f"[{self.username}] Erro no listener da fila '{queue_name}': {e}")
        
        self.listener_thread = threading.Thread(target=listen_to_queue, daemon=True)
        self.listener_thread.start()
        self.listening = True
    
    def get_subscribed_topics(self):
        """Retorna a lista de tópicos inscritos"""
        return list(self.subscribed_topics)

