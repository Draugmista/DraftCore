# DraftCore 数据模型与 Schema 说明

## 1. 目的

本文把第一版核心对象从“字段列表”进一步细化为“数据模型约定”，用于指导 SQLModel 建模、SQLite 建表和对象关系设计。

## 2. 设计原则

- 数据库存对象关系与运行状态
- 文件系统存原始素材和导出结果
- 第一版优先保证可追溯，而不是复杂版本管理
- 不复制原始大文件正文到数据库
- 允许为抽取结果保存摘要和可检索文本

## 3. 核心实体

## 3.1 `report_projects`

用途：

- 表示一次具体报告任务

建议字段：

- `id`
- `name`
- `topic`
- `target_output`
- `status`
- `created_at`
- `updated_at`

约束建议：

- `name` 非空
- `topic` 非空
- `target_output` 第一版默认 `markdown`

## 3.2 `assets`

用途：

- 表示被纳入管理的本地素材文件

建议字段：

- `id`
- `name`
- `path`
- `file_type`
- `source_category`
- `topic_or_task`
- `usage_note`
- `ingestion_status`
- `created_at`
- `updated_at`

约束建议：

- `path` 非空
- `file_type` 非空
- `source_category` 非空
- `path` 建议唯一

拍板结论：

- `assets` 表示全局素材主档，不直接挂 `project_id`
- 同一物理文件按规范化绝对路径只登记一次
- 是否被某个项目使用，不放在 `assets` 上，而放在项目关系表和后续引用表中表达
- `source_category` 表示该素材的主业务属性，第一版先按素材主属性登记，不做“同一素材在不同项目下切换类别”的复杂建模

枚举建议：

- `file_type`
  - `md`
  - `txt`
  - `docx`
  - `pptx`
  - `image`
  - `xlsx`
  - `unknown`

- `source_category`
  - `raw`
  - `template`
  - `reference`

- `ingestion_status`
  - `pending`
  - `parsed`
  - `partial`
  - `failed`

## 3.3 `asset_content_profiles`

用途：

- 保存解析后的标准化内容摘要

建议字段：

- `asset_id`
- `title`
- `summary`
- `searchable_text`
- `structure_excerpt`
- `page_count`
- `paragraph_count`
- `parser_name`
- `extracted_at`

约束建议：

- `asset_id` 唯一
- `asset_id` 外键指向 `assets.id`

说明：

- 第一版允许 `searchable_text` 为空，尤其是图片素材
- `structure_excerpt` 存最小结构信息，而不是完整格式树

## 3.4 `asset_collections`

用途：

- 表示围绕项目组织出的素材集合

建议字段：

- `id`
- `project_id`
- `name`
- `purpose`
- `created_at`

约束建议：

- `project_id` 外键指向 `report_projects.id`

## 3.5 `asset_collection_items`

用途：

- 表示素材和素材集合的多对多关系

建议字段：

- `collection_id`
- `asset_id`
- `usage_note`
- `priority_hint`
- `is_candidate`
- `created_at`

说明：

- `is_candidate` 用于区分“已收集”和“更可能被使用”

## 3.6 `project_assets`

用途：

- 表示项目和素材的多对多关系

建议字段：

- `project_id`
- `asset_id`
- `relation_note`
- `linked_at`

约束建议：

- `project_id` 外键指向 `report_projects.id`
- `asset_id` 外键指向 `assets.id`
- `project_id + asset_id` 联合唯一

说明：

- 第一版明确使用关系表，不再把 `project_id` 直接放在 `assets` 上
- 该表负责表达“这个素材已被纳入这个项目范围”
- `relation_note` 只放项目内补充说明，例如“本项目中作为背景参考”或“本项目中作为结构模板”
- 是否进入草稿或最终报告，不在本表强行记录，分别由 `draft_asset_refs` 和 `final_report_asset_refs` 追踪

## 3.7 `reuse_candidates`

用途：

- 保存复用定位结果

建议字段：

- `id`
- `project_id`
- `asset_id`
- `candidate_type`
- `snippet`
- `reason`
- `score_hint`
- `created_at`

枚举建议：

- `candidate_type`
  - `structure`
  - `section`
  - `paragraph`
  - `expression`
  - `path_reference`

说明：

- `path_reference` 只表示降级参考，不代表正文级复用成功

## 3.8 `drafts`

用途：

- 保存主草稿元数据

建议字段：

- `id`
- `project_id`
- `name`
- `version_label`
- `status`
- `content_model`
- `source_snapshot`
- `created_at`
- `updated_at`

约束建议：

- `project_id` 外键指向 `report_projects.id`
- `content_model` 非空

枚举建议：

- `status`
  - `draft`
  - `ready`
  - `archived`

说明：

- `content_model` 建议以 JSON 形式保存结构化章节和文本块
- `source_snapshot` 建议记录生成时使用过的素材和复用候选 ID

## 3.9 `draft_asset_refs`

用途：

- 保存草稿与素材的引用关系

建议字段：

- `draft_id`
- `asset_id`
- `ref_type`
- `created_at`

## 3.10 `draft_reuse_refs`

用途：

- 保存草稿与复用候选的引用关系

建议字段：

- `draft_id`
- `reuse_candidate_id`
- `created_at`

## 3.11 `final_reports`

用途：

- 保存最终归档成果

建议字段：

- `id`
- `project_id`
- `draft_id`
- `name`
- `output_format`
- `output_path`
- `archived_at`

约束建议：

- `project_id` 外键指向 `report_projects.id`
- `draft_id` 外键指向 `drafts.id`
- `output_path` 非空

## 3.12 `final_report_asset_refs`

用途：

- 保存最终报告与素材来源的关系

建议字段：

- `final_report_id`
- `asset_id`
- `ref_role`

## 3.13 `final_report_reuse_refs`

用途：

- 保存最终报告与复用候选的关系

建议字段：

- `final_report_id`
- `reuse_candidate_id`

## 4. 关键关系

- 一个项目可关联多个素材
- 一个项目可关联多个素材集合
- 一个素材可被多个项目复用，前提是它在 `assets` 中只保留一条主档记录
- 一个项目在第一版默认只有一个主草稿，但数据库设计可允许多个版本记录
- 一个草稿可关联多个素材与多个复用候选
- 一个最终报告必须追溯到其来源草稿
- 一个最终报告必须能追溯到使用过的素材与复用候选

关系落地顺序拍板如下：

1. 素材先登记到 `assets`
2. 项目纳入范围时写入 `project_assets`
3. 围绕当前任务组织输入上下文时写入 `asset_collections` 和 `asset_collection_items`
4. 真正进入草稿或终稿引用时，再写入 `draft_asset_refs` 或 `final_report_asset_refs`

这样可以把“已登记”“已纳入项目”“更可能使用”“实际已使用”四层语义拆开，避免一个字段承载过多状态。

## 5. 建模建议

### 5.1 时间字段

所有核心实体建议统一包含：

- `created_at`
- `updated_at`

纯关系表可以只保留：

- `created_at`
或
- `linked_at`

### 5.2 路径字段

- 路径建议保存为规范化绝对路径
- Windows 下建议在写入前统一归一化分隔符和大小写比较策略

### 5.3 JSON 字段

建议优先用于以下场景：

- `drafts.content_model`
- `drafts.source_snapshot`

第一版不要把大量不稳定业务结构都塞进 JSON，避免后续查询能力变差。

## 6. 初始化与迁移建议

- 第一版可先使用简单初始化脚本创建全部表
- 在 Schema 还不稳定时，可以接受开发期删库重建
- 一旦进入真实数据试运行，建议尽快引入迁移工具

如果后续要引入迁移，优先考虑：

- `alembic`

## 7. 第一版不做的 Schema 能力

- 复杂审批流
- 多人协作锁
- 云同步状态
- 向量索引表
- 重型版本树

## 8. Schema 验收标准

当以下问题都能被清晰回答时，可认为数据模型说明足以指导编码：

- 每个核心对象怎么建模
- 哪些是实体表，哪些是关系表
- 哪些字段必须非空
- 哪些状态需要枚举
- 草稿和最终报告如何保留追溯关系
