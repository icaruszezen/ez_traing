# 实现计划：预标注数据集选择器

## 概述

在预标注页面添加数据集选择器 ComboBox，复用现有 ProjectManager，实现数据集选择、图片扫描加载、页面切换刷新等功能。

## 任务

- [x] 1. 提取共享常量并添加数据集选择器卡片
  - [x] 1.1 将 `SUPPORTED_IMAGE_FORMATS` 从 `dataset_page.py` 提取到共享模块 `src/ez_traing/common/constants.py`，并更新 `dataset_page.py` 的导入
    - 创建 `src/ez_traing/common/__init__.py` 和 `src/ez_traing/common/constants.py`
    - 将 `SUPPORTED_IMAGE_FORMATS` 移至 `constants.py`
    - 更新 `dataset_page.py` 中的导入路径
    - _Requirements: 2.1_

  - [x] 1.2 在 `PrelabelingPage` 中添加 `set_project_manager` 方法和数据集选择器卡片 UI
    - 添加 `_project_manager`、`_current_project_id`、`_project_ids` 属性
    - 实现 `_create_dataset_card()` 方法，创建包含 ComboBox 和信息标签的卡片
    - 在 `_setup_ui()` 中将数据集选择器卡片插入到 API 配置卡片之前
    - 实现 `set_project_manager()` 方法
    - _Requirements: 1.1, 1.2, 1.4_

  - [x] 1.3 实现 `_refresh_dataset_list` 方法
    - 从 ProjectManager 获取所有项目
    - 填充 ComboBox 选项，格式为 "项目名称 (N 张图片)"
    - 无项目时显示占位提示文本
    - 刷新后保持之前选中的项目
    - _Requirements: 1.2, 1.3, 1.4, 3.2, 3.3_

  - [ ]* 1.4 编写属性测试：ComboBox 与项目列表同步
    - **Property 1: ComboBox 与项目列表同步**
    - **Validates: Requirements 1.2, 1.4**

  - [ ]* 1.5 编写属性测试：刷新后保持选中项
    - **Property 3: 刷新后保持选中项**
    - **Validates: Requirements 3.2**

- [x] 2. 实现数据集选择与图片扫描加载
  - [x] 2.1 实现 `_on_dataset_changed` 回调和 `_scan_project_images` 方法
    - ComboBox 选择变化时获取对应的 DatasetProject
    - 扫描项目目录下所有支持格式的图片文件
    - 更新 `_image_paths` 和进度标签
    - 处理目录不存在的错误情况
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 2.2 编写属性测试：图片扫描完整性
    - **Property 2: 图片扫描完整性**
    - **Validates: Requirements 2.1**

  - [ ]* 2.3 编写单元测试：边界情况
    - 测试空项目列表时的占位文本
    - 测试目录不存在时的错误处理
    - 测试刷新后选中项被删除时的清空行为
    - _Requirements: 1.3, 2.3, 3.3_

- [x] 3. 集成到主窗口并处理页面切换
  - [x] 3.1 修改 `AppWindow` 共享 ProjectManager 并处理页面切换刷新
    - 在 `__init__` 中调用 `prelabeling_page.set_project_manager(dataset_page.project_manager)`
    - 重写 `PrelabelingPage.showEvent` 触发 `_refresh_dataset_list()`
    - 移除 `_on_page_changed` 中旧的自动同步图片逻辑
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.2 修改 `_on_start_clicked` 和 `_set_running_state` 集成预标注流程
    - 修改 `_on_start_clicked` 中的验证逻辑，未选择数据集时提示"请先选择数据集"
    - 修改 `_set_running_state` 添加 ComboBox 的启用/禁用控制
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 3.3 编写单元测试：预标注流程集成
    - 测试未选择数据集时点击开始的验证
    - 测试运行状态下 ComboBox 禁用/启用切换
    - _Requirements: 4.1, 4.3, 4.4_

- [x] 4. 最终检查点
  - 确保所有测试通过，如有问题请向用户确认。

## 备注

- 标记 `*` 的任务为可选任务，可跳过以加快 MVP 开发
- 每个任务引用了具体的需求编号以确保可追溯性
- 属性测试验证通用正确性属性，单元测试验证特定示例和边界情况
