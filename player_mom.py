import pygame
import threading
import json
import sys
import time
from pygame.locals import *
from mom_client import MOMClient # Importar o cliente MOM

# Configurações gráficas
LARGURA = 600
ALTURA = 850 # Altura ajustada para integrar UI e chat
TAMANHO_CELULA = 120
TAMANHO_TABULEIRO = 5

CORES = {
    'PRETO': (0, 0, 0),
    'BRANCO': (255, 255, 255),
    'CINZA': (100, 100, 100),
    'CINZA_ESCURO': (150, 150, 150),
    'MARROM': (139, 69, 19),
    'MARROM_CLARO': (160, 82, 45),
    'VERDE_ESCURO': (50, 255, 0),
    'AZUL': (0, 0, 255),
    'VERMELHO': (255, 0, 0),
    'VERMELHO_CLARO': (200, 0, 0),
    'VERDE': (0, 255, 0),
    'AMARELO': (255, 255, 0)
}

class TelaInicial:
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((400, 300))
        self.fonte = pygame.font.Font(None, 32)
        self.ip = 'localhost'
        self.nome = ''
        self.campo_ativo = 'nome'
        self.erro = ''

    def desenhar(self):
        self.tela.fill((30, 30, 30))
        # Título
        titulo = self.fonte.render('Configuração da Partida', True, (255, 255, 255))
        self.tela.blit(titulo, (20, 20))
        # Campo IP
        pygame.draw.rect(self.tela, (100, 100, 100) if self.campo_ativo == 'ip' else (70, 70, 70), (20, 80, 360, 40))
        texto_ip = self.fonte.render(f'IP: {self.ip}', True, (255, 255, 255))
        self.tela.blit(texto_ip, (30, 90))
        # Campo Nome
        pygame.draw.rect(self.tela, (100, 100, 100) if self.campo_ativo == 'nome' else (70, 70, 70), (20, 150, 360, 40))
        texto_nome = self.fonte.render(f'Nome: {self.nome}', True, (255, 255, 255))
        self.tela.blit(texto_nome, (30, 160))
        # Botão Conectar
        pygame.draw.rect(self.tela, (0, 200, 0), (20, 220, 360, 50))
        texto_botao = self.fonte.render('CONECTAR', True, (255, 255, 255))
        self.tela.blit(texto_botao, (150, 235))
        # Mensagem de erro
        if self.erro:
            texto_erro = self.fonte.render(self.erro, True, (255, 0, 0))
            self.tela.blit(texto_erro, (20, 270))
        pygame.display.flip()

    def executar(self):
        executando = True
        while executando:
            for evento in pygame.event.get():
                if evento.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if evento.type == MOUSEBUTTONDOWN:
                    x, y = evento.pos
                    if 20 <= x <= 380 and 220 <= y <= 270:
                        if self.ip and self.nome:
                            executando = False
                        else:
                            self.erro = 'Preencha ambos os campos!'
                    elif 20 <= y <= 120:
                        self.campo_ativo = 'ip'
                    elif 150 <= y <= 190:
                        self.campo_ativo = 'nome'
                if evento.type == KEYDOWN:
                    if evento.key == K_TAB:
                        self.campo_ativo = 'nome' if self.campo_ativo == 'ip' else 'ip'
                    elif evento.key == K_RETURN:
                        if self.ip and self.nome:
                            executando = False
                        else:
                            self.erro = 'Preencha ambos os campos!'
                    elif evento.key == K_BACKSPACE:
                        if self.campo_ativo == 'ip':
                            self.ip = self.ip[:-1]
                        else:
                            self.nome = self.nome[:-1]
                    else:
                        if evento.unicode.isprintable():
                            if self.campo_ativo == 'ip' and len(self.ip) < 15:
                                self.ip += evento.unicode
                            elif self.campo_ativo == 'nome' and len(self.nome) < 20:
                                self.nome += evento.unicode
                    self.erro = ''
            self.desenhar()
        return self.ip.strip(), self.nome.strip()

class ClienteSeega:
    def __init__(self, ip, nome):
        self.ip = ip
        self.nome = nome
        self.mom_client = MOMClient(nome, ip) # Inicializa o cliente MOM
        self.jogador_id = None # Será atribuído pelo servidor MOM
        self.estado = {
            'tabuleiro': [['-' for _ in range(5)] for _ in range(5)],
            'jogador_atual': 'P1',
            'fase': 1,
            'vencedor': None,
            'pecas_p1': 12,
            'pecas_p2': 12,
            'board_pieces_p1': 0,
            'board_pieces_p2': 0,
            'players': {} # Inicializa players como um dicionário vazio
        }
        self.chat = []
        self.input_chat = ''
        self.selecionado = None
        self.movimentos_validos = []
        self.running = True

        self.connect_to_server()
        self.mom_client.set_game_state_callback(self.update_game_state)
        self.mom_client.set_chat_message_callback(self.update_chat_history)
        
        # Iniciar o consumo da fila do usuário em uma thread separada
        threading.Thread(target=self.mom_client.start_listening, daemon=True).start()

        self.iniciar_interface()

    def connect_to_server(self):
        if not self.mom_client.connect():
            print("Não foi possível conectar ao broker MOM.")
            sys.exit()
        
        # Enviar mensagem de conexão para o servidor MOM
        # O servidor MOM responderá com o jogador_id e o estado inicial do jogo
        connect_message = {
            'type': 'connect_player',
            'player_name': self.nome
        }
        self.mom_client.send_message_to_user('game_server_queue', json.dumps(connect_message))
        print(f"Mensagem de conexão enviada para o servidor MOM como {self.nome}")

    def update_game_state(self, new_state):
        # Callback para atualizar o estado do jogo
        self.estado.update({
            'tabuleiro': new_state.get('tabuleiro', self.estado['tabuleiro']),
            'jogador_atual': new_state.get('jogador_atual', self.estado['jogador_atual']),
            'fase': new_state.get('fase', self.estado['fase']),
            'vencedor': new_state.get('vencedor', self.estado['vencedor']),
            'pecas_p1': new_state.get('pecas_p1', self.estado['pecas_p1']),
            'pecas_p2': new_state.get('pecas_p2', self.estado['pecas_p2']),
            'board_pieces_p1': new_state.get('board_pieces_p1', self.estado['board_pieces_p1']),
            'board_pieces_p2': new_state.get('board_pieces_p2', self.estado['board_pieces_p2']),
            'players': new_state.get('players', self.estado['players'])
        })
        # Atribuir jogador_id se ainda não tiver sido atribuído
        if self.jogador_id is None:
            for p_id, p_name in self.estado['players'].items():
                if p_name == self.nome:
                    self.jogador_id = p_id
                    print(f"Conectado como {self.jogador_id}")
                    break
        self.atualizar_movimentos_validos()

    def update_chat_history(self, sender, message):
        # Callback para atualizar o histórico do chat
        full_message = f"{sender}: {message}"
        self.chat.append(full_message)

    def enviar_movimento(self, tipo, origem, destino):
        message = {
            'type': 'game_action',
            'action': tipo,
            'origin': origem,
            'destination': destino,
            'player_id': self.jogador_id
        }
        self.mom_client.send_message_to_user('game_server_queue', json.dumps(message))

    def enviar_chat(self, texto):
        self.mom_client.publish_to_topic('chat_messages', texto)

    def surrender_game(self):
        message = {
            'type': 'surrender',
            'player_id': self.jogador_id
        }
        self.mom_client.send_message_to_user('game_server_queue', json.dumps(message))

    def atualizar_movimentos_validos(self):
        self.movimentos_validos = []
        if self.estado['fase'] != 2:
            return
        for i in range(5):
            for j in range(5):
                # Verifica se a peça na posição (i, j) pertence ao jogador atual
                if self.estado['tabuleiro'][i][j] == ('P' if self.jogador_id == 'P1' else 'B'):
                    # Itera sobre as 4 direções (cima, baixo, esquerda, direita)
                    for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                        dist = 1
                        while True:
                            ni, nj = i + dx*dist, j + dy*dist
                            # Verifica se a nova posição está dentro dos limites do tabuleiro
                            # e se a célula está vazia ('-')
                            if not (0 <= ni < 5 and 0 <= nj < 5) or self.estado['tabuleiro'][ni][nj] != '-':
                                break # Sai do loop se fora do tabuleiro ou célula ocupada
                            self.movimentos_validos.append((ni, nj))
                            dist += 1

    def desenhar_tabuleiro(self, tela):
        tela.fill(CORES['MARROM_CLARO'])
        for i in range(5):
            for j in range(5):
                cor = CORES['MARROM_CLARO'] if (i+j) % 2 == 0 else CORES['MARROM']
                pygame.draw.rect(tela, cor, (j*TAMANHO_CELULA, i*TAMANHO_CELULA, TAMANHO_CELULA, TAMANHO_CELULA))
                c = self.estado['tabuleiro'][i][j]
                centro = (j*TAMANHO_CELULA + TAMANHO_CELULA//2, i*TAMANHO_CELULA + TAMANHO_CELULA//2)
                if c == 'P':
                    pygame.draw.circle(tela, CORES['PRETO'], centro, 25)
                elif c == 'B':
                    pygame.draw.circle(tela, CORES['BRANCO'], centro, 25)
                elif c == 'X':
                    pygame.draw.rect(tela, CORES['CINZA_ESCURO'], (j*TAMANHO_CELULA, i*TAMANHO_CELULA, TAMANHO_CELULA, TAMANHO_CELULA))
                if self.selecionado == (i, j):
                    pygame.draw.rect(tela, CORES['AMARELO'], (j*TAMANHO_CELULA+3, i*TAMANHO_CELULA+3, TAMANHO_CELULA-6, TAMANHO_CELULA-6), 3)

    def desenhar_ui(self, tela):
        fonte = pygame.font.Font(None, 30)
        
        # Nome e ID local
        texto_jogador = fonte.render(f"Jogador: {self.nome} ({self.jogador_id})", True, CORES['AZUL'])
        tela.blit(texto_jogador, (10, 610))
        
        # Fase e peças
        texto_fase = fonte.render(f"Fase: {self.estado['fase']}", True, CORES['VERMELHO'])
        tela.blit(texto_fase, (10, 640))
        texto_pecas = fonte.render(f"Peças: P1={self.estado['pecas_p1']} | P2={self.estado['pecas_p2']}", True, CORES['PRETO'])
        tela.blit(texto_pecas, (10, 670))
        
        # Turno atual (exibe id)
        atual = self.estado['jogador_atual']
        if atual == self.jogador_id:
            turno_txt = f"Seu turno: {self.nome}"
        else:
            oponente_id = 'P1' if self.jogador_id == 'P2' else 'P2'
            oponente_nome = self.estado['players'].get(oponente_id, atual) 
            turno_txt = f"Turno de: {oponente_nome}"
        texto_turno = fonte.render(turno_txt, True, CORES['VERDE'])
        tela.blit(texto_turno, (300, 610))
        
        # Vencedor
        if self.estado.get('vencedor'):
            txt_v = fonte.render(f"Vencedor: {self.estado['vencedor']}!", True, CORES['VERDE'])
            tela.blit(txt_v, (LARGURA//2 - 100, ALTURA//2 - 20))

        # Botão Desistir
        btn_desistir_rect = pygame.Rect(LARGURA - 120, 700, 100, 40) # Mover para baixo para 700
        pygame.draw.rect(tela, CORES['VERMELHO_CLARO'], btn_desistir_rect)
        fonte_pequena = pygame.font.Font(None, 24)
        texto_desistir = fonte_pequena.render("DESISTIR", True, CORES['BRANCO'])
        texto_desistir_rect = texto_desistir.get_rect(center=btn_desistir_rect.center)
        tela.blit(texto_desistir, texto_desistir_rect)

        # Área do chat integrada
        chat_y_start = 750 # Início da área do chat
        pygame.draw.rect(tela, CORES['CINZA'], (0, chat_y_start, LARGURA, ALTURA - chat_y_start)) # Fundo do chat
        
        chat_font = pygame.font.Font(None, 24)
        
        # Campo de input do chat
        input_chat_height = 30
        input_chat_y = ALTURA - input_chat_height - 10 # Posição Y para o input, com margem inferior
        pygame.draw.rect(tela, CORES['BRANCO'], (10, input_chat_y, LARGURA - 20, input_chat_height))
        input_text_surface = chat_font.render(f"> {self.input_chat}", True, CORES['PRETO'])
        tela.blit(input_text_surface, (15, input_chat_y + 5))

        # Exibir as últimas mensagens do chat acima do campo de input
        chat_message_y = input_chat_y - 20 # Começa 20 pixels acima do input
        for msg in reversed(self.chat):
            chat_text_surface = chat_font.render(msg, True, CORES['BRANCO'])
            text_height = chat_text_surface.get_height()
            if chat_message_y - text_height < chat_y_start + 10: # Se a mensagem for muito alta, pare
                break
            tela.blit(chat_text_surface, (10, chat_message_y - text_height))
            chat_message_y -= 20 # Espaçamento entre as mensagens

    def desenhar_chat(self, tela): # Esta função não será mais usada, mas mantida por enquanto
        pass

    def handle_clique(self, pos):
        x, y = pos
        
        # Clique no botão DESISTIR
        btn_desistir_rect = pygame.Rect(LARGURA - 120, 700, 100, 40) # Usar as mesmas coordenadas do desenho do botão
        if btn_desistir_rect.collidepoint(x, y): # Usar collidepoint para verificar clique
            self.surrender_game()
            return

        # Ajustar a área clicável do tabuleiro para não incluir a área da UI/chat
        if y > (TAMANHO_TABULEIRO * TAMANHO_CELULA) or self.estado.get('vencedor'): # Limite superior da área de UI/chat
            return
        lin, col = y // TAMANHO_CELULA, x // TAMANHO_CELULA
        if self.estado['fase'] == 1 and self.jogador_id == self.estado['jogador_atual']:
            self.enviar_movimento('colocacao', None, (lin, col))
        elif self.estado['fase'] == 2 and self.jogador_id == self.estado['jogador_atual']:
            if not self.selecionado:
                if self.estado['tabuleiro'][lin][col] == ('P' if self.jogador_id=='P1' else 'B'):
                    self.selecionado = (lin, col)
            else:
                if (lin, col) in self.movimentos_validos:
                    self.enviar_movimento('movimento', self.selecionado, (lin, col))
                self.selecionado = None

    def iniciar_interface(self):
        pygame.init()
        tela = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption(f"Seega - {self.nome}")
        clock = pygame.time.Clock()
        chat_ativo = False
        while self.running:
            for evento in pygame.event.get():
                if evento.type == QUIT:
                    self.running = False
                    self.mom_client.disconnect()
                    pygame.quit()
                    sys.exit()
                if evento.type == MOUSEBUTTONDOWN:
                    self.handle_clique(evento.pos)
                    # Ajustar a área de clique para ativar o chat
                    chat_ativo = evento.pos[1] > (TAMANHO_TABULEIRO * TAMANHO_CELULA) + 140 # Ajustado para a nova posição do chat
                if evento.type == KEYDOWN and chat_ativo:
                    if evento.key == K_RETURN and self.input_chat.strip():
                        self.enviar_chat(self.input_chat)
                        self.input_chat = ''
                    elif evento.key == K_BACKSPACE:
                        self.input_chat = self.input_chat[:-1]
                    else:
                        self.input_chat += evento.unicode
            self.desenhar_tabuleiro(tela)
            self.desenhar_ui(tela)
            pygame.display.flip()
            clock.tick(30)

if __name__ == '__main__':
    tela_inicial = TelaInicial()
    ip, nome = tela_inicial.executar()
    ClienteSeega(ip, nome)


