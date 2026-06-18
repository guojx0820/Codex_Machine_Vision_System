# 工业机器视觉缺陷检测软件闭环示例（PySide6 + YOLO/模拟算法 + PLC + SQLite）

## 1. 技术栈结论

建议第一版使用 **Python + PySide6 + OpenCV + Ultralytics YOLO + SQLite + Modbus TCP**：

- Python：算法、相机 SDK、OpenCV、YOLO 训练/推理生态最完整，开发最快。
- PySide6：Qt 工业软件界面能力成熟，同时保留 Python 开发效率。
- YOLO：先快速跑通缺陷检测闭环；量产前可导出 ONNX/TensorRT。
- SQLite：单机工控机可靠够用；多工位联网后再切 MySQL/PostgreSQL。
- Modbus TCP：与 PLC 交互简单通用，适合 OK/NG、触发、复位等信号。

## 2. 完整闭环

```text
PLC/光电触发 -> 工业相机采图 -> OpenCV 预处理 -> YOLO/缺陷算法推理
     -> OK/NG 判定 -> GUI 显示 -> NG 图片保存 -> SQLite 记录 -> Modbus TCP 回写 PLC
```

本示例默认使用 `SimulatorCamera` 和 `DummyDefectDetector`，没有相机和 GPU 也能运行。切换到真实产线时：

1. 在 `app/camera.py` 增加海康/Basler/大恒 SDK 适配类，实现 `open/read/close`。
2. 在 `config/config.yaml` 将 `camera.type` 改为对应类型。
3. 训练 YOLO 后将 `model.backend` 改为 `ultralytics`，`model.weights` 指向你的 `.pt` 文件。
4. 打开 `plc.enabled`，配置 PLC IP、端口和线圈地址。

## 3. 运行

```bash
cd industrial_vision_app
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main config/config.yaml
```

## 4. 训练自己的缺陷模型

### 4.1 采集与标注

- 每种零件、每种缺陷至少采集 200-1000 张；小样本可先每类 50-100 张验证流程。
- 使用 LabelImg、CVAT 或 Roboflow 标注框。
- 导出 YOLO 格式：`images/train`、`images/val`、`labels/train`、`labels/val`。

### 4.2 data.yaml 示例

```yaml
path: /data/defect_dataset
train: images/train
val: images/val
names:
  0: scratch
  1: dent
  2: stain
```

### 4.3 训练命令

```bash
cd industrial_vision_app
python tools/train_yolo.py
```

训练完成后，把 `runs/detect/train/weights/best.pt` 写入 `config/config.yaml`：

```yaml
model:
  backend: ultralytics
  weights: runs/detect/train/weights/best.pt
  confidence: 0.35
  device: 0
```

## 5. 部署到 Windows 工控机

```bash
pip install pyinstaller
pyinstaller -F -w -n IndustrialVision app/main.py --add-data "config;config"
```

把以下内容放到同一部署目录：

- 生成的 `IndustrialVision.exe`
- `config/config.yaml`
- YOLO 权重文件 `best.pt`
- 相机厂商 SDK runtime/DLL
- 若使用 TensorRT，安装匹配 CUDA/TensorRT 版本

## 6. 真实相机接入位置

`app/camera.py` 已定义统一接口：

```python
class Camera(Protocol):
    def open(self) -> None: ...
    def read(self) -> np.ndarray: ...
    def close(self) -> None: ...
```

真实 SDK 只要返回 OpenCV BGR `np.ndarray`，后面的算法、界面、数据库、PLC 都不需要改。

## 7. 量产注意事项

- 现场必须做光源、镜头、曝光、触发防抖和相机固定治具验证。
- 模型阈值不要只看 mAP，要用漏检率、误检率、节拍、复判成本评估。
- 每次 NG 保存原图和标注图，便于追溯和持续迭代训练。
- 推理延迟不满足节拍时，优先 ONNX/TensorRT、缩小 ROI、降低分辨率、使用线扫/面阵合适方案。
