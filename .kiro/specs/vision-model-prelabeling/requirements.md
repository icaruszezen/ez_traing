# 需求文档

## 简介

本功能为 ez_traing 图像标注应用程序新增视觉理解大模型预标注能力。用户可以通过提示词描述想要标注的目标内容，系统调用视觉理解大模型（兼容 OpenAI API 规范）对未标注的图片进行自动检测，生成矩形框目标，并将结果保存为 VOC 格式标注文件。此功能旨在减少人工标注工作量，提高标注效率。

## 术语表

- **Vision_Model_Service**: 视觉理解大模型服务，负责与 OpenAI 兼容 API 进行通信
- **Prelabeling_Engine**: 预标注引擎，协调图片处理、模型调用和标注文件生成
- **VOC_Writer**: VOC 格式标注文件写入器，使用现有的 PascalVocWriter 实现
- **API_Config**: API 配置管理器，负责存储和读取 API 地址和令牌设置
- **Prompt_Input**: 提示词输入组件，用户输入描述目标内容的文本
- **Prelabeling_Page**: 预标注页面，提供预标注功能的用户界面

## 需求

### 需求 1：API 配置管理

**用户故事：** 作为用户，我希望能够配置视觉大模型的 API 地址和令牌，以便系统能够连接到我选择的模型服务。

#### 验收标准

1. THE API_Config SHALL 提供 API 地址（endpoint）的输入和持久化存储
2. THE API_Config SHALL 提供 API 令牌（token）的输入和持久化存储
3. WHEN 用户修改 API 配置 THEN THE API_Config SHALL 立即保存配置到本地存储
4. WHEN 应用程序启动 THEN THE API_Config SHALL 自动加载已保存的配置
5. THE API_Config SHALL 对令牌进行脱敏显示（仅显示部分字符）

### 需求 2：提示词输入

**用户故事：** 作为用户，我希望能够输入提示词来描述我想要标注的目标内容，以便模型能够理解我的标注需求。

#### 验收标准

1. THE Prompt_Input SHALL 提供多行文本输入框供用户输入提示词
2. THE Prompt_Input SHALL 提供默认提示词模板作为参考
3. WHEN 用户输入提示词 THEN THE Prelabeling_Page SHALL 保存提示词以便复用
4. IF 提示词为空 THEN THE Prelabeling_Engine SHALL 阻止预标注操作并提示用户

### 需求 3：图片编码与传输

**用户故事：** 作为系统，我需要将图片转换为 base64 格式并发送给视觉大模型，以便模型能够分析图片内容。

#### 验收标准

1. WHEN 处理图片 THEN THE Vision_Model_Service SHALL 将图片文件读取并编码为 base64 格式
2. THE Vision_Model_Service SHALL 支持常见图片格式（jpg、jpeg、png、bmp、webp）
3. WHEN 构建 API 请求 THEN THE Vision_Model_Service SHALL 按照 OpenAI Vision API 规范组装请求体
4. THE Vision_Model_Service SHALL 在请求中包含图片的 MIME 类型信息

### 需求 4：模型调用与响应解析

**用户故事：** 作为系统，我需要调用视觉大模型 API 并解析返回的检测结果，以便生成标注数据。

#### 验收标准

1. THE Vision_Model_Service SHALL 使用标准 OpenAI API 规范发送请求
2. THE Vision_Model_Service SHALL 在请求头中包含 Authorization Bearer 令牌
3. WHEN 模型返回响应 THEN THE Vision_Model_Service SHALL 解析响应中的矩形框坐标和标签信息
4. IF API 调用失败 THEN THE Vision_Model_Service SHALL 返回错误信息并记录日志
5. IF API 返回格式异常 THEN THE Vision_Model_Service SHALL 返回解析错误并提供原始响应内容
6. THE Vision_Model_Service SHALL 支持设置请求超时时间

### 需求 5：VOC 标注文件生成

**用户故事：** 作为用户，我希望预标注结果能够保存为 VOC 格式的 XML 文件，以便与现有标注工作流程兼容。

#### 验收标准

1. WHEN 模型返回检测结果 THEN THE VOC_Writer SHALL 为每张图片生成对应的 XML 标注文件
2. THE VOC_Writer SHALL 使用现有的 PascalVocWriter 类生成标准 VOC 格式文件
3. THE VOC_Writer SHALL 将标注文件保存在与图片相同的目录下
4. THE VOC_Writer SHALL 在标注文件中包含图片尺寸、文件名和所有检测到的目标框
5. IF 图片已存在标注文件 THEN THE Prelabeling_Engine SHALL 询问用户是否覆盖

### 需求 6：批量预标注处理

**用户故事：** 作为用户，我希望能够对数据集中的多张未标注图片进行批量预标注，以便高效完成大量图片的初步标注。

#### 验收标准

1. THE Prelabeling_Engine SHALL 支持选择单张或多张图片进行预标注
2. THE Prelabeling_Engine SHALL 提供"仅处理未标注图片"的选项
3. WHEN 执行批量预标注 THEN THE Prelabeling_Page SHALL 显示处理进度（当前/总数）
4. THE Prelabeling_Engine SHALL 支持用户中途取消批量处理
5. WHEN 单张图片处理完成 THEN THE Prelabeling_Page SHALL 更新进度显示
6. WHEN 批量处理完成 THEN THE Prelabeling_Page SHALL 显示处理结果统计（成功数、失败数）

### 需求 7：预标注页面界面

**用户故事：** 作为用户，我希望有一个专门的预标注页面，以便我能够方便地配置和执行预标注操作。

#### 验收标准

1. THE Prelabeling_Page SHALL 集成到主窗口的导航栏中
2. THE Prelabeling_Page SHALL 包含 API 配置区域、提示词输入区域和操作按钮区域
3. THE Prelabeling_Page SHALL 显示当前选中的数据集项目信息
4. THE Prelabeling_Page SHALL 提供"开始预标注"按钮触发预标注流程
5. WHEN 预标注进行中 THEN THE Prelabeling_Page SHALL 禁用开始按钮并显示取消按钮
6. THE Prelabeling_Page SHALL 显示预标注操作的日志输出

### 需求 8：错误处理与用户反馈

**用户故事：** 作为用户，我希望在预标注过程中遇到问题时能够获得清晰的错误提示，以便我能够了解问题原因并采取相应措施。

#### 验收标准

1. IF API 配置未完成 THEN THE Prelabeling_Page SHALL 提示用户先完成配置
2. IF 网络连接失败 THEN THE Vision_Model_Service SHALL 显示网络错误提示
3. IF 模型返回空结果 THEN THE Prelabeling_Engine SHALL 记录该图片未检测到目标
4. WHEN 发生错误 THEN THE Prelabeling_Page SHALL 在日志区域显示详细错误信息
5. THE Prelabeling_Engine SHALL 在单张图片处理失败时继续处理后续图片
