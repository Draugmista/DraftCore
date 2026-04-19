# DraftCore

DraftCore 是一个面向个人报告工作流的本地 CLI 工具。

它的目标不是做通用知识库，也不是做高保真文档编辑器，而是把分散在本地目录中的多类型素材组织成可复用输入，并支撑以下最小闭环：

1. 创建报告项目
2. 登记和归集本地素材
3. 从模板和历史成果中定位可复用内容
4. 生成和改写主草稿
5. 导出 Markdown
6. 归档最终报告并保留追溯关系

当前仓库已进入 MVP 第一阶段实现，重点是在不突破边界的前提下，逐步把阶段 5 的任务闭环落到可运行代码与可验证测试上。

## 当前状态

- 已完成 MVP 范围说明
- 已完成阶段任务拆解
- 已完成总体架构与技术选型
- 已完成第一版实现骨架说明与基础工程搭建
- 已落地 `project`、`asset`、`collection` 的最小 CLI/服务/模型闭环
- 已补充任务 1、任务 2 的单元测试、集成测试与端到端验收场景
- 任务 3 至任务 6 仍处于待实现状态

## 文档导航

建议按以下顺序阅读：

1. [实施说明.md](实施说明.md)
2. [阶段5任务清单.md](阶段5任务清单.md)
3. [PRD-lite](docs/PRD-lite.md)
4. [总体架构](docs/architecture.md)
5. [技术选型 ADR](docs/adr/001-tech-stack.md)
6. [开发落地说明](docs/implementation-guide.md)
7. [开发环境](docs/dev-setup.md)
8. [配置说明](docs/configuration.md)
9. [CLI 规格](docs/cli-spec.md)
10. [数据模型](docs/schema.md)
11. [测试策略](docs/testing.md)
12. [样例约定](docs/sample-conventions.md)

## MVP 范围摘要

- 单人使用
- 本地优先
- 报告工作流优先
- 第一版稳定输出为 Markdown
- 支持 `md`、`txt`、`docx`、`pptx`、图片等本地素材
- 第一版不做 Word 导出、OCR、向量检索和多人协作

## 计划技术栈

- 语言：Python
- CLI：Typer
- 数据库：SQLite
- ORM：SQLModel
- 配置：TOML

详细理由见 [docs/adr/001-tech-stack.md](docs/adr/001-tech-stack.md)。

## 建议目录结构

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

详细说明见 [docs/implementation-guide.md](docs/implementation-guide.md)。

## 当前检查重点

在继续推进后续任务前，建议优先确认以下事项：

- CLI 命令边界是否固定
- 数据模型字段和关系是否固定
- 配置字段是否固定
- 各类解析器的输入输出契约是否固定
- 测试样例和验收方式是否固定

## 下一步建议

当前建议按以下顺序继续推进：

1. 实现任务 3 的 `reuse find` 最小闭环
2. 在任务 3 落地后补齐对应单测、集成测试和验收场景
3. 继续推进 `draft`、`export`、`archive`，保持每个任务单独闭环
4. 持续同步 README、CLI 规格、Schema、测试文档，避免实现与约定脱节
