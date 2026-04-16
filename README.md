**Smart Cradle: Monitoramento Infantil via IoT**


https://github.com/user-attachments/assets/1b5fe12c-a84f-41a4-8e70-34ba9ef489fb

Este projeto apresenta o desenvolvimento de um Berço Inteligente fundamentado numa arquitetura IoT híbrida de três camadas: Percepção, Intermediação e Decisão. 

O sistema utiliza os protocolos CoAP e MQTT para garantir baixa latência e robustez no monitoramento neonatal. O sistema é capaz de detetar o choro e responder automaticamente com ações de conforto (balanço mecânico, musicoterapia e iluminação), mantendo os cuidadores informados através de notificações remotas.

**Funcionalidades Principais**

Monitoramento em Tempo Real: Captura de áudio e visualização de dados via dashboard web.
Atuação Automática: Acionamento de motor servo para balanço, LEDs endereçáveis e reprodução de música.
Histerese Dinâmica: Ajuste automático do limiar de sensibilidade para ignorar o próprio ruído da música de ninar, evitando loops de feedback.
Notificações Remotas: Alertas imediatos via API do Telegram e protocolo SMTP (Gmail) ao detetar choro persistente.

<img width="768" height="274" alt="image" src="https://github.com/user-attachments/assets/3e0aafbc-080e-4708-ab91-7e3904ef0e4d" />
_A imagem mostra a notificação recebida via telegram._

Proteção Temporal: Algoritmo que filtra ruídos isolados e mantém o sistema ativo durante pausas respiratórias naturais do bebé.

**Arquitetura do Sistema**

O projeto divide-se em três camadas lógicas para otimizar o tráfego de rede:
Camada de Percepção (Nó de Borda): Um ESP32 realiza a leitura do sensor MAX9814 e controla os periféricos. Comunica via CoAP/UDP para garantir rapidez.
Camada de Intermediação (Gateway): Um segundo ESP32 atua como ponte, traduzindo mensagens CoAP para MQTT/TCP.
Camada de Decisão (Servidor): Um script Python com Flask processa a lógica de controle e gere a interface de monitoramento.

**Tecnologias e Componentes**

Microcontroladores: 2x ESP32 NodeMCU.
Sensores: Módulo MAX9814 com Controle Automático de Ganho (AGC).
Atuadores: Micro Servo 9G SG90 (modificado para 360°), LEDs WS2812B (NeoPixel) e Módulo DFPlayer Mini.
Protocolos: CoAP, MQTT, HTTP (API Telegram) e SMTP.Software: Python 3, Flask, Paho-MQTT e Eclipse Mosquitto (Broker).

**Resultados de Validação**

O sistema foi submetido a testes rigorosos demonstrando alta imunidade a falsos positivos:
Estado de Repouso: Ruído de fundo estável entre 123 e 263 unidades ADC, bem abaixo do limiar de ativação (2500).
Atuação com Música: O sistema elevou o limiar para 3050, conseguindo "ignorar" o ruído da própria atuação (picos de 2300).
Detecção de Choro: Validação da persistência do sinal mesmo com interferência sonora.

**Configuração e Instalação**

Hardware: Siga o esquema de pinos detalhado nos arquivos .ino (PINO_SENSOR = 34, PINO_SERVO = 23, etc.).
Broker MQTT: Certifique-se de que o Eclipse Mosquitto está rodando no seu servidor local.

Servidor Python:
Bashpip install flask paho-mqtt requests
python server.py

Firmware: Carregue o código do Gateway e do Berço nos respectivos ESP32 via Arduino IDE.

Este projeto foi desenvolvido como parte da pesquisa académica no ** Departamento de Ciência da Computação da UDESC. **

O artigo completo com a fundamentação teórica está disponível na pasta /docs.

**Referências Consultadas:**

Artigo Académico: "Berço Inteligente: Monitoramento de Bebês Utilizando IoT" (Alessandra da Silva Lima Pereira).

Repositório de Código: Scripts de Servidor e Firmware ESP32 (fornecidos em Repositório.docx).
