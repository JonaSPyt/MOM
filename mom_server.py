import pika
import json
import threading
import time
from copy import deepcopy

TAMANHO_TABULEIRO = 5

class MOMGameServer:
    def __init__(self, host='localhost'):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        self.channel = self.connection.channel()
        self.game_lock = threading.Lock()
        self.players = {}
        self.chat_history = []
        self.game_state_topic = 'game_state_updates'
        self.chat_topic = 'chat_messages'
        self.server_queue = 'game_server_queue'

        # Declare topics (exchanges)
        self.channel.exchange_declare(exchange=self.game_state_topic, exchange_type='fanout', durable=True)
        self.channel.exchange_declare(exchange=self.chat_topic, exchange_type='fanout', durable=True)
        
        # Declare server queue for direct messages from clients
        self.channel.queue_declare(queue=self.server_queue, durable=True)
        self.channel.basic_consume(queue=self.server_queue, on_message_callback=self._process_client_message, auto_ack=True)

        self.reiniciar_jogo()
        
        # Start consuming in a separate thread
        threading.Thread(target=self.channel.start_consuming, daemon=True).start()

    def reiniciar_jogo(self):
        with self.game_lock:
            self.tabuleiro = [['-' for _ in range(TAMANHO_TABULEIRO)] for _ in range(TAMANHO_TABULEIRO)]
            self.bloqueio_central = True
            self.inicializar_centro()
            self.fase = 1
            self.jogador_atual = 'P1'
            self.peças_p1 = 12
            self.peças_p2 = 12
            self.peças_tabuleiro_p1 = 0
            self.peças_tabuleiro_p2 = 0
            self.vencedor = None
            self.contador_colocacao = 0
            self.ultima_peça_capturadora = None
            self.chat_history.clear()
            self._publish_game_state()
            self._publish_chat_message('Server', 'Nova partida iniciada!')

    def inicializar_centro(self):
        self.tabuleiro[2][2] = 'X' if self.bloqueio_central else '-'

    def coordenadas_validas(self, linha, coluna):
        return 0 <= linha < TAMANHO_TABULEIRO and 0 <= coluna < TAMANHO_TABULEIRO

    def _process_client_message(self, ch, method, properties, body):
        try:
            message = json.loads(body)
            msg_type = message.get('type')
            
            if msg_type == 'connect_player':
                player_name = message.get('player_name')
                player_id = self.connect_player(player_name)
                # Send initial game state to the newly connected player
                if player_id:
                    self._send_game_state_to_player(player_name)
            elif msg_type == 'game_action':
                action = message.get('action')
                origem = message.get('origin')
                destino = message.get('destination')
                player_id = message.get('player_id')
                
                if action == 'colocacao':
                    self.place_piece(destino, player_id)
                elif action == 'movimento':
                    self.move_piece(origem, destino, player_id)
            elif msg_type == 'surrender':
                player_id = message.get('player_id')
                self.surrender(player_id)
            elif msg_type == 'chat_message': # Adicionado para processar mensagens de chat
                sender = message.get('sender')
                content = message.get('content')
                self._publish_chat_message(sender, content)
            else:
                print(f"Mensagem de cliente desconhecida: {message}")
        except json.JSONDecodeError:
            print(f"Erro ao decodificar JSON da mensagem do cliente: {body.decode()}")
        except Exception as e:
            print(f"Erro ao processar mensagem do cliente: {e}")

    def connect_player(self, player_name):
        with self.game_lock:
            if len(self.players) >= 2:
                return None # Jogo cheio
            
            player_id = 'P1' if not self.players else 'P2'
            self.players[player_id] = player_name
            print(f"Jogador {player_name} conectado como {player_id}")
            
            # Create a dedicated queue for the player for direct messages/commands
            user_queue_name = f"user_queue_{player_name}"
            self.channel.queue_declare(queue=user_queue_name, durable=True)
            
            self._publish_game_state()
            self._publish_chat_message('Server', f'{player_name} ({player_id}) entrou no jogo.')
            return player_id

    def disconnect_player(self, player_id):
        with self.game_lock:
            player_name = self.players.pop(player_id, None)
            if player_name:
                print(f"Jogador {player_id} ({player_name}) desconectado")
                # Delete the player's queue
                user_queue_name = f"user_queue_{player_name}"
                self.channel.queue_delete(queue=user_queue_name)

                if self.vencedor is None and len(self.players) == 1:
                    remaining_player_id = list(self.players.keys())[0]
                    self.vencedor = remaining_player_id
                    self._publish_chat_message('Server', f'{player_name} desconectou. {self.players[remaining_player_id]} venceu!')
                self._publish_game_state()

    def place_piece(self, destino, player_id):
        with self.game_lock:
            linha, coluna = destino
            if not self.coordenadas_validas(linha, coluna) or self.tabuleiro[linha][coluna] != '-' or (linha, coluna) == (2, 2):
                return False

            if self.jogador_atual != player_id or self.fase != 1:
                return False

            if player_id == 'P1' and self.peças_p1 > 0:
                self.tabuleiro[linha][coluna] = 'P'
                self.peças_p1 -= 1
                self.peças_tabuleiro_p1 += 1
                self.contador_colocacao += 1
            elif player_id == 'P2' and self.peças_p2 > 0:
                self.tabuleiro[linha][coluna] = 'B'
                self.peças_p2 -= 1
                self.peças_tabuleiro_p2 += 1
                self.contador_colocacao += 1
            else:
                return False

            if self.contador_colocacao == 2:
                self.mudar_jogador()
                self.contador_colocacao = 0

            if self.peças_p1 == 0 and self.peças_p2 == 0:
                self.fase = 2
                self.bloqueio_central = False
                self.inicializar_centro()

            self._publish_game_state()
            return True

    def move_piece(self, origem, destino, player_id):
        with self.game_lock:
            if self.jogador_atual != player_id or self.fase != 2:
                return False

            linha_origem, coluna_origem = origem
            linha_destino, coluna_destino = destino

            if not self.coordenadas_validas(linha_origem, coluna_origem) or not self.coordenadas_validas(linha_destino, coluna_destino):
                return False

            peça = self.tabuleiro[linha_origem][coluna_origem]
            if peça == '-' or self.tabuleiro[linha_destino][coluna_destino] != '-':
                return False

            if (player_id == 'P1' and peça != 'P') or (player_id == 'P2' and peça != 'B'):
                return False

            if not self.movimento_valido(origem, destino):
                return False

            self.tabuleiro[linha_origem][coluna_origem] = '-'
            self.tabuleiro[linha_destino][coluna_destino] = peça

            capturas = self.verificar_capturas(destino, player_id)
            if capturas:
                self.ultima_peça_capturadora = destino
                for cap_linha, cap_coluna in capturas:
                    self.tabuleiro[cap_linha][cap_coluna] = '-'
                    if player_id == 'P1':
                        self.peças_tabuleiro_p2 -= 1
                    else:
                        self.peças_tabuleiro_p1 -= 1

            self.verificar_vencedor()
            if not capturas:
                self.mudar_jogador()

            self._publish_game_state()
            return True

    def movimento_valido(self, origem, destino):
        linha_origem, coluna_origem = origem
        linha_destino, coluna_destino = destino

        if linha_origem == linha_destino:
            inicio, fim = min(coluna_origem, coluna_destino), max(coluna_origem, coluna_destino)
            for col in range(inicio + 1, fim):
                if self.tabuleiro[linha_origem][col] != '-':
                    return False
        elif coluna_origem == coluna_destino:
            inicio, fim = min(linha_origem, linha_destino), max(linha_origem, linha_destino)
            for lin in range(inicio + 1, fim):
                if self.tabuleiro[lin][coluna_origem] != '-':
                    return False
        else:
            return False

        return True

    def verificar_capturas(self, posicao, player_id):
        linha, coluna = posicao
        capturas = []
        peça_jogador = 'P' if player_id == 'P1' else 'B'
        peça_oponente = 'B' if player_id == 'P1' else 'P'

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            captura_linha = []
            x, y = linha + dx, coluna + dy

            while self.coordenadas_validas(x, y) and self.tabuleiro[x][y] == peça_oponente:
                captura_linha.append((x, y))
                x, y = x + dx, y + dy

            if self.coordenadas_validas(x, y) and self.tabuleiro[x][y] == peça_jogador and captura_linha:
                capturas.extend(captura_linha)

        return capturas

    def verificar_vencedor(self):
        if self.peças_tabuleiro_p1 <= 2:
            self.vencedor = 'P2'
        elif self.peças_tabuleiro_p2 <= 2:
            self.vencedor = 'P1'

    def mudar_jogador(self):
        self.jogador_atual = 'P2' if self.jogador_atual == 'P1' else 'P1'

    def surrender(self, player_id):
        with self.game_lock:
            if player_id in self.players:
                self.vencedor = 'P2' if player_id == 'P1' else 'P1'
                self._publish_game_state()
                self._publish_chat_message('Server', f'{self.players[player_id]} desistiu. {self.players[self.vencedor]} venceu!')

    def _publish_game_state(self):
        game_state = {
            'tabuleiro': self.tabuleiro,
            'jogador_atual': self.jogador_atual,
            'fase': self.fase,
            'vencedor': self.vencedor,
            'pecas_p1': self.peças_p1,
            'pecas_p2': self.peças_p2,
            'board_pieces_p1': self.peças_tabuleiro_p1,
            'board_pieces_p2': self.peças_tabuleiro_p2,
            'players': self.players
        }
        message = {
            'type': 'game_state',
            'content': game_state
        }
        self.channel.basic_publish(
            exchange=self.game_state_topic,
            routing_key='',
            body=json.dumps(message)
        )

    def _send_game_state_to_player(self, player_name):
        game_state = {
            'tabuleiro': self.tabuleiro,
            'jogador_atual': self.jogador_atual,
            'fase': self.fase,
            'vencedor': self.vencedor,
            'pecas_p1': self.peças_p1,
            'pecas_p2': self.peças_p2,
            'board_pieces_p1': self.peças_tabuleiro_p1,
            'board_pieces_p2': self.peças_tabuleiro_p2,
            'players': self.players
        }
        message = {
            'type': 'game_state',
            'content': game_state
        }
        user_queue_name = f"user_queue_{player_name}"
        self.channel.basic_publish(
            exchange='',
            routing_key=user_queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )

    def _publish_chat_message(self, sender, content):
        message = {
            'type': 'chat_message',
            'sender': sender,
            'content': content
        }
        self.channel.basic_publish(
            exchange=self.chat_topic,
            routing_key='',
            body=json.dumps(message)
        )

    def run(self):
        print("Servidor Seega MOM (RabbitMQ) pronto.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Encerrando servidor...")
        finally:
            self.connection.close()

if __name__ == '__main__':
    server = MOMGameServer()
    server.run()


