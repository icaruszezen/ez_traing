# 实现计划：视觉模型预标注功能

## 概述

本实现计划将视觉模型预标注功能分解为可执行的编码任务。实现顺序遵循依赖关系：先实现基础数据模型和配置管理，然后实现核心服务，最后实现 UI 页面和集成。

## 任务

- [x] 1. 实现数据模型和配置管理
  - [x] 1.1 创建数据模型定义
    - 在 `src/ez_traing/prelabeling/` 目录下创建 `models.py`
    - 定义 `VisionAPIConfig` 数据类（endpoint, api_key, model_name, timeout）
    - 定义 `BoundingBox` 数据类（label, x_min, y_min, x_max, y_max, confidence）
    - 定义 `DetectionResult` 数据类（success, boxes, error_message, raw_response）
    - 定义 `PrelabelingStats` 数据类（total, processed, success, failed, skipped）
    - _需求: 4.3, 6.6_

  - [x] 1.2 实现 API 配置管理器
    - 在 `src/ez_traing/prelabeling/` 目录下创建 `config.py`
    - 实现 `APIConfigManager` 类
    - 实现配置的加载、保存、更新方法
    - 实现 `is_configured()` 验证方法
    - 实现 `get_masked_api_key()` 脱敏方法
    - 配置文件保存在 `~/.ez_traing/vision_api_config.json`
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 1.3 编写配置管理器属性测试
    - **Property 1: 配置往返一致性**
    - **Property 2: API 令牌脱敏格式**
    - **Property 14: 配置完整性验证**
    - **验证需求: 1.1, 1.2, 1.3, 1.4, 1.5, 8.1**

- [x] 2. 实现视觉模型服务
  - [x] 2.1 实现图片编码功能
    - 在 `src/ez_traing/prelabeling/` 目录下创建 `vision_service.py`
    - 实现 `encode_image_base64()` 方法，支持 jpg/jpeg/png/bmp/webp 格式
    - 实现 MIME 类型映射
    - _需求: 3.1, 3.2, 3.4_

  - [ ]* 2.2 编写图片编码属性测试
    - **Property 4: 图片 Base64 编码往返**
    - **Property 5: 图片格式与 MIME 类型映射**
    - **验证需求: 3.1, 3.2, 3.4**

  - [x] 2.3 实现 API 请求构建
    - 实现 `build_request_payload()` 方法
    - 按照 OpenAI Vision API 规范构建请求体
    - 包含 model、messages、max_tokens 字段
    - _需求: 3.3_

  - [ ]* 2.4 编写请求构建属性测试
    - **Property 6: API 请求体结构**
    - **验证需求: 3.3**

  - [x] 2.5 实现响应解析功能
    - 实现 `parse_response()` 方法
    - 解析 JSON 响应中的 objects 数组
    - 提取 label、bbox、confidence 信息
    - 处理异常格式响应
    - _需求: 4.3, 4.5_

  - [ ]* 2.6 编写响应解析属性测试
    - **Property 7: 响应解析正确性**
    - **Property 8: 异常响应处理**
    - **验证需求: 4.3, 4.5**

  - [x] 2.7 实现 API 调用功能
    - 实现 `detect_objects()` 方法
    - 使用 requests 库发送 POST 请求
    - 设置 Authorization Bearer 头
    - 处理超时和网络错误
    - _需求: 4.1, 4.2, 4.4, 4.6_

- [x] 3. 检查点 - 确保所有测试通过
  - 运行已编写的测试，确保配置管理和视觉服务功能正常
  - 如有问题请询问用户

- [x] 4. 实现 VOC 标注写入器
  - [x] 4.1 实现 VOC 标注写入功能
    - 在 `src/ez_traing/prelabeling/` 目录下创建 `voc_writer.py`
    - 实现 `VOCAnnotationWriter` 类
    - 使用现有的 `PascalVocWriter` 生成 XML
    - 实现 `save_annotation()` 方法
    - 实现 `_get_image_size()` 辅助方法
    - _需求: 5.1, 5.2, 5.3, 5.4_

  - [ ]* 4.2 编写 VOC 写入器属性测试
    - **Property 9: VOC 标注文件完整性**
    - **Property 10: 标注文件路径**
    - **验证需求: 5.1, 5.3, 5.4**

- [x] 5. 实现预标注引擎
  - [x] 5.1 实现预标注工作线程
    - 在 `src/ez_traing/prelabeling/` 目录下创建 `engine.py`
    - 实现 `PrelabelingWorker` 类（继承 QThread）
    - 实现 `run()` 方法处理图片列表
    - 实现 `cancel()` 方法支持取消
    - 实现 `_has_annotation()` 检查已有标注
    - 发射 progress、image_completed、finished 信号
    - _需求: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 5.2 实现输入验证
    - 实现提示词非空验证
    - 实现配置完整性验证
    - _需求: 2.4, 8.1_

  - [ ]* 5.3 编写预标注引擎属性测试
    - **Property 3: 空提示词验证**
    - **Property 11: 批量处理统计一致性**
    - **Property 12: 取消处理有效性**
    - **Property 13: 未标注图片过滤**
    - **Property 15: 错误恢复继续处理**
    - **验证需求: 2.4, 6.2, 6.4, 6.6, 8.1, 8.5**

- [x] 6. 检查点 - 确保所有测试通过
  - 运行所有测试，确保核心功能正常
  - 如有问题请询问用户

- [x] 7. 实现预标注页面 UI
  - [x] 7.1 创建预标注页面基础结构
    - 在 `src/ez_traing/pages/` 目录下创建 `prelabeling_page.py`
    - 实现 `PrelabelingPage` 类（继承 QWidget）
    - 设置页面布局（ScrollArea + 卡片布局）
    - _需求: 7.1, 7.2_

  - [x] 7.2 实现 API 配置卡片
    - 创建 API 地址输入框（LineEdit）
    - 创建 API 令牌输入框（PasswordLineEdit）
    - 创建模型名称输入框
    - 创建超时时间输入框
    - 实现配置保存逻辑
    - _需求: 1.1, 1.2, 1.5_

  - [x] 7.3 实现提示词输入卡片
    - 创建多行文本输入框（TextEdit）
    - 设置默认提示词模板
    - _需求: 2.1, 2.2, 2.3_

  - [x] 7.4 实现操作按钮卡片
    - 创建"开始预标注"按钮
    - 创建"取消"按钮
    - 创建"仅处理未标注"复选框
    - 创建进度条和进度标签
    - _需求: 6.3, 7.4, 7.5_

  - [x] 7.5 实现日志显示卡片
    - 创建日志文本区域（TextEdit，只读）
    - 实现 `_log()` 方法添加带时间戳的日志
    - _需求: 7.6, 8.4_

  - [x] 7.6 实现预标注流程控制
    - 实现 `_on_start_clicked()` 启动预标注
    - 实现 `_on_cancel_clicked()` 取消预标注
    - 实现 `_on_progress()` 更新进度
    - 实现 `_on_finished()` 处理完成
    - 连接工作线程信号
    - _需求: 6.3, 6.4, 6.5, 6.6, 8.2, 8.3_

- [x] 8. 集成到主窗口
  - [x] 8.1 注册预标注页面
    - 在 `main_window.py` 中导入 `PrelabelingPage`
    - 创建页面实例并设置 objectName
    - 添加到导航栏（使用合适的图标）
    - _需求: 7.1_

  - [x] 8.2 实现数据集联动
    - 从 DatasetPage 获取当前选中的项目
    - 传递图片列表给预标注页面
    - _需求: 7.3_

- [x] 9. 创建模块初始化文件
  - 创建 `src/ez_traing/prelabeling/__init__.py`
  - 导出主要类和函数
  - 更新 `src/ez_traing/__init__.py` 如需要

- [x] 10. 最终检查点 - 确保所有测试通过
  - 运行所有测试
  - 验证 UI 功能正常
  - 如有问题请询问用户

## 注意事项

- 标记为 `*` 的任务为可选测试任务，可跳过以加快 MVP 开发
- 每个任务都引用了具体的需求编号以便追溯
- 检查点任务用于确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证特定示例和边界情况
