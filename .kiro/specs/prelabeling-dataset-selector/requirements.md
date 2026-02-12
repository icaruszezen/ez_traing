# 需求文档

## 简介

为预标注页面（PrelabelingPage）添加数据集选择器功能，使用户可以在预标注页面直接选择要操作的数据集项目，而无需依赖页面切换时的自动同步机制。该功能通过在预标注页面嵌入一个下拉选择框（ComboBox），让用户从已有的数据集项目中选择目标数据集，选择后自动加载该数据集的图片列表并显示基本信息。

## 术语表

- **PrelabelingPage**: 预标注页面，提供视觉大模型预标注功能的用户界面
- **DatasetSelector**: 数据集选择器组件，嵌入在预标注页面中的下拉选择框
- **ProjectManager**: 项目管理器，负责管理所有数据集项目的增删改查
- **DatasetProject**: 数据集项目数据类，包含项目 ID、名称、目录路径、图片数量等信息
- **ImageScanner**: 图片扫描器，异步扫描指定目录下的所有支持格式的图片文件
- **ComboBox**: qfluentwidgets 提供的下拉选择框组件

## 需求

### 需求 1：数据集选择器显示

**用户故事：** 作为用户，我希望在预标注页面看到一个数据集选择器，以便我可以直接选择要操作的数据集。

#### 验收标准

1. WHEN 用户打开预标注页面, THE PrelabelingPage SHALL 在操作卡片上方显示一个数据集选择器卡片，包含一个 ComboBox 下拉框
2. WHEN 数据集选择器初始化时, THE DatasetSelector SHALL 从 ProjectManager 加载所有已有的数据集项目并填充到 ComboBox 中
3. WHEN 没有任何数据集项目存在时, THE DatasetSelector SHALL 显示占位提示文本"请先在数据集页面创建项目"
4. THE DatasetSelector SHALL 在每个下拉选项中显示项目名称和图片数量信息

### 需求 2：数据集选择与图片加载

**用户故事：** 作为用户，我希望选择数据集后自动加载该数据集的图片列表，以便我可以直接进行预标注操作。

#### 验收标准

1. WHEN 用户在 ComboBox 中选择一个数据集项目, THE PrelabelingPage SHALL 扫描该项目目录并加载所有支持格式的图片路径列表
2. WHEN 图片加载完成后, THE PrelabelingPage SHALL 更新进度标签显示已加载的图片数量
3. WHEN 用户选择的数据集项目目录不存在, THE PrelabelingPage SHALL 显示错误提示信息并清空图片列表
4. WHEN 图片扫描正在进行中用户切换了数据集选择, THE PrelabelingPage SHALL 取消当前扫描并启动新的扫描任务

### 需求 3：数据集列表刷新

**用户故事：** 作为用户，我希望能够刷新数据集列表，以便在数据集页面新增项目后能在预标注页面看到最新的项目列表。

#### 验收标准

1. WHEN 预标注页面变为可见状态时, THE DatasetSelector SHALL 自动刷新数据集项目列表
2. WHEN 刷新数据集列表后, THE DatasetSelector SHALL 保持之前选中的数据集项目（如果该项目仍然存在）
3. WHEN 刷新后之前选中的项目已被删除, THE DatasetSelector SHALL 清空选择状态并清空图片列表

### 需求 4：与现有预标注流程集成

**用户故事：** 作为用户，我希望数据集选择器与现有的预标注流程无缝集成，以便选择数据集后可以直接开始预标注。

#### 验收标准

1. WHEN 用户未选择任何数据集就点击"开始预标注"按钮, THE PrelabelingPage SHALL 显示提示信息"请先选择数据集"
2. WHEN 用户已选择数据集并加载了图片, THE PrelabelingPage SHALL 使用已加载的图片列表执行预标注流程
3. WHEN 预标注正在运行时, THE DatasetSelector SHALL 禁用 ComboBox 防止用户切换数据集
4. WHEN 预标注完成或取消后, THE DatasetSelector SHALL 重新启用 ComboBox 允许用户切换数据集
