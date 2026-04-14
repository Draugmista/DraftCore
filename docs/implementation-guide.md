# DraftCore 开发落地说明

## 1. 文档目的

本文用于把总体架构转化为可直接开工的实现说明，重点回答以下问题：

- 第一版 CLI 需要有哪些命令
- 核心对象怎么定义
- 文件解析和导出接口怎么固定
- 多类型素材如何支撑阶段 5 的六个任务

本文默认遵循 [docs/architecture.md](/C:/Codefield/DraftCore/docs/architecture.md) 与 [docs/adr/001-tech-stack.md](/C:/Codefield/DraftCore/docs/adr/001-tech-stack.md)。

## 2. 第一版建议目录结构

以下是建议的实现骨架，供后续搭建代码时使用：

```text
draftcore/
  app/
    cli/
    config/
    db/
    models/
    services/
    parsers/
    exporters/
    ai/
```

职责约定如下：

- `cli/`：Typer 命令入口和参数解析
- `config/`：TOML 配置读取
- `db/`：SQLite 连接、会话和初始化
- `models/`：SQLModel 数据模型和领域对象
- `services/`：项目、素材、草稿、归档等业务服务
- `parsers/`：按文件类型实现素材解析器
- `exporters/`：Markdown 与后续 Word 导出器
- `ai/`：AI Provider 接口与具体实现

## 3. CLI 命令设计

第一版 CLI 命令按工作流组织，保持和阶段 5 任务顺序一致。

### 3.1 `project`

建议子命令：

- `project create`
- `project list`
- `project show`

职责：

- 创建报告项目
- 查看项目主题、状态、目标输出
- 作为其他命令的上下文入口

### 3.2 `asset`

建议子命令：

- `asset add`
- `asset list`
- `asset show`

职责：

- 把本地文件登记为素材
- 查看项目下的素材范围
- 查看单个素材的元数据、抽取状态和基础摘要

### 3.3 `collection`

建议子命令：

- `collection build`
- `collection show`

职责：

- 围绕项目生成素材集合
- 对素材集合执行用途标记和范围展示

### 3.4 `reuse`

建议子命令：

- `reuse find`

职责：

- 在项目上下文中查找模板、历史成果和已登记素材中的可复用内容
- 输出复用候选清单

### 3.5 `draft`

建议子命令：

- `draft create`
- `draft update`
- `draft show`

职责：

- 创建主草稿
- 基于素材和复用候选更新草稿
- 查看草稿结构、来源和状态

### 3.6 `export`

建议子命令：

- `export render`

职责：

- 将结构化草稿渲染为目标格式文件
- 第一版默认目标为 Markdown

### 3.7 `archive`

建议子命令：

- `archive finalize`
- `archive show`

职责：

- 将主草稿转为最终报告
- 保存归档记录和来源追溯关系

## 4. 核心数据对象

第一版至少固定以下对象。

### 4.1 `ReportProject`

表示一次具体报告任务。

最小字段：

- `id`
- `name`
- `topic`
- `target_output`
- `status`
- `created_at`
- `updated_at`

### 4.2 `Asset`

表示一个被纳入管理的素材文件。

最小字段：

- `id`
- `name`
- `path`
- `file_type`
- `source_category`
- `topic_or_task`
- `usage_note`
- `is_used`
- `ingestion_status`
- `created_at`
- `updated_at`

说明：

- `file_type` 负责表达 `md`、`docx`、`pptx`、图片等技术格式
- `source_category` 负责表达原始素材、模板素材、参考成果等业务角色

### 4.3 `AssetContentProfile`

表示素材经解析后的标准化内容摘要。

最小字段：

- `asset_id`
- `title`
- `summary`
- `searchable_text`
- `structure_excerpt`
- `page_count`
- `paragraph_count`
- `parser_name`
- `extracted_at`

说明：

- 图片素材可允许 `searchable_text` 为空
- `structure_excerpt` 用于保存标题层级、页标题或关键结构片段的最小表示

### 4.4 `AssetCollection`

表示围绕报告项目组织的素材集合。

最小字段：

- `id`
- `project_id`
- `name`
- `purpose`
- `created_at`

### 4.5 `ReuseCandidate`

表示复用定位结果。

最小字段：

- `id`
- `project_id`
- `asset_id`
- `candidate_type`
- `snippet`
- `reason`
- `score_hint`
- `created_at`

说明：

- 第一版 `score_hint` 可以是简单排序依据，不要求复杂评分体系

### 4.6 `Draft`

表示项目主草稿。

最小字段：

- `id`
- `project_id`
- `name`
- `version_label`
- `status`
- `content_model`
- `source_snapshot`
- `created_at`
- `updated_at`

说明：

- `content_model` 应保存结构化章节和文本块，而不是只保存 Markdown 文本
- `source_snapshot` 用于记录生成或改写时引用过的素材和复用候选

### 4.7 `FinalReport`

表示归档后的最终成果。

最小字段：

- `id`
- `project_id`
- `draft_id`
- `name`
- `output_format`
- `output_path`
- `archived_at`

## 5. 关键关系约束

- 一个 `ReportProject` 可关联多个 `Asset`
- 一个 `ReportProject` 可关联多个 `AssetCollection`
- 一个 `ReportProject` 默认只有一个主 `Draft`
- 一个 `Draft` 可引用多个 `Asset` 和多个 `ReuseCandidate`
- 一个 `FinalReport` 必须能追溯到其来源 `Draft`
- 一个 `FinalReport` 必须能追溯到其使用过的素材、模板和参考成果

第一版不引入复杂版本树，不引入多人协作状态流。

## 6. 文件解析接口

### 6.1 统一解析器接口

每种文件类型都实现统一接口，建议语义如下：

- 输入：
  - 文件路径
  - 基础上下文，例如项目主题、来源类别
- 输出：
  - 标准化素材内容对象
  - 包括标题、文本摘要、结构片段、页数/段落数、可检索文本

### 6.2 各类型最低要求

#### `md` / `txt`

- 读取全文
- 生成摘要
- 提取可检索文本
- 支持复用定位

#### `docx`

- 提取段落文本
- 识别标题层级或近似结构
- 生成摘要
- 支持复用定位

#### `pptx`

- 提取页标题
- 提取文本框文本
- 提取备注区文本（如可行）
- 生成最小结构摘要

#### 图片

- 记录路径、文件名、扩展名、尺寸等基础信息
- 支持备注和用途说明
- 支持按名称、路径、备注和用途检索
- 默认不要求 OCR

#### `xlsx`

- 第一版只预留接口和类型标识
- 不作为阶段 6 的必做交付项

## 7. 草稿模型与导出接口

## 7.1 草稿内部表示

草稿内部模型建议采用以下思路：

- 草稿由多个章节组成
- 每个章节下包含文本块、引用片段或占位说明
- 每个章节和文本块可保留来源引用

这样做的目的：

- 让业务层围绕“内容结构”工作，而不是围绕 Markdown 语法工作
- 让后续新增 Word 导出时可复用同一份草稿模型

### 7.2 导出器接口

统一导出器应固定如下语义：

- 输入：
  - 结构化草稿
  - 报告元数据
  - 输出路径
- 输出：
  - 目标格式文件

第一版实现：

- `MarkdownExporter`

后续扩展：

- `WordExporter`

### 7.3 第一版输出规则

- 主草稿可保存为结构化模型
- `export render` 负责生成 `.md` 文件
- `archive finalize` 在归档时记录 Markdown 输出路径

## 8. 复用定位规则

第一版复用定位采用保守可解释策略。

### 8.1 适用于文本类和文档类素材

对 `md`、`txt`、`docx`、`pptx`：

- 按项目主题关键词筛选
- 按来源类别筛选模板素材、参考成果
- 在抽取文本中查找匹配片段
- 输出候选片段和复用理由

### 8.2 适用于图片素材

对图片：

- 基于文件名、路径、备注、用途说明进行检索
- 可作为报告插图或证据材料来源
- 不要求参与正文语义片段提取

## 9. AI Provider 接口约定

第一版至少定义两个能力入口：

- `generate_draft`
- `rewrite_text`

输入要求：

- 输入必须基于标准化素材片段、复用候选和项目上下文
- 不直接把原始文件二进制作为业务层标准输入

输出要求：

- `generate_draft` 输出结构化草稿片段或章节内容
- `rewrite_text` 输出改写后的文本块

未配置 AI 时的默认行为：

- CLI 仍可完成项目、素材、归集、检索、导出和归档
- 草稿生成与改写能力可降级为模板化或人工补全流程

## 10. 与阶段 5 任务的映射

### 任务 1：报告项目与素材收集

- 对应 `project create` 和 `asset add`

### 任务 2：素材归集与用途标记

- 对应 `collection build`
- 补充 `Asset.usage_note`

### 任务 3：复用定位

- 对应 `reuse find`

### 任务 4：主草稿生成

- 对应 `draft create`

### 任务 5：主草稿改写

- 对应 `draft update`

### 任务 6：最终报告归档

- 对应 `export render` 和 `archive finalize`

## 11. 第一版验收标准

当以下条件全部满足时，可认为实现说明足以支持开发启动：

- 命令入口已经固定
- 核心对象字段已经固定
- 文件解析接口已经固定
- 导出接口已经固定
- 开发者可以明确区分“Markdown 当前实现”和“Word 后续扩展”
- 多类型素材输入能力已经和阶段 5 六个任务建立一一对应关系
