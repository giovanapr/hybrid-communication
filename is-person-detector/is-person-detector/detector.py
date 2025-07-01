from ultralytics import YOLO
import cv2
import numpy as np

from is_msgs.image_pb2 import ObjectAnnotations, Image

Width = int
Height = int
Channels = int

class personDetector:
    def __init__(self):
        self.model = YOLO('../model/yolov8m-pose.pt')
        self.model.to('cuda')        
    @staticmethod
    def bounding_box(image, annotations: ObjectAnnotations):

        image_2 = image
        for obj in annotations.objects:
            x1 = int(obj.region.vertices[0].x)
            y1 = int(obj.region.vertices[0].y)
            x2 = int(obj.region.vertices[1].x)
            y2 = int(obj.region.vertices[1].y)
            cv2.rectangle(image_2, (x1, y1), (x2, y2), (0, 0, 255), 2)
        return image_2
  
    @staticmethod
    def to_object_annotations(bounding_coords, image_shape,) -> ObjectAnnotations:
            annotations = ObjectAnnotations()
            for det in bounding_coords:
                bounding_box = det[0:4].cpu().numpy().astype(np.int32)
                item = annotations.objects.add()
                vertex_1 = item.region.vertices.add()
                vertex_1.x = bounding_box[0]
                vertex_1.y = bounding_box[1]
                vertex_2 = item.region.vertices.add()
                vertex_2.x = bounding_box[2]
                vertex_2.y = bounding_box[3]            
                item.label = "person"
                item.score = det[-1]
            annotations.resolution.width = image_shape[1]
            annotations.resolution.height = image_shape[0]
            return annotations
        
    def detect(self, array) -> ObjectAnnotations:
        
        results = self.model(array)
        return results
