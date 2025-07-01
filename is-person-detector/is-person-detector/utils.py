from typing import Optional

import dateutil.parser as dp

import re

from google.protobuf.json_format import Parse
from is_wire.core import Logger, AsyncTransport
from opencensus.ext.zipkin.trace_exporter import ZipkinExporter

from is_msgs.image_pb2 import Image

import cv2
import numpy as np

def get_topic_id(topic: str) -> str: # type: ignore[return]
    re_topic = re.compile(r"CameraGateway.(\d+).Frame")
    result = re_topic.match(topic)
    if result:
        return result.group(1)
    
def span_duration_ms(span) -> float:
    dt = dp.parse(span.end_time) - dp.parse(span.start_time)
    return dt.total_seconds() * 1000.0

    
def to_np(input_image):
    if isinstance(input_image, np.ndarray):
        output_image = input_image
    elif isinstance(input_image, Image):
        buffer = np.frombuffer(input_image.data, dtype=np.uint8)
        output_image = cv2.imdecode(buffer, flags=cv2.IMREAD_COLOR)
    else:
        output_image = np.array([], dtype=np.uint8)
    return output_image

def to_image(image, encode_format: str = ".jpeg", compression_level: float = 0.8, ) -> Image:
    if encode_format == ".jpeg":
        params = [cv2.IMWRITE_JPEG_QUALITY, int(compression_level * (100 - 0) + 0)]
    elif encode_format == ".png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, int(compression_level * (9 - 0) + 0)]
    else:
        return Image()
    cimage = cv2.imencode(ext=encode_format, img=image, params=params)
    return Image(data=cimage[1].tobytes())
    
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

def msg_commtrace(msg: str, type: str, timestamp_rcvd: float, service: str):
    if msg.metadata != {}:
        span = f'{msg.topic}_{service}_{type}'
        msg_to_commtrace = (
            f'{{"timestamp_send": "{int(msg.created_at*1000000)}", '
            f'"timestamp_rcvd": "{int(timestamp_rcvd*1000000)}", '
            f'"x-b3-flags": "{msg.metadata["x-b3-flags"]}", '
            f'"x-b3-parentspanid": "{msg.metadata["x-b3-parentspanid"]}", '
            f'"x-b3-sampled": "{msg.metadata["x-b3-sampled"]}", '
            f'"x-b3-spanid": "{msg.metadata["x-b3-spanid"]}", '
            f'"x-b3-traceid": "{msg.metadata["x-b3-traceid"]}", '
            f'"spanname": "{span}"}}'
        )
        bytesToSend = str.encode(msg_to_commtrace)

        return (bytesToSend, msg_to_commtrace)
