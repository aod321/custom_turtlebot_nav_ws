import cv2
import numpy as np

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    from tensorflow import lite as tflite


def load_labels(label_path):
    """Load label map from text file. Each line is one class name."""
    labels = {}
    if not label_path:
        return labels
    with open(label_path, 'r') as f:
        for i, line in enumerate(f):
            labels[i] = line.strip()
    return labels


def preprocess_image(cv_image, input_shape, dtype):
    """Resize and format image for TFLite model input."""
    resized = cv2.resize(cv_image, (input_shape[1], input_shape[0]))
    input_data = np.expand_dims(resized, axis=0)
    if dtype == np.uint8:
        return input_data.astype(np.uint8)
    return (input_data / 255.0).astype(np.float32)


def parse_detections(boxes, classes, scores, threshold, labels, img_w, img_h):
    """Parse TFLite SSD output into a list of detection dicts."""
    results = []
    for i in range(len(scores)):
        if scores[i] < threshold:
            continue
        ymin, xmin, ymax, xmax = boxes[i]
        class_id = int(classes[i])
        results.append({
            'class_id': labels.get(class_id, str(class_id)),
            'score': float(scores[i]),
            'bbox': {
                'cx': (xmin + xmax) / 2.0 * img_w,
                'cy': (ymin + ymax) / 2.0 * img_h,
                'w': (xmax - xmin) * img_w,
                'h': (ymax - ymin) * img_h,
            },
            'bbox_norm': {
                'x1': float(xmin), 'y1': float(ymin),
                'x2': float(xmax), 'y2': float(ymax),
            },
        })
    return results


def draw_detections(cv_image, detections):
    """Draw bounding boxes and labels on image."""
    viz = cv_image.copy()
    for det in detections:
        b = det['bbox_norm']
        h, w = viz.shape[:2]
        x1, y1 = int(b['x1'] * w), int(b['y1'] * h)
        x2, y2 = int(b['x2'] * w), int(b['y2'] * h)
        label = "{}: {:.2f}".format(det['class_id'], det['score'])
        cv2.rectangle(viz, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(viz, label, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return viz


# --- ROS2 Node (imported conditionally so pure functions are testable standalone) ---

def make_node_class():
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import Image
    from vision_msgs.msg import (
        Detection2DArray, Detection2D, ObjectHypothesisWithPose
    )
    from cv_bridge import CvBridge

    class ObjectDetectorNode(Node):

        def __init__(self):
            super().__init__('object_detector')

            self.declare_parameter('model_path', '')
            self.declare_parameter('label_path', '')
            self.declare_parameter('confidence_threshold', 0.5)
            self.declare_parameter('inference_rate', 3.0)

            model_path = self.get_parameter('model_path').value
            label_path = self.get_parameter('label_path').value
            self.threshold = self.get_parameter('confidence_threshold').value
            rate = self.get_parameter('inference_rate').value

            self.labels = load_labels(label_path)

            if not model_path:
                self.get_logger().error('model_path parameter is required')
                return

            self.interpreter = tflite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            self.input_shape = self.input_details[0]['shape'][1:3]
            self.input_dtype = self.input_details[0]['dtype']

            self.bridge = CvBridge()
            self.latest_image = None

            self.sub = self.create_subscription(
                Image, '/camera/image_raw', self._image_cb, 1)
            self.det_pub = self.create_publisher(
                Detection2DArray, '/detections', 10)
            self.viz_pub = self.create_publisher(
                Image, '/detections/image', 10)

            self.timer = self.create_timer(1.0 / rate, self._run_inference)
            self.get_logger().info(
                'Detector started: {}Hz, threshold={}'.format(rate, self.threshold))

        def _image_cb(self, msg):
            self.latest_image = msg

        def _run_inference(self):
            if self.latest_image is None:
                return

            msg = self.latest_image
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'rgb8')
            h, w = cv_image.shape[:2]

            input_data = preprocess_image(
                cv_image, self.input_shape, self.input_dtype)

            self.interpreter.set_tensor(
                self.input_details[0]['index'], input_data)
            self.interpreter.invoke()

            raw_boxes = self.interpreter.get_tensor(
                self.output_details[0]['index'])[0]
            raw_classes = self.interpreter.get_tensor(
                self.output_details[1]['index'])[0]
            raw_scores = self.interpreter.get_tensor(
                self.output_details[2]['index'])[0]

            detections = parse_detections(
                raw_boxes, raw_classes, raw_scores,
                self.threshold, self.labels, w, h)

            det_array = Detection2DArray()
            det_array.header = msg.header
            for det in detections:
                d = Detection2D()
                d.bbox.center.position.x = det['bbox']['cx']
                d.bbox.center.position.y = det['bbox']['cy']
                d.bbox.size_x = det['bbox']['w']
                d.bbox.size_y = det['bbox']['h']
                hyp = ObjectHypothesisWithPose()
                hyp.hypothesis.class_id = det['class_id']
                hyp.hypothesis.score = det['score']
                d.results.append(hyp)
                det_array.detections.append(d)
            self.det_pub.publish(det_array)

            if self.viz_pub.get_subscription_count() > 0:
                viz = draw_detections(
                    cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR), detections)
                viz_msg = self.bridge.cv2_to_imgmsg(viz, 'bgr8')
                viz_msg.header = msg.header
                self.viz_pub.publish(viz_msg)

            if detections:
                names = [d['class_id'] for d in detections]
                self.get_logger().info('Detected: {}'.format(names))

    return ObjectDetectorNode


def main(args=None):
    import rclpy
    rclpy.init(args=args)
    cls = make_node_class()
    node = cls()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
