#!/usr/bin/env python3
"""
Sistema de Gerenciamento e Utilização de Comunicação por Mensagens (MOM)
Baseado nos requisitos do projeto e códigos Java fornecidos
"""

import sys
import time
from broker_manager import BrokerManager
from user_application import UserApplication

def print_menu():
    print("\n" + "="*50)
    print("    SISTEMA MOM - MENU PRINCIPAL")
    print("="*50)
    print("1. Gerenciar Broker")
    print("2. Gerenciar Usuários")
    print("3. Testar Comunicação")
    print("4. Sair")
    print("-"*50)

def print_broker_menu():
    print("\n" + "="*50)
    print("    GERENCIAMENTO DO BROKER")
    print("="*50)
    print("1. Adicionar Fila")
    print("2. Remover Fila")
    print("3. Adicionar Tópico")
    print("4. Remover Tópico")
    print("5. Listar Filas")
    print("6. Listar Tópicos")
    print("7. Contar Mensagens em Fila")
    print("8. Voltar ao Menu Principal")
    print("-"*50)

def print_user_menu():
    print("\n" + "="*50)
    print("    GERENCIAMENTO DE USUÁRIOS")
    print("="*50)
    print("1. Criar Usuário")
    print("2. Remover Usuário")
    print("3. Listar Usuários")
    print("4. Voltar ao Menu Principal")
    print("-"*50)

def print_communication_menu():
    print("\n" + "="*50)
    print("    TESTE DE COMUNICAÇÃO")
    print("="*50)
    print("1. Enviar Mensagem entre Usuários")
    print("2. Receber Mensagens de Usuário")
    print("3. Publicar Mensagem em Tópico")
    print("4. Inscrever Usuário em Tópico")
    print("5. Iniciar Listener de Tópico")
    print("6. Iniciar Listener de Fila")
    print("7. Voltar ao Menu Principal")
    print("-"*50)

def manage_broker(broker_manager):
    while True:
        print_broker_menu()
        choice = input("Escolha uma opção: ").strip()
        
        if choice == '1':
            queue_name = input("Nome da fila: ").strip()
            broker_manager.add_queue(queue_name)
        
        elif choice == '2':
            queue_name = input("Nome da fila: ").strip()
            broker_manager.remove_queue(queue_name)
        
        elif choice == '3':
            topic_name = input("Nome do tópico: ").strip()
            broker_manager.add_topic(topic_name)
        
        elif choice == '4':
            topic_name = input("Nome do tópico: ").strip()
            broker_manager.remove_topic(topic_name)
        
        elif choice == '5':
            broker_manager.list_queues()
        
        elif choice == '6':
            broker_manager.list_topics()
        
        elif choice == '7':
            queue_name = input("Nome da fila: ").strip()
            broker_manager.get_queue_message_count(queue_name)
        
        elif choice == '8':
            break
        
        else:
            print("Opção inválida!")

def manage_users(broker_manager):
    while True:
        print_user_menu()
        choice = input("Escolha uma opção: ").strip()
        
        if choice == '1':
            username = input("Nome do usuário: ").strip()
            broker_manager.create_user(username)
        
        elif choice == '2':
            username = input("Nome do usuário: ").strip()
            broker_manager.remove_user(username)
        
        elif choice == '3':
            broker_manager.list_users()
        
        elif choice == '4':
            break
        
        else:
            print("Opção inválida!")

def test_communication(broker_manager):
    while True:
        print_communication_menu()
        choice = input("Escolha uma opção: ").strip()
        
        if choice == '1':
            sender = input("Nome do usuário remetente: ").strip()
            receiver = input("Nome do usuário destinatário: ").strip()
            message = input("Mensagem: ").strip()
            
            if sender in broker_manager.users:
                user_app = UserApplication(sender, broker_manager)
                user_app.send_message_to_user(receiver, message)
            else:
                print(f"Usuário '{sender}' não existe.")
        
        elif choice == '2':
            username = input("Nome do usuário: ").strip()
            
            if username in broker_manager.users:
                user_app = UserApplication(username, broker_manager)
                message = user_app.receive_messages_from_user_queue()
                if not message:
                    print("Nenhuma mensagem disponível.")
            else:
                print(f"Usuário '{username}' não existe.")
        
        elif choice == '3':
            publisher = input("Nome do usuário publicador: ").strip()
            topic_name = input("Nome do tópico: ").strip()
            message = input("Mensagem: ").strip()
            
            if publisher in broker_manager.users:
                user_app = UserApplication(publisher, broker_manager)
                user_app.publish_message_to_topic(topic_name, message)
            else:
                print(f"Usuário '{publisher}' não existe.")
        
        elif choice == '4':
            username = input("Nome do usuário: ").strip()
            topic_name = input("Nome do tópico: ").strip()
            
            if username in broker_manager.users:
                user_app = UserApplication(username, broker_manager)
                user_app.subscribe_to_topic(topic_name)
            else:
                print(f"Usuário '{username}' não existe.")
        
        elif choice == '5':
            username = input("Nome do usuário: ").strip()
            topic_name = input("Nome do tópico: ").strip()
            
            if username in broker_manager.users:
                user_app = UserApplication(username, broker_manager)
                user_app.start_topic_listener(topic_name)
                print("Listener iniciado. Pressione Enter para parar...")
                input()
                user_app.stop_topic_listener()
            else:
                print(f"Usuário '{username}' não existe.")
        
        elif choice == '6':
            username = input("Nome do usuário: ").strip()
            queue_name = input("Nome da fila (deixe vazio para usar a fila do usuário): ").strip()
            
            if username in broker_manager.users:
                user_app = UserApplication(username, broker_manager)
                if queue_name:
                    user_app.start_queue_listener(queue_name)
                else:
                    user_app.start_queue_listener()
                print("Listener iniciado. Pressione Enter para parar...")
                input()
                user_app.stop_topic_listener()
            else:
                print(f"Usuário '{username}' não existe.")
        
        elif choice == '7':
            break
        
        else:
            print("Opção inválida!")

def main():
    print("Iniciando Sistema MOM...")
    
    # Inicializa o gerenciador do broker
    broker_manager = BrokerManager()
    
    # Cria alguns usuários e recursos de exemplo
    print("\nConfigurando ambiente de exemplo...")
    broker_manager.create_user("alice")
    broker_manager.create_user("bob")
    broker_manager.add_topic("noticias")
    broker_manager.add_topic("chat_geral")
    broker_manager.add_queue("fila_publica")
    
    print("Sistema MOM iniciado com sucesso!")
    
    while True:
        try:
            print_menu()
            choice = input("Escolha uma opção: ").strip()
            
            if choice == '1':
                manage_broker(broker_manager)
            
            elif choice == '2':
                manage_users(broker_manager)
            
            elif choice == '3':
                test_communication(broker_manager)
            
            elif choice == '4':
                print("Encerrando sistema...")
                break
            
            else:
                print("Opção inválida!")
        
        except KeyboardInterrupt:
            print("\n\nEncerrando sistema...")
            break
        except Exception as e:
            print(f"Erro: {e}")

if __name__ == "__main__":
    main()

