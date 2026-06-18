from ultralytics import YOLO

# 数据集需按 Ultralytics YOLO 格式准备，并在 data.yaml 中声明 train/val 路径、类别名。
model = YOLO("yolo11n.pt")
model.train(data="data.yaml", epochs=100, imgsz=640, batch=16, device=0)
model.export(format="onnx", dynamic=True)
