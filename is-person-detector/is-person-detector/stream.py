from is_msgs.image_pb2 import Image
from is_msgs.common_pb2 import Shape
from is_wire.core import Logger, Channel, Subscription, Message, Tracer, AsyncTransport
from is_wire.rpc import ServiceProvider, LogInterceptor
from opencensus.trace.span import Span
from opencensus.ext.zipkin.trace_exporter import ZipkinExporter
from detector import personDetector

from streamChannel import StreamChannel
from utils import get_topic_id, to_np, to_image, create_exporter, span_duration_ms, msg_commtrace

import re
import time
import socket
import json
import sys
import pickle

def send_commtrace_msg(msg:str,type_comunication:str,timestamp_rcvd:int,serverAddressPort:str,log:Logger,service:str,bufferSize=2048):
    if msg.metadata != {}:
        bytesToSend, msg_to_commtrace = msg_commtrace(msg,type_comunication,timestamp_rcvd,service)

        UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
#        log.info("Enviando mensagem para Contrace")
        UDPClientSocket.sendto(bytesToSend, serverAddressPort)
#        log.info("Mensagem para Contrace: {}", msg_to_commtrace)
    else:
        log.warn("Could not send message to Commtrace because msg.metadata is empty")

def main() -> None:

    config = json.load(open('../etc/conf/options.json'))
#    broker_uri = config['broker_uri']
    broker_uri = "amqp://guest:guest@10.10.2.211:30000"
    zipkin_host = config['zipkin_uri']

    service_name = 'Person.Detector'

    person_detector = personDetector()

    log = Logger(name=service_name)
    channel = StreamChannel()
    channel_1 = Channel("amqp://guest:guest@10.10.2.211:30000") #Não mudar
    log.info(f'Connected to broker {broker_uri}')

    exporter = create_exporter(service_name, zipkin_host, log)

    subscription = Subscription(channel=channel, name=service_name)
    subscription.subscribe('CameraGateway.*.Frame')

    log.info("Creating the RPC Server and waiting requests...")

    #RPC GATEWAY

    def get_local_ip() -> str:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
            except OSError:
                return "127.0.0.1"

    def HC(request,ctx):
        HOST = get_local_ip()
        PORT = 20000
        log.info(f'Socket created {HOST}:{PORT}')
        msg = Shape.Dimension()
        msg.size = PORT
        msg.name = HOST
        return msg

    def recvall(sock, n):
        data = bytearray()
        print(data)
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                raise ConnectionError("conexão fechada prematuramente")
            data.extend(packet)
        return data

    rpc_channel = Channel("amqp://guest:guest@10.10.2.211:30000")
    server = ServiceProvider(rpc_channel)
    logging = LogInterceptor()
    server.add_interceptor(logging)

    server.delegate(
        topic=service_name + ".HC",
        request_type=Shape.Dimension,
        reply_type=Shape.Dimension,
        function=HC)

    channel_requisicao = Channel("amqp://guest:guest@10.10.2.211:30000")
    subscription_requisicao = Subscription(channel_requisicao)

    hc = 0

    while True:
        if hc == 0:
            msg = channel.consume_last()
            timestamp_rcvd = time.time()
            type_comunication = "pub/sub"
        else:
            tamanho_dados_bytes = client_socket.recv(8)
            tamanho_dados = int.from_bytes(tamanho_dados_bytes, byteorder='big')
            log.info(f"Esperando mensagens")
            dados_recebidos = bytearray()
            while len(dados_recebidos) < tamanho_dados:
                chunk = client_socket.recv(min(4096, tamanho_dados - len(dados_recebidos)))
                if not chunk:
                   break
                dados_recebidos.extend(chunk)
            client_socket.sendall(b"OK")
            log.info(f"Recebidos {tamanho_dados} bytes e ACK devolvido")

            msg = pickle.loads(dados_recebidos)
            timestamp_rcvd = time.time()
            print(timestamp_rcvd-msg.created_at)
            type_comunication = "socket"

        if type(msg) == bool:
            print("MENSAGEM VAZIA")
            continue


        tracer = Tracer(exporter=exporter, span_context=msg.extract_tracing())
        span = tracer.start_span(name='detection_and_render')

        serverAddressPort = (config['conmtrace_host'], config['conmtrace_port'])
        send_commtrace_msg(msg,type_comunication,timestamp_rcvd,serverAddressPort,log,service=service_name)

        detection_span = None

        with tracer.span(name='unpack'):
            img = msg.unpack(Image)
            if len(img.data) == 0:
                print("MENSAGEM VAZIA")
                continue
            im_np = to_np(img)

        with tracer.span(name='detection') as _span:
            camera_id = get_topic_id(msg.topic)
            detections = person_detector.detect(im_np)
            detection_span = _span

        with tracer.span(name='pack_and_publish_detections'):
            person_msg = Message()
            person_msg.topic = f'PersonDetector.{camera_id}.Detection'
            person_msg.inject_tracing(span)

            bounding_boxes = detections[0].boxes.xyxy
            obj_annotations = person_detector.to_object_annotations(bounding_boxes, detections[0].orig_shape)
            person_msg.created_at = time.time()
            channel_1.publish(person_msg)

        with tracer.span(name='render_pack_publish'):

            image_with_bounding = person_detector.bounding_box(im_np, obj_annotations)
            rendered_msg = Message()
            rendered_msg.topic = f'PersonDetector.{camera_id}.Rendered'
            rendered_msg.inject_tracing(span)

            rendered_msg.pack(to_image(image_with_bounding))
            rendered_msg.created_at = time.time()
            channel_1.publish(rendered_msg)

        span.add_attribute('Detections', len(detections[0].boxes))
        tracer.end_span()

        info = {
            'detections': len(detections[0].boxes),
               'took_ms': {
                'detection': round(span_duration_ms(detection_span), 2),
                'service': round(span_duration_ms(span), 2),
            },
        }
#        log.info('{}', str(info).replace("'", '"'))
        print(msg.reply_to)
        if msg.reply_to == "SOCKET":
            log.info("Aguardando publisher")
            try:
                message = rpc_channel.consume(timeout=5)
                if server.should_serve(message):
                    server.serve(message)
                    hc = 1
                    HOST = get_local_ip()
                    PORT = 20000
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.bind((HOST, PORT))
                    s.listen()
                    log.info(f"Servidor socket TCP iniciado em {HOST}:{PORT}")
                    client_socket, client_address = s.accept()
                    log.info(f"Connection from {client_address}")

            except socket.timeout:
                pass


if __name__ == '__main__':
    main()

