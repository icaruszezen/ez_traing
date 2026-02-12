# 实现计划: 参考图片预标注

## 概述

本实现计划将参考图片预标注功能分解为可执行的编码任务。实现遵循现有代码架构，主要修改 `prelabeling_page.py`、`vision_service.py`、`engine.py` 和 `models.py`。

## 任务

- [x] 1. 扩展数据模型
  - [x] 1.1 在 `models.py` 中添加 `DetectionMode` 枚举和 `ReferenceImageInfo` 数据类
    - 添加 `DetectionMode` 枚举，包含 `TEXT_ONLY` 和 `REFERENCE_IMAGE` 两个值
    - 添加 `ReferenceImageInfo` 数据类，包含 `path`、`is_valid`、`error_message` 字段
    - _需求: 3.1, 3.2, 3.3_

- [x] 2. 实现参考图片面板组件
  - [x] 2.1 创建 `ReferenceImagePanel` 类基础结构
    - 在 `prelabeling_page.py` 中创建 `ReferenceImagePanel` 类
    - 实现 `__init__`、`_setup_ui` 方法
    - 定义 `images_changed` 信号、`MAX_IMAGES` 和 `THUMBNAIL_SIZE` 常量
    - _需求: 1.1, 2.4_
  
  - [x] 2.2 实现图片添加功能
    - 实现 `add_images` 方法，支持添加多张图片
    - 实现 `_validate_image` 方法，验证图片格式
    - 实现最大数量限制检查
    - _需求: 1.1, 1.2, 1.3, 1.5_
  
  - [x] 2.3 实现图片显示和缩略图
    - 实现 `_create_thumbnail` 方法，创建图片缩略图
    - 实现 `_add_image_item` 方法，在列表中显示图片
    - _需求: 1.4_
  
  - [x] 2.4 实现图片删除和清空功能
    - 实现 `remove_image` 方法
    - 实现 `clear_all` 方法
    - 实现 `get_image_paths` 和 `get_image_count` 方法
    - _需求: 2.2, 2.3_
  
  - [ ]* 2.5 编写 ReferenceImagePanel 属性测试
    - **Property 1: 图片格式验证一致性**
    - **Property 2: 添加图片后列表状态一致性**
    - **Property 3: 删除图片后列表状态一致性**
    - **Property 4: 清空操作幂等性**
    - **验证: 需求 1.2, 1.3, 1.4, 2.2, 2.3, 2.4**

- [x] 3. 检查点 - 确保参考图片面板测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 4. 扩展 VisionModelService
  - [x] 4.1 实现参考图片编码方法
    - 复用现有的 `encode_image_base64` 方法
    - 实现批量编码参考图片的逻辑
    - _需求: 4.1_
  
  - [x] 4.2 实现参考图片提示词生成
    - 实现 `generate_reference_prompt` 方法
    - 生成包含参考图片用途说明、查找指令、JSON 格式要求的提示词
    - 支持整合用户额外描述
    - _需求: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 4.3 实现参考图片 API 请求构建
    - 实现 `build_reference_image_payload` 方法
    - 构建包含多张参考图片和待检测图片的请求体
    - _需求: 4.2, 4.3, 4.4_
  
  - [x] 4.4 实现参考图片检测方法
    - 实现 `detect_objects_with_reference` 方法
    - 整合编码、请求构建、API 调用和响应解析
    - _需求: 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 4.5 编写 VisionModelService 属性测试
    - **Property 6: API 请求体图片编码完整性**
    - **Property 7: 提示词生成完整性**
    - **验证: 需求 4.1, 4.2, 4.4, 5.1, 5.2, 5.3, 5.4**

- [x] 5. 检查点 - 确保 VisionModelService 测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 6. 扩展预标注引擎
  - [x] 6.1 扩展 PrelabelingWorker 构造函数
    - 添加 `reference_images` 和 `detection_mode` 参数
    - 实现参数验证逻辑
    - _需求: 6.1, 6.3_
  
  - [x] 6.2 修改图片处理逻辑
    - 修改 `_process_one` 方法，根据检测模式选择调用方法
    - 在参考图片模式下调用 `detect_objects_with_reference`
    - _需求: 6.2, 6.4_
  
  - [x] 6.3 扩展输入验证函数
    - 修改 `validate_prelabeling_input` 函数
    - 添加参考图片模式的验证逻辑
    - _需求: 6.3_
  
  - [ ]* 6.4 编写 PrelabelingWorker 属性测试
    - **Property 8: 引擎参考图片传递一致性**
    - **验证: 需求 6.1, 6.2, 6.4**

- [x] 7. 检查点 - 确保预标注引擎测试通过
  - 确保所有测试通过，如有问题请询问用户。

- [x] 8. 集成到预标注页面
  - [x] 8.1 添加检测模式选择器
    - 在 `_create_prompt_card` 中添加模式选择下拉框
    - 实现模式切换回调 `_on_mode_changed`
    - _需求: 3.1, 3.2, 3.3_
  
  - [x] 8.2 集成参考图片面板
    - 在页面中添加 `ReferenceImagePanel` 实例
    - 根据检测模式控制面板可见性
    - _需求: 3.2, 3.3_
  
  - [x] 8.3 修改开始预标注逻辑
    - 修改 `_on_start_clicked` 方法
    - 根据检测模式传递参考图片列表给 `PrelabelingWorker`
    - 添加参考图片模式的验证检查
    - _需求: 3.4, 6.1_
  
  - [x] 8.4 更新错误处理和日志
    - 确保参考图片相关错误正确显示在日志面板
    - _需求: 7.1, 7.2, 7.3, 7.4_
  
  - [ ]* 8.5 编写集成属性测试
    - **Property 5: 模式切换面板可见性一致性**
    - **Property 9: 错误信息日志记录**
    - **验证: 需求 3.2, 3.3, 7.4**

- [x] 9. 最终检查点 - 确保所有测试通过
  - 确保所有测试通过，如有问题请询问用户。

## 备注

- 标记 `*` 的任务为可选任务，可跳过以加快 MVP 开发
- 每个任务都引用了具体的需求以便追溯
- 检查点确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证特定示例和边界情况
