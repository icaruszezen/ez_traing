# EZ Traing 项目说明文档

## 1. 项目简介

`ez_traing` 是一个基于 **PyQt5 + qfluentwidgets** 的一体化视觉数据工具，面向目标检测场景，覆盖从数据集管理、预标注、人工标注、训练前数据准备到 YOLO 训练与验证的完整流程。

项目将传统标注工具能力（集成 `labelImg`）与自动化能力（视觉 API / YOLO 推理、模板匹配、脚本化标注）结合，帮助你提高数据生产效率。

---

## 2. 核心功能

应用主界面包含以下页面（按导航顺序）：

1. **数据集**
   - 数据集项目创建/管理
   - 目录扫描与图片预览
   - 标注统计与筛选
   - 与单张标注、批量标注联动

2. **预标注**
   - 支持两种推理后端：
     - 视觉 API（大模型）
     - 本地 YOLO `.pt` 权重
   - 支持文本提示词与参考图模式
   - 批量生成 VOC XML 标注

3. **标注**
   - 基于 `third_party/labelImg` 集成的人工标注能力
   - 支持常规框选标注流程

4. **批量标注**
   - 多图批量处理
   - 适合同类目标快速校正与补标

5. **模板匹配**
   - 基于 OpenCV `matchTemplate`
   - 支持多模板、阈值过滤、NMS 去重
   - 可选多尺度匹配

6. **数据准备**
   - 扫描样本并解析 VOC 标注
   - 训练/验证集划分
   - 可选数据增强
   - 导出 YOLO 训练结构（`images/`, `labels/`, `classes.txt`, `data.yaml`）

7. **脚本标注**
   - 内置脚本模板
   - 可在界面创建、编辑、保存、执行 Python 标注脚本
   - 支持绑定数据集项目执行

8. **训练**
   - YOLO 训练配置（模型、epoch、batch、imgsz、device）
   - 实时日志与进度
   - 训练结果目录管理

9. **验证**
   - YOLO 模型验证
   - 输出核心指标（mAP、Precision、Recall、F1）
   - 支持结果图与报告导出

10. **设置**
    - 依赖与运行环境相关设置入口

---

## 3. 技术栈与依赖

### 3.1 主要技术栈

- Python 3
- PyQt5
- PyQt-Fluent-Widgets
- OpenCV
- Ultralytics YOLO
- Albumentations
- Matplotlib
- lxml / PyYAML

### 3.2 依赖清单（`requirements.txt`）

- `PyQt5>=5.15.2`
- `PyQt-Fluent-Widgets>=1.4.0`
- `lxml>=4.9.1`
- `ultralytics>=8.0.0`
- `PyYAML>=6.0`
- `matplotlib>=3.7.0`
- `albumentations>=1.4.0`
- `opencv-python>=4.8.0`

---

## 4. 项目结构（核心目录）

```text
ez_traing/
├─ src/
│  ├─ ez_traing/
│  │  ├─ main.py                     # 应用入口
│  │  ├─ ui/main_window.py           # 主窗口与导航
│  │  ├─ pages/                      # 各功能页面
│  │  ├─ prelabeling/                # 预标注引擎/模型服务/API配置
│  │  ├─ data_prep/                  # 训练前数据准备流水线
│  │  ├─ template_matching/          # 模板匹配引擎与线程
│  │  ├─ evaluation/                 # 验证引擎、报告与可视化
│  │  ├─ labeling/                   # 标注窗口封装（对接 labelImg）
│  │  └─ common/constants.py         # 公共常量
│  └─ third_party/labelImg/          # 集成的第三方标注工具
├─ tests/                            # 单元测试
├─ requirements.txt
└─ README.md
```

---

## 5. 安装与运行

> 以下示例以 Windows PowerShell 为例，Linux/macOS 可按等价命令执行。

### 5.1 创建虚拟环境并安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 5.2 启动应用

```powershell
python src/ez_traing/main.py
```

### 5.3 冒烟测试（快速启动后自动退出）

```powershell
python src/ez_traing/main.py --smoke-test
```

---

## 6. 典型使用流程（推荐）

1. 在 **数据集** 页面创建项目并选择图片目录
2. 在 **预标注** 页面批量生成初始标注（视觉 API 或 YOLO）
3. 在 **标注/批量标注** 页面人工复核与修正
4. 在 **数据准备** 页面导出 YOLO 训练数据结构
5. 在 **训练** 页面启动训练并观察日志
6. 在 **验证** 页面评估模型并导出报告

---

## 7. 配置与数据存储说明

程序会在用户目录下创建配置目录：

- `~/.ez_traing/`

常见内容包括：

- 数据集项目配置（如 `datasets.json`）
- 视觉 API 配置（如 `vision_api_config.json`）
- 训练/验证输出（如 `runs/`）

---

## 8. 开发与测试

项目包含预标注等模块的测试用例（`tests/prelabeling/`）。

可使用 `pytest` 运行测试：

```powershell
pytest
```

---

## 9. 注意事项

1. 训练与验证功能依赖 `ultralytics`，并受本机 CUDA / GPU 环境影响。
2. 若使用视觉 API 预标注，请先在配置中填写有效 `endpoint` 与 `api_key`。
3. 模板匹配与批量任务对图片规模较敏感，建议分批处理大型数据集。
4. 预标注与模板匹配默认可选择跳过已有 XML 标注，避免重复覆盖。

---

## 10. 后续可扩展方向

- 增加更多模型后端（ONNX/TensorRT）
- 增强批量质检（低置信度回查、类别分布预警）
- 与 MLOps 平台集成（实验追踪、模型版本管理）
- 更完善的数据闭环（困难样本回流与主动学习）

---

如需，我可以继续补一份“新成员上手指南（按页面点击步骤）”或“面向标注团队的标准操作流程（SOP）”。