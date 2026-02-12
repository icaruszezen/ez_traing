# 需求文档

## 简介

本功能扩展现有的预标注系统，允许用户提供一张或多张参考图片（包含目标物体的示例），让视觉模型根据参考图片来识别和定位待标注图片中的相同或相似目标。这是一种 visual grounding / few-shot detection 的方式，比纯文本描述更直观准确。

## 术语表

- **Reference_Image（参考图片）**: 用户提供的包含目标物体示例的图片，用于指导视觉模型识别相似目标
- **Target_Image（待检测图片）**: 需要进行目标检测和标注的图片
- **Reference_Image_Panel（参考图片面板）**: UI 组件，用于显示和管理参考图片列表
- **Vision_Service（视觉服务）**: 负责与视觉模型 API 通信的服务模块
- **Prelabeling_Engine（预标注引擎）**: 协调图片处理、模型调用和标注文件生成的核心模块
- **Detection_Mode（检测模式）**: 预标注的工作模式，包括"仅文本提示"和"参考图片"两种

## 需求

### 需求 1：参考图片选择与上传

**用户故事：** 作为标注人员，我希望能够选择和上传参考图片，以便让视觉模型根据参考图片识别目标。

#### 验收标准

1. WHEN 用户点击"添加参考图片"按钮 THEN Reference_Image_Panel SHALL 打开文件选择对话框，支持选择单张或多张图片
2. WHEN 用户选择图片文件 THEN Reference_Image_Panel SHALL 验证文件格式为支持的图片格式（jpg、jpeg、png、bmp、webp）
3. WHEN 图片格式不支持 THEN Reference_Image_Panel SHALL 显示错误提示并拒绝添加该图片
4. WHEN 参考图片添加成功 THEN Reference_Image_Panel SHALL 在列表中显示图片缩略图和文件名
5. WHEN 参考图片数量超过最大限制（10张） THEN Reference_Image_Panel SHALL 显示警告提示并拒绝添加更多图片

### 需求 2：参考图片预览与管理

**用户故事：** 作为标注人员，我希望能够预览和管理已添加的参考图片，以便确认参考图片的正确性。

#### 验收标准

1. WHEN 用户点击参考图片缩略图 THEN Reference_Image_Panel SHALL 显示该图片的放大预览
2. WHEN 用户点击参考图片的删除按钮 THEN Reference_Image_Panel SHALL 从列表中移除该图片
3. WHEN 用户点击"清空全部"按钮 THEN Reference_Image_Panel SHALL 移除所有参考图片并重置面板状态
4. THE Reference_Image_Panel SHALL 显示当前参考图片数量（如"已添加 3/10 张参考图片"）

### 需求 3：检测模式切换

**用户故事：** 作为标注人员，我希望能够在"仅文本提示"和"参考图片"模式之间切换，以便根据实际需求选择合适的检测方式。

#### 验收标准

1. THE Prelabeling_Page SHALL 提供检测模式选择器，包含"仅文本提示"和"参考图片"两个选项
2. WHEN 用户选择"仅文本提示"模式 THEN Prelabeling_Page SHALL 隐藏参考图片面板并使用现有的纯文本提示词功能
3. WHEN 用户选择"参考图片"模式 THEN Prelabeling_Page SHALL 显示参考图片面板
4. WHEN 检测模式为"参考图片"且未添加任何参考图片 THEN Prelabeling_Page SHALL 在开始预标注时显示错误提示

### 需求 4：参考图片 API 请求构建

**用户故事：** 作为系统，我需要将参考图片和待检测图片一起发送给视觉模型 API，以便模型能够根据参考图片进行目标检测。

#### 验收标准

1. WHEN 构建 API 请求 THEN Vision_Service SHALL 将所有参考图片编码为 base64 格式并包含在请求中
2. WHEN 构建 API 请求 THEN Vision_Service SHALL 将待检测图片编码为 base64 格式并包含在请求中
3. WHEN 构建 API 请求 THEN Vision_Service SHALL 生成指导模型进行参考图片匹配的提示词
4. THE Vision_Service SHALL 支持同时发送 1-10 张参考图片和 1 张待检测图片

### 需求 5：参考图片提示词生成

**用户故事：** 作为系统，我需要生成合适的提示词来指导视觉模型根据参考图片进行目标检测。

#### 验收标准

1. WHEN 生成提示词 THEN Vision_Service SHALL 包含明确的指令说明参考图片的用途
2. WHEN 生成提示词 THEN Vision_Service SHALL 包含要求模型在待检测图片中查找与参考图片相似目标的指令
3. WHEN 用户提供了额外的文本描述 THEN Vision_Service SHALL 将用户描述整合到提示词中
4. THE Vision_Service SHALL 生成要求模型返回 JSON 格式检测结果的提示词

### 需求 6：预标注引擎集成

**用户故事：** 作为系统，我需要在预标注引擎中支持参考图片模式，以便批量处理图片时使用参考图片进行检测。

#### 验收标准

1. WHEN 预标注引擎启动 THEN Prelabeling_Engine SHALL 接收参考图片列表作为输入参数
2. WHEN 处理每张待检测图片 THEN Prelabeling_Engine SHALL 将参考图片列表传递给 Vision_Service
3. WHEN 参考图片列表为空且模式为"参考图片" THEN Prelabeling_Engine SHALL 抛出验证错误
4. THE Prelabeling_Engine SHALL 在整个批量处理过程中复用相同的参考图片列表

### 需求 7：错误处理与用户反馈

**用户故事：** 作为标注人员，我希望在参考图片功能出现问题时获得清晰的错误提示，以便快速定位和解决问题。

#### 验收标准

1. IF 参考图片文件无法读取 THEN Reference_Image_Panel SHALL 显示具体的错误信息并跳过该图片
2. IF 参考图片编码失败 THEN Vision_Service SHALL 返回包含错误详情的 DetectionResult
3. IF API 请求因参考图片过大而失败 THEN Vision_Service SHALL 返回建议减少参考图片数量或压缩图片的提示
4. WHEN 预标注过程中发生错误 THEN Prelabeling_Page SHALL 在日志面板中显示详细的错误信息
