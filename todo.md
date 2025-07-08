## Projeto MOM - Refatoração de Código Python

### Fase 1: Análise dos códigos existentes e especificações
- [x] Ler e entender o código `player.py` (cliente RMI).
- [x] Ler e entender o código `server.py` (servidor RMI).
- [x] Ler e entender o código `Produtor.java` (exemplo JMS).
- [x] Ler e entender o código `Publisher.java` (exemplo JMS).
- [x] Ler e entender o código `Subscriber.java` (exemplo JMS).
- [x] Ler e entender o código `Consumidor.java` (exemplo JMS).
- [x] Identificar as funcionalidades RMI no código Python que precisam ser substituídas por MOM.
- [x] Pesquisar bibliotecas MOM para Python (e.g., Pika para RabbitMQ, stompy para ActiveMQ, ou MQTT).
- [x] Escolher a biblioteca MOM mais adequada para o projeto (Pika para RabbitMQ).

### Fase 2: Implementação do Broker MOM
- [x] Configurar um broker MOM (e.g., RabbitMQ, ActiveMQ) no ambiente do sandbox.
- [x] Implementar as funcionalidades de gerenciamento do broker:
    - [x] Adicionar e remover filas e tópicos.
    - [x] Listar filas e tópicos.
    - [x] Listar quantidade de mensagens nas filas.
    - [x] Instanciar aplicações de usuários (verificar duplicidade de nomes).
    - [x] Criar automaticamente uma fila para cada usuário novo criado.

### Fase 3: Implementação das aplicações de usuários
- [x] Refatorar `player.py` para se conectar ao broker MOM.
- [ ] Implementar as funcionalidades do usuário:
    - [x] Permitir assinar tópicos.
    - [x] Enviar mensagens entre usuários diretamente (via filas).
    - [x] Enviar mensagens para tópicos.

### Fase 4: Criação das interfaces gráficas
- [x] Adaptar a interface gráfica existente em `player.py` para interagir com o novo sistema MOM.
- [x] Criar uma interface gráfica para o gerenciamento do broker (se necessário).

### Fase 5: Testes e finalização
- [x] Realizar testes unitários e de integração das funcionalidades MOM.
- [x] Garantir que todas as funcionalidades do projeto foram implementadas corretamente.
- [x] Otimizar o código e garantir a robustez do sistema.

### Fase 6: Entrega dos resultados
- [ ] Compactar os códigos-fonte.
- [ ] Preparar o email com o link do Google Drive/GitHub.
- [ ] Escrever um player.py e server.py executáveis (se aplicável).
- [ ] Apresentar o trabalho pessoalmente (conforme observações).



- [x] Identificar as funcionalidades RMI no código Python que precisam ser substituídas por MOM.


