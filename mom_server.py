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

    def verificar_movimento_valido(self, origem, destino):
        origem_linha, origem_coluna = origem
        destino_linha, destino_coluna = destino

        if origem_linha != destino_linha and origem_coluna != destino_coluna:
            return False

        passo_linha = 0 if origem_linha == destino_linha else (1 if destino_linha > origem_linha else -1)
        passo_coluna = 0 if origem_coluna == destino_coluna else (1 if destino_coluna > origem_coluna else -1)
        
        x, y = origem_linha + passo_linha, origem_coluna + passo_coluna
        while (x, y) != (destino_linha, destino_coluna):
            if self.tabuleiro[x][y] != '-' and (x,y) != origem:
                return False
            x += passo_linha
            y += passo_coluna

        return self.tabuleiro[destino_linha][destino_coluna] == '-'

    def move_piece(self, origem, destino, player_id):
        with self.game_lock:
            if self.fase != 2 or self.jogador_atual != player_id:
                return False

            if not self.verificar_movimento_valido(origem, destino):
                return False

            peça = self.tabuleiro[origem[0]][origem[1]]
            self.tabuleiro[origem[0]][origem[1]] = '-'
            self.tabuleiro[destino[0]][destino[1]] = peça

            capturas = self.verificar_capturas_sanduiche(destino)
            for x, y in capturas:
                self.tabuleiro[x][y] = '-'
                if self.jogador_atual == 'P1':
                    self.peças_tabuleiro_p2 -= 1
                else:
                    self.peças_tabuleiro_p1 -= 1

            self.verificar_vencedor()
            if not capturas:
                self.mudar_jogador()
            else:
                self.ultima_peça_capturadora = destino
            
            self._publish_game_state()
            return True

    def verificar_capturas_sanduiche(self, destino):
        capturas = []
        jogador = 'P' if self.jogador_atual == 'P1' else 'B'
        inimigo = 'B' if jogador == 'P' else 'P'
        direcoes = [(-1,0), (1,0), (0,-1), (0,1)]
        
        for dx, dy in direcoes:
            x, y = destino[0] + dx, destino[1] + dy
            x2, y2 = x + dx, y + dy
            if self.coordenadas_validas(x, y) and self.coordenadas_validas(x2, y2):
                if self.tabuleiro[x][y] == inimigo and self.tabuleiro[x2][y2] == jogador:
                    capturas.append((x, y))
        return capturas

    def mudar_jogador(self):
        self.jogador_atual = 'P2' if self.jogador_atual == 'P1' else 'P1'
        self.ultima_peça_capturadora = None

    def verificar_vencedor(self):
        if self.peças_tabuleiro_p1 == 0:
            self.vencedor = 'P2'
        elif self.peças_tabuleiro_p2 == 0:
            self.vencedor = 'P1'

    def send_chat_message(self, sender, message):
        with self.game_lock:
            full_message = f'{sender}: {message}'
            self.chat_history.append(full_message)
            self._publish_chat_message(sender, message)
            print(f"Chat: {full_message}")

    def _publish_game_state(self):
        state = {
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
        self.channel.basic_publish(
            exchange=self.game_state_topic,
            routing_key='',
            body=json.dumps({'type': 'game_state', 'content': state})
        )

    def _send_game_state_to_player(self, player_name):
        state = {
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
            'content': state
        }
        self.channel.basic_publish(
            exchange='',
            routing_key=f"user_queue_{player_name}",
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2) # make message persistent
        )

    def _publish_chat_message(self, sender, message):
        msg = {
            'sender': sender,
            'type': 'chat_message',
            'content': message
        }
        self.channel.basic_publish(
            exchange=self.chat_topic,
            routing_key='',
            body=json.dumps(msg)
        )

    def surrender(self, player_id):
        with self.game_lock:
            if player_id == 'P1':
                self.vencedor = 'P2'
            elif player_id == 'P2':
                self.vencedor = 'P1'
            
            player_name = self.players.get(player_id, f"Jogador {player_id}")
            surrender_message = f'{player_name} desistiu da partida!'
            self.chat_history.append(surrender_message)
            self._publish_chat_message('Server', surrender_message)
            self._publish_game_state()
            print(f"Jogador {player_id} ({player_name}) desistiu")

    def close(self):
        self.connection.close()


if __name__ == '__main__':
    server = MOMGameServer()
    print("Servidor Seega MOM (RabbitMQ) pronto.")
    
    # Keep the server running. The server will consume messages in a separate thread.
    try:
        while True:
            time.sleep(1) # Keep main thread alive
    except KeyboardInterrupt:
        print("Encerrando servidor.")
        server.close()


