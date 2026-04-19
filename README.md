# DraftCore

DraftCore 是一个面向个人报告工作流的本地 CLI 工具。

它的目标不是做通用知识库，也不是做高保真文档编辑器，而是把分散在本地目录中的多类型素材组织成可复用输入，并支撑以下最小闭环：

1. 创建报告项目
2. 登记和归集本地素材
3. 从模板和历史成果中定位可复用内容
4. 生成和改写主草稿
5. 导出 Markdown
6. 归档最终报告并保留追溯关系

当前仓库仍处于开发准备阶段，重点是先把 MVP 的产品边界、架构边界和实现约定固定下来。

## 当前状态

- 已完成 MVP 范围说明
- 已完成阶段任务拆解
- 已完成总体架构与技术选型
- 已完成第一版实现骨架说明
- 已补充开发启动所需的基础工程文档
- 代码尚未开始搭建

## 文档导航

建议按以下顺序阅读：

1. [实施说明.md](/E:/MYcoede/DraftCore/实施说明.md)
2. [阶段5任务清单.md](/E:/MYcoede/DraftCore/阶段5任务清单.md)
3. [PRD-lite](docs/PRD-lite.md)
4. [总体架构](docs/architecture.md)
5. [技术选型 ADR](docs/adr/001-tech-stack.md)
6. [开发落地说明](docs/implementation-guide.md)
7. [开发环境](docs/dev-setup.md)
8. [配置说明](docs/configuration.md)
9. [CLI 规格](docs/cli-spec.md)
10. [数据模型](docs/schema.md)
11. [测试策略](docs/testing.md)

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

详细理由见 [docs/adr/001-tech-stack.md](/E:/MYcoede/DraftCore/docs/adr/001-tech-stack.md)。

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

详细说明见 [docs/implementation-guide.md](/E:/MYcoede/DraftCore/docs/implementation-guide.md)。

## 开发启动前的最小检查项

在正式开始编码前，建议先确认以下文档约定已经稳定：

- CLI 命令边界是否固定
- 数据模型字段和关系是否固定
- 配置字段是否固定
- 各类解析器的输入输出契约是否固定
- 测试样例和验收方式是否固定

## 下一步建议

如果准备正式进入编码阶段，建议按以下顺序推进：

1. 初始化 Python 项目结构与依赖管理
2. 搭建 SQLite 和 SQLModel 基础设施
3. 实现 `project` 和 `asset` 的最小闭环
4. 补齐解析器接口与文本类解析
5. 完成 `collection`、`reuse`、`draft`、`export`、`archive`
6. 为关键流程补齐测试和样例数据
