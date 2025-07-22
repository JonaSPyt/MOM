import pika

def get_rabbitmq_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    return connection

def close_rabbitmq_connection(connection):
    connection.close()


