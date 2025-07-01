import requests
from requests.auth import HTTPBasicAuth
from is_msgs.common_pb2 import ConsumerList
from is_msgs.common_pb2 import Shape
import json
import wget
from datetime import datetime, timedelta
from collections import defaultdict
import re
from is_wire.core import Logger, Channel, Subscription, Message
import socket

#Parâmetros iniciais
service_name = "hybrid.communication"
log = Logger(name=service_name)


publishers_channel = Channel("amqp://guest:guest@10.10.2.211:30000")
subscription_publishers = Subscription(publishers_channel)

# Para consultar o Broker
url_broker_consumers = "http://10.10.2.211:30080/api/consumers"
username = "guest"
password = "guest"

response_consumers = requests.get(
    url_broker_consumers,
    auth=HTTPBasicAuth(username, password),
    timeout=10  # Timeout de 10 segundos
)

# Para consultar o Zipkin
ZIPKIN_URL = "http://10.10.2.211:30200"
ENDPOINT = "/api/v2/traces"          # Endpoint da API v2

params = {
    "limit": 10000,                       # Limite de traces retornados
    "lookback": 900000,                # Período em milissegundos (15 minutos)
    "endTs": int(datetime.now().timestamp() * 1000),  # Timestamp atual em ms
}

#Função para filtrar traces do commtrace
def filtra_traces(traces):
    every_commtime = defaultdict(list)
    for trace in traces:
        for span in trace:
            name = span.get("name")
            service = span.get("localEndpoint", {}).get("serviceName")
            if service == 'commtrace':
                every_commtime[name].append(span)
    return(every_commtime)

#Retorna a media de duração (e outras informações) para cada consumidor
def media_duracao(commtime):
    resultado_media = []
    for name, spans in commtime.items():
        duracoes = [span['duration'] for span in spans if 'duration' in span]
        #print(spans)
        if duracoes:
            media = sum(duracoes) / len(duracoes)
            publish = name.split("_")[1]
            subscribe = name.split("_")[2]
            type = name.split("_")[3]
            resultado_media.append({
                "Publish": publish,
                "Subscribe": subscribe,
                "Media": media,
                "Duracos": len(duracoes),
                "Type": type
            })
    return(resultado_media)

consumidores_socket = []

#Loop Principal
while True:

    response = requests.get(f"{ZIPKIN_URL}{ENDPOINT}", params=params)

    if response.status_code == 200:
        traces = response.json()
        log.info(f"Total de traces encontrados: {len(traces)}")
    else:
        log.error(f"Erro na consulta: {response.status_code} - {response.text}")

    traces_commtime = filtra_traces(traces)
    media_tduracao = media_duracao(traces_commtime)

    for item in media_tduracao:
        print(item)
        if item['Media'] > 0 and item['Subscribe'] not in consumidores_socket:    #Verifica o tempo de comunicação
            consumer_atual = item['Subscribe']
            log.info(f"Mudar comunicação entre {item['Publish']} e {item['Subscribe']} para socket")
            response_consumers.raise_for_status()  #Coleta dos consumers Broker
            consumers = response_consumers.json()   #Passa para o formato json

            # Inicializando variáveis
            publisher_apto = 0

            #Verifica se dentre a lista de consumidores está o topic do Publisher+HC
            for item1 in consumers:
                print(item)
                publisher_zipkin = item["Publish"] + ".HC"
                consumer_broker = item1.get("queue", {}).get("name")
                if publisher_zipkin.lower() == consumer_broker.lower():
                    publisher_apto = 1
                    publisher_topic = consumer_broker

            if publisher_apto == 1:
                log.info(f"Publisher {publisher_topic} apto")
                msg = Shape.Dimension()
                msg.name = "Socket-{item['Subscribe']}"
                message_pub = Message(content = msg, reply_to = subscription_publishers)
                publishers_channel.publish(message_pub, topic=publisher_topic)
                log.info("Waiting RETURN PUBLISHER")
                try:
                    reply = publishers_channel.consume(timeout=5.0)
                    log.info("Publisher respondeu")
                    consumidores_socket.append(consumer_atual)
                except socket.timeout:
                    print('No reply (Consumer) :(')
            else:
                print("ERRO")
