import time
import threading
import smtplib
import requests
import json
from datetime import datetime
from flask import Flask, render_template_string, jsonify
import paho.mqtt.client as mqtt
from email.mime.text import MIMEText

# --- CONFIGURAÇÕES ---
TELEGRAM_TOKEN = " "
TELEGRAM_CHAT_ID = " "
EMAIL_REMETENTE = " "
EMAIL_SENHA_APP = " " 
EMAIL_DESTINO   = " "

TOPIC_SENSOR = "berco/sensor/som"
TOPIC_ATUADOR = "berco/atuador/comando"
BROKER_ADDRESS = "localhost" 

# --- LÓGICA DE CONTROLE ---
LIMIAR_BARULHO = 2500 
LIMIAR_MUSICA = 3050  # Limiar mais alto quando a música está tocando

TEMPO_PARA_LIGAR = 2 
TEMPO_SILENCIO_FIM = 8 

# --- VARIÁVEIS DE ESTADO E HISTÓRICO ---
current_noise = 0
status_atuador = "DESLIGADO"
start_cry_time = 0
last_noise_time = 0
is_crying = False
last_notification_time = 0

# Lista para armazenar o histórico (ex: [{'time': '10:00:01', 'val': 120, 'status': 'OFF'}])
history_data = []

app = Flask(__name__)

# --- FUNÇÕES AUXILIARES ---
def add_to_history(val, status):
    global history_data
    now_str = datetime.now().strftime("%H:%M:%S")
    
    # Adiciona novo registro
    history_data.append({
        'time': now_str,
        'value': val,
        'status': status,
        'threshold': LIMIAR_MUSICA if status == "LIGADO" else LIMIAR_BARULHO
    })
    
    # Mantém apenas os últimos 10 registros
    if len(history_data) > 10:
        history_data.pop(0)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print(f"Erro Telegram: {e}")

def send_email(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINO
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
            server.sendmail(EMAIL_REMETENTE, EMAIL_DESTINO, msg.as_string())
    except Exception as e:
        print(f"Erro Email: {e}")

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc):
    print("Conectado ao MQTT")
    client.subscribe(TOPIC_SENSOR)

def on_message(client, userdata, msg):
    global current_noise, last_noise_time, start_cry_time, is_crying, status_atuador, last_notification_time
    
    try:
        val = int(msg.payload.decode())
        current_noise = val
        now = time.time()

        # Atualiza histórico para o gráfico
        add_to_history(val, status_atuador)

        # Seleciona o Limiar
        limiar_atual = LIMIAR_MUSICA if status_atuador == "LIGADO" else LIMIAR_BARULHO

        if val > limiar_atual:
            last_noise_time = now 
            
            if not is_crying and status_atuador == "DESLIGADO":
                if start_cry_time == 0:
                    start_cry_time = now
                elif (now - start_cry_time) > TEMPO_PARA_LIGAR:
                    print(f"ALERTA: ATIVANDO BERÇO (Nível: {val})")
                    client.publish(TOPIC_ATUADOR, "LIGAR")
                    status_atuador = "LIGADO"
                    is_crying = False 
                    start_cry_time = 0
                    
                    if (now - last_notification_time) > 60:
                        send_telegram(f"⚠️ Choro detectado: {val}. Música ligada.")
                        threading.Thread(target=send_email, args=("Alerta Berço", f"Nível {val}. Berço ligado.")).start()
                        last_notification_time = now
            
        else:
            # Silêncio
            if start_cry_time > 0 and (now - last_noise_time) > 2 and status_atuador == "DESLIGADO":
                start_cry_time = 0 

            if status_atuador == "LIGADO":
                if (now - last_noise_time) > TEMPO_SILENCIO_FIM:
                    print("SILÊNCIO: DESLIGANDO BERÇO")
                    client.publish(TOPIC_ATUADOR, "DESLIGAR")
                    status_atuador = "DESLIGADO"
                    send_telegram("✅ Bebê acalmou. Berço desligado.")
                    time.sleep(1) 

    except Exception as e:
        print(f"Erro processamento: {e}")

# --- THREAD MQTT ---
def mqtt_loop():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(BROKER_ADDRESS, 1883, 60)
        client.loop_forever()
    except:
        print("Erro conexão MQTT")

# --- INTERFACE WEB ---

# Rota API para o JavaScript pegar os dados sem recarregar a página
@app.route('/data')
def get_data():
    limiar_atual = LIMIAR_MUSICA if status_atuador == "LIGADO" else LIMIAR_BARULHO
    return jsonify({
        'noise': current_noise,
        'atuador': status_atuador,
        'limiar': limiar_atual,
        'history': history_data
    })

html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Monitor Berço Pro</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #f0f2f5; padding: 20px; text-align: center; }
        .container { max-width: 800px; margin: 0 auto; }
        
        .dashboard { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-bottom: 20px; }
        
        .card { 
            background: white; padding: 20px; width: 300px; border-radius: 12px; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
        }
        
        .value-box { font-size: 2.5em; font-weight: bold; margin: 10px 0; color: #333; }
        .status-on { color: #2ecc71; }
        .status-off { color: #95a5a6; }
        .alert-text { color: #e74c3c; animation: pulse 1s infinite; }
        
        .chart-container { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 20px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background: white; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px; border-bottom: 1px solid #ddd; text-align: center; }
        th { background-color: #f8f9fa; }
        
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>👶 Monitoramento em Tempo Real</h1>
        
        <div class="dashboard">
            <!-- Card Sensor -->
            <div class="card">
                <h3>🔊 Nível de Som</h3>
                <div id="noise-display" class="value-box">--</div>
                <p id="noise-status">Aguardando...</p>
                <small>Limiar Atual: <span id="threshold-display">--</span></small>
            </div>

            <!-- Card Atuador -->
            <div class="card">
                <h3>🎵 Berço / Música</h3>
                <div id="actuator-display" class="value-box status-off">--</div>
                <p id="actuator-desc">Status do sistema</p>
            </div>
        </div>

        <!-- Gráfico -->
        <div class="chart-container">
            <canvas id="noiseChart"></canvas>
        </div>

        <!-- Histórico -->
        <div class="chart-container">
            <h3>📜 Histórico (Últimos 10 níveis de som)</h3>
            <table id="history-table">
                <thead><tr><th>Hora</th><th>Nível</th><th>Limiar</th><th>Status</th></tr></thead>
                <tbody><!-- Preenchido via JS --></tbody>
            </table>
        </div>
    </div>

    <script>
        // Configuração do Gráfico
        const ctx = document.getElementById('noiseChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Nível de Ruído',
                    data: [],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.2)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Limiar de Disparo',
                    data: [],
                    borderColor: '#e74c3c',
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                animation: false, // Desativa animação para update rápido
                scales: {
                    y: { beginAtZero: true, suggestedMax: 600 }
                }
            }
        });

        async function fetchData() {
            try {
                const response = await fetch('/data');
                const data = await response.json();

                // 1. Atualiza Cards
                document.getElementById('noise-display').innerText = data.noise;
                document.getElementById('threshold-display').innerText = data.limiar;
                
                const noiseStatus = document.getElementById('noise-status');
                if (data.noise > data.limiar) {
                    //noiseStatus.innerHTML = '<span class="alert-text">⚠️ BARULHO ALTO</span>';
                } else {
                    //noiseStatus.innerHTML = '<span style="color:green">Ambiente Calmo</span>';
                }

                const actuatorDisplay = document.getElementById('actuator-display');
                actuatorDisplay.innerText = data.atuador;
                actuatorDisplay.className = data.atuador === 'LIGADO' ? 'value-box status-on' : 'value-box status-off';
                document.getElementById('actuator-desc').innerText = data.atuador === 'LIGADO' ? 'Filtrando ruído da música...' : 'Monitorando silêncio...';

                // 2. Atualiza Tabela de Histórico
                const tbody = document.querySelector('#history-table tbody');
                tbody.innerHTML = '';
                // Inverte para mostrar o mais recente primeiro
                [...data.history].reverse().forEach(row => {
                    const tr = `<tr>
                        <td>${row.time}</td>
                        <td><strong>${row.value}</strong></td>
                        <td>${row.threshold}</td>
                        <td>${row.status}</td>
                    </tr>`;
                    tbody.innerHTML += tr;
                });

                // 3. Atualiza Gráfico
                const labels = data.history.map(h => h.time);
                const noiseData = data.history.map(h => h.value);
                const thresholdData = data.history.map(h => h.threshold);

                chart.data.labels = labels;
                chart.data.datasets[0].data = noiseData;
                chart.data.datasets[1].data = thresholdData;
                chart.update();

            } catch (error) {
                console.error("Erro ao buscar dados:", error);
            }
        }

        // Atualiza a cada 2 segundos
        setInterval(fetchData, 2000);
        fetchData(); // Chamada inicial
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_template)

if __name__ == "__main__":
    t = threading.Thread(target=mqtt_loop)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=5000, debug=False)