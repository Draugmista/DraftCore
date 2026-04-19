# DraftCore CLI 规格

## 1. 目的

本文把第一版 CLI 从“命令清单”进一步细化为“接口规格”，用于约束命令边界、参数命名、输出语义和错误处理方式。

## 2. 设计原则

- 命令按工作流组织
- 尽量显式，不做过度魔法行为
- 输出优先面向人类可读
- 错误提示必须可用于定位问题
- 第一版以非交互命令为主，允许少量确认型交互

## 3. 全局约定

### 3.1 命令入口

建议主入口为：

```powershell
draftcore <group> <command> [options]
```

在开发阶段，也可先使用：

```powershell
python -m draftcore.app.cli <group> <command> [options]
```

### 3.2 全局参数

建议预留以下全局参数：

- `--config`
- `--db-path`
- `--output-dir`
- `--json`
- `--verbose`

说明：

- `--json` 用于机器可读输出
- 非 `--json` 模式下默认输出人类可读文本

### 3.3 全局错误语义

命令失败时至少区分以下类别：

- 配置错误
- 参数错误
- 文件路径不可访问
- 数据对象不存在
- 解析失败
- 导出失败
- 归档失败

错误消息应尽量包含：

- 哪个对象失败
- 哪个路径失败
- 属于输入问题还是系统问题

## 4. 命令规格

## 4.1 `project`

### `project create`

用途：

- 创建报告项目

建议参数：

- `--name`
- `--topic`
- `--target-output`

最小成功输出：

- 项目 ID
- 项目名称
- 项目主题
- 目标输出格式

失败条件：

- `name` 或 `topic` 缺失
- 数据库不可写

### `project list`

用途：

- 列出已创建项目

建议参数：

- `--status`
- `--limit`

最小成功输出：

- 项目列表
- 每项至少显示 `id`、`name`、`status`

### `project show`

用途：

- 查看单个项目详情

建议参数：

- `--project-id`

最小成功输出：

- 项目基础信息
- 关联素材数量
- 当前草稿状态
- 最终报告状态

## 4.2 `asset`

### `asset add`

用途：

- 将本地文件登记为素材

建议参数：

- `--project-id`
- `--path`
- `--source-category`
- `--usage-note`

最小成功输出：

- 素材 ID
- 文件名
- 文件类型
- 来源类别
- 抽取状态

失败条件：

- 文件路径不存在
- 项目不存在
- 来源类别非法

### `asset list`

用途：

- 查看项目下素材范围

建议参数：

- `--project-id`
- `--source-category`
- `--used-only`

### `asset show`

用途：

- 查看素材详情

建议参数：

- `--asset-id`

最小成功输出：

- 元数据
- 抽取状态
- 内容摘要
- 关联项目

## 4.3 `collection`

### `collection build`

用途：

- 围绕项目建立素材集合
- 以 `project_id + name` 做 create-or-refresh，输出当前项目可用输入上下文

建议参数：

- `--project-id`
- `--name`
- `--purpose`

最小成功输出：

- 集合 ID
- 纳入素材数量
- 用途说明覆盖情况
- 候选素材数量

行为约定：

- 命令读取当前项目下全部已登记素材
- 同一项目下同名集合重复执行时，刷新集合快照而不是累积重复项
- 若项目下没有任何素材，命令失败
- 用途说明优先级为 `project_assets.relation_note -> assets.usage_note -> 来源类别默认说明`
- 第一版默认说明映射：
  - `raw -> background reference`
  - `template -> structure template`
  - `reference -> history reference`
- 候选区分规则：
  - `template`、`reference` 默认进入候选
  - `raw` 仅在存在显式备注时进入候选

### `collection show`

用途：

- 查看素材集合

建议参数：

- `--collection-id`

最小成功输出：

- 集合基础信息，如 `id`、`project_id`、`name`、`purpose`
- 汇总信息，如 `asset_count`、`candidate_count`、`collected_only_count`
- `usage_note_coverage`
- 素材明细项，至少包含 `asset_id`、`asset_name`、`source_category`、`usage_note`、`is_candidate`、`ingestion_status`

## 4.4 `reuse`

### `reuse find`

用途：

- 查找可复用结构、章节或片段

建议参数：

- `--project-id`
- `--collection-id`
- `--keywords`
- `--limit`

最小成功输出：

- `project_id`
- `collection_id`
- 候选清单
- 模板候选数、历史候选数、降级候选数
- 每项的来源素材
- 每项的复用理由

行为约定：

- 显式传入 `--collection-id` 时，必须属于当前 `project_id`
- 未传 `--collection-id` 时，只有项目下恰好一个集合才自动选用；若存在多个集合则报错，要求显式指定
- 同一项目重复执行时，按项目刷新旧 `reuse_candidates`，本次结果即当前项目最新复用清单
- 仅处理集合中 `template` 与 `reference` 来源类别的素材
- `keywords` 为大小写不敏感的最小文本过滤条件，匹配范围包括标题、摘要、结构摘录、抽取正文和集合用途说明
- 第一版排序仅使用简单 `score_hint`，不引入复杂评分和语义排序

失败条件：

- 项目或集合不存在
- 无可用参考或模板素材
- 项目下集合不唯一且未传 `--collection-id`
- 只产出路径级参考，未形成内容级或结构级复用结果

## 4.5 `draft`

### `draft create`

用途：

- 生成主草稿

建议参数：

- `--project-id`
- `--collection-id`
- `--reuse-from-latest`
- `--title`

最小成功输出：

- 草稿 ID
- 草稿名称
- 章节数
- 生成模式
- 素材引用数
- 复用引用数

生成模式建议区分：

- `ai`
- `template`
- `manual-fallback`

当前 MVP 约束：

- 每个项目只允许一个主草稿；若草稿已存在，`draft create` 应失败
- 当前实现只读取项目最新一批 `reuse_candidates`
- 若项目下集合不唯一且未传 `--collection-id`，命令应失败
- 若尚未执行 `reuse find`，命令应失败并提示先准备复用结果

### `draft update`

用途：

- 改写现有主草稿

建议参数：

- `--draft-id`
- `--instructions`
- `--use-latest-assets`

最小成功输出：

- 草稿 ID
- 新版本标识
- 更新摘要

行为约定：

- 始终更新同一条主草稿记录，不新建第二份草稿
- `version_label` 按 `vN -> vN+1` 递增；若旧值不可解析，则按修订次数回退生成
- 成功更新后，草稿状态进入 `ready`
- `--use-latest-assets` 为真时，纳入当前项目中尚未进入草稿上下文的最新素材，并补写 `draft_asset_refs`
- 更新结果至少返回：
  - `id`
  - `project_id`
  - `name`
  - `previous_version_label`
  - `version_label`
  - `status`
  - `updated_section_count`
  - `asset_ref_count`
  - `assets_added_count`
  - `change_summary`
  - `changed_sections`
  - `revision_count`
  - `updated_at`

失败条件：

- 草稿不存在
- `instructions` 为空
- 草稿内容损坏，无法形成可编辑章节

### `draft show`

用途：

- 查看草稿详情

建议参数：

- `--draft-id`

最小成功输出：

- 草稿元数据
- 结构化章节与文本块
- 来源快照摘要
- 素材引用数与复用引用数
- 修订次数与最近一次修订摘要

## 4.6 `export`

### `export render`

用途：

- 将结构化草稿渲染为 Markdown

建议参数：

- `--draft-id`
- `--format`
- `--output-path`

第一版约束：

- `format` 仅支持 `markdown`

最小成功输出：

- 生成文件路径
- 导出格式

## 4.7 `archive`

### `archive finalize`

用途：

- 生成最终报告并写入归档记录

建议参数：

- `--project-id`
- `--draft-id`
- `--output-path`
- `--name`

最小成功输出：

- 最终报告 ID
- 输出文件路径
- 归档时间

### `archive show`

用途：

- 查看归档结果与追溯关系

建议参数：

- `--report-id`
- `--project-id`

## 5. 输出风格建议

### 5.1 默认文本输出

适用于人工使用，应强调：

- 关键对象 ID
- 关键状态
- 文件路径
- 是否成功

### 5.2 JSON 输出

适用于脚本或自动化：

- 字段命名保持稳定
- 不混入额外说明性文字

## 6. 第一版不做的 CLI 能力

- 多轮交互式向导
- 远程服务模式
- Web API
- 复杂批处理 DSL
- 多用户会话管理

## 7. CLI 文档验收标准

当以下问题都能被直接回答时，可认为 CLI 规格足够稳定：

- 每个命令叫什么
- 每个命令最少需要哪些参数
- 成功时返回什么
- 失败时怎么报错
- 哪些参数属于第一版正式承诺
