from is_wire.core import Channel, Subscription, Message, Logger, AsyncTransport, Tracer
from is_wire.rpc import ServiceProvider, LogInterceptor
from is_msgs.common_pb2 import Shape
from is_msgs.image_pb2 import Image
from opencensus.ext.zipkin.trace_exporter import ZipkinExporter
from google.protobuf.empty_pb2 import Empty
import numpy as np
import cv2
import json
import time
import re
import socket
import pickle
import zlib

service_name = 'Pub.Camera1'
log = Logger(name=service_name)

def HC(request,ctx):
    type = (request.name).split('-')[0]
    consumer_topic = (request.name).split('-')[1] + "HC"
    if type == "Socket":
        log.info("Enviando solicitação para alterar comunicação")
        exporter = create_exporter(service_name, zipkin_host, log)
        msg = channel_1.consume()
        tracer = Tracer(exporter=exporter)
        img = msg.unpack(Image)
        aux = 0
        while aux < 5:
            with tracer.span(name='frame_camera1_PUBSUB') as span:
                img_msg = Message()
                img_msg.reply_to = "SOCKET"
                img_msg.pack(to_image(img))
                img_msg.topic = service_name
                img_msg.inject_tracing(span)
                img_msg.created_at = time.time()
                channel_2.publish(img_msg)
                log.info('Mensagem enviada via pub/sub')
            aux += 1
        return Empty()

rpc_channel = Channel("amqp://guest:guest@10.10.2.211:30000")
server = ServiceProvider(rpc_channel)
logging = LogInterceptor()
server.add_interceptor(logging)

server.delegate(
    topic=service_name + ".HC",
    request_type=Shape.Dimension,
    reply_type=Empty,
    function=HC)

def create_exporter(service_name: str, uri: str, log: Logger) -> ZipkinExporter:
    zipkin_ok = re.match("http:\\/\\/([a-zA-Z0-9\\.]+)(:(\\d+))?", uri)
    if not zipkin_ok:
        log.critical('Invalid zipkin uri "{}", expected http://<hostname>:<port>', uri)
    exporter = ZipkinExporter(
        service_name=service_name,
        host_name=zipkin_ok.group(1), # type: ignore[union-attr]
        port=zipkin_ok.group(3), # type: ignore[union-attr]
        transport=AsyncTransport,
    )
    return exporter

def to_image(input_image, encode_format='.jpeg', compression_level=0.8):
    if isinstance(input_image, np.ndarray):
        if encode_format == '.jpeg':
            params = [cv2.IMWRITE_JPEG_QUALITY, int(compression_level * (100 - 0) + 0)]
        elif encode_format == '.png':
            params = [cv2.IMWRITE_JPEG_COMPRESSION, int(compression_level * (9 - 0) + 0)]
        else:
            return Image()
        cimage = cv2.imencode(ext=encode_format, img=input_image, params=params)
        return Image(data=cimage[1].tobytes())
    elif isinstance(input_image, Image):
        return input_image
    else:
        return Image()

channel_1 = Channel("amqp://guest:guest@10.10.2.211:30000")  #NÃO MUDAR
channel_2 = Channel("amqp://guest:guest@10.10.2.211:30000")
channel_consume = Channel("amqp://guest:guest@10.10.2.211:30000")
log.info(f'Connected to broker: amqp://guest:guest@10.10.2.211:30000')

zipkin_host = "http://10.10.2.211:30200"

exporter = create_exporter(service_name, zipkin_host, log)

subscription = Subscription(channel=channel_1, name=service_name)
subscription_consume = Subscription(channel=channel_consume, name=service_name+".HC")
subscription_consume.subscribe(service_name+".HC")
subscription.subscribe('CameraGateway.2.Frame')

hc = 0

mudar_comunicacao = 0

while True:
    msg = channel_1.consume()
    tracer = Tracer(exporter=exporter)
    img = msg.unpack(Image)
    if len(img.data) == 0:
        log.warn("MENSAGEM VAZIA")
        continue

    if hc == 0:
        with tracer.span(name='frame_camera1_PUBSUB') as span:
            img_msg = Message()
            img_msg.pack(to_image(img))
            img_msg.topic = service_name
            img_msg.inject_tracing(span)
        img_msg.created_at = time.time()
        channel_2.publish(img_msg)
        log.info('Mensagem enviada via pub/sub')
    else:
        timestamp2 = time.time()
        TOTAL = timestamp2-timestamp1
        log.info(f"TEMPO PARA TROCA DE MODELO: {TOTAL}")
        with tracer.span(name='frame_camera1_UDP') as span:
            img_msg = Message()
            img_msg.pack(to_image(img))
            img_msg.topic = service_name
            img_msg.inject_tracing(span)
        img_msg.created_at = time.time()
        data = pickle.dumps(img_msg)
        size_bytes = len(data).to_bytes(8, "big")
        sock.sendall(size_bytes)
        sock.sendall(data)

        ack = sock.recv(2)
        if ack != b"OK":
            raise RuntimeError("ACK inválido do consumer")

        log.info("Quadro enviado via socket para {}:{}", HOST, PORT)

    try:
        message = rpc_channel.consume(timeout=0)
        if server.should_serve(message):
            server.serve(message)
            timestamp1 = time.time()
            hc = 1
            rpc_channel_2 = Channel("amqp://guest:guest@10.10.2.211:30000")
            subscription_2 = Subscription(rpc_channel_2)

            msg = Shape.Dimension()
            msg.name = "Socket"
            message_pub = Message(content = msg, reply_to = subscription_2)
            log.info("Mensagem criada")
            rpc_channel_2.publish(message_pub, topic="Person.Detector.HC")
            log.info("Waiting RETURN CONSUMER")
            try:
                reply = rpc_channel_2.consume(timeout=1.0)
                log.info("Mensagem recebida")
                message = reply.unpack(Shape.Dimension)
                HOST = message.name
                PORT = message.size
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((HOST, PORT))
                log.info(f"Conectado ao servidor {HOST}:{PORT}")

            except socket.timeout:
                print('No reply (Consumer) :(')
    except socket.timeout:
        pass
