# DraftCore 配置说明

## 1. 目的

本文定义 DraftCore 第一版的本地配置边界，说明配置文件放在哪里、包含哪些字段、默认值如何处理，以及缺省配置时系统应怎样降级。

## 2. 配置原则

- 配置仅服务于本地 CLI 使用
- 采用 TOML 格式
- 配置优先描述目录、数据库、输出和 AI Provider
- 缺省配置时，基础闭环仍应可运行
- AI 相关配置缺失时，不应阻塞项目、素材、归集、导出和归档

## 3. 配置文件位置建议

第一版建议支持以下优先级：

1. 命令行显式传入的配置路径
2. 工作区下的 `draftcore.toml`
3. 用户目录下的默认配置文件

如果三个位置都不存在，系统应使用内置默认值启动。

## 4. 建议配置结构

```toml
[workspace]
root_dir = "./data"
assets_dir = "./samples/assets"
output_dir = "./data/outputs"

[database]
path = "./data/db/draftcore.db"
echo = false

[defaults]
target_output = "markdown"
project_status = "active"

[ai]
enabled = false
provider = ""
model = ""
api_base = ""
api_key_env = ""

[logging]
level = "INFO"
```

## 5. 配置字段说明

### 5.1 `[workspace]`

- `root_dir`
  - 工作区数据根目录
  - 用于承载数据库、导出物和运行时文件

- `assets_dir`
  - 默认样例素材目录
  - 可用于开发期快速导入测试素材

- `output_dir`
  - 默认导出目录
  - `export render` 和 `archive finalize` 默认写入这里

### 5.2 `[database]`

- `path`
  - SQLite 文件路径
  - 第一版建议为相对工作区的本地路径

- `echo`
  - 是否输出 SQL 调试日志
  - 开发期可开启，默认建议关闭

### 5.3 `[defaults]`

- `target_output`
  - 默认输出格式
  - 第一版固定建议为 `markdown`

- `project_status`
  - 新项目默认状态
  - 推荐默认值为 `active`

### 5.4 `[ai]`

- `enabled`
  - 是否启用 AI 能力

- `provider`
  - AI Provider 标识

- `model`
  - 默认模型名

- `api_base`
  - 自定义接口地址

- `api_key_env`
  - 读取 API Key 的环境变量名

### 5.5 `[logging]`

- `level`
  - 日志等级
  - 建议支持 `DEBUG`、`INFO`、`WARNING`、`ERROR`

## 6. 默认值与降级行为

### 6.1 无配置文件时

系统应至少具备以下默认行为：

- 自动使用默认数据库路径
- 自动使用默认输出目录
- AI 视为关闭
- CLI 基础命令仍可运行

### 6.2 AI 配置不完整时

- 不应中断基础流程
- `draft create` 和 `draft update` 可降级为模板化或人工骨架模式
- 应给出清晰提示，说明当前运行在非 AI 模式

### 6.3 路径不存在时

- 若是输出目录不存在，可自动创建
- 若是数据库父目录不存在，可自动创建
- 若是素材输入路径不存在，应在业务命令层返回错误，而不是在配置加载阶段静默吞掉

## 7. 环境变量建议

第一版建议支持以下环境变量模式：

- `DRAFTCORE_CONFIG`
- `DRAFTCORE_DB_PATH`
- `DRAFTCORE_OUTPUT_DIR`
- `DRAFTCORE_AI_API_KEY`

建议原则：

- 环境变量用于覆盖敏感信息或环境差异
- 敏感信息不直接写入仓库内配置文件

## 8. 配置校验规则

配置加载后应至少完成以下校验：

- 数据库路径非空
- 输出目录非空
- `target_output` 必须是当前支持的输出格式
- AI 开启时，`provider` 和 `model` 不能为空
- AI 开启时，如果需要密钥，`api_key_env` 必须可解析到有效环境变量

## 9. 示例

### 9.1 最小本地配置

```toml
[database]
path = "./data/db/draftcore.db"

[defaults]
target_output = "markdown"
```

### 9.2 启用 AI 的配置

```toml
[database]
path = "./data/db/draftcore.db"

[defaults]
target_output = "markdown"

[ai]
enabled = true
provider = "openai"
model = "gpt-5.4-mini"
api_key_env = "DRAFTCORE_AI_API_KEY"
```

## 10. 配置文档验收标准

当以下问题都能直接回答时，可认为配置说明足够支撑开发：

- 配置文件放哪里
- 默认数据库和输出目录在哪里
- AI 配置缺失时如何降级
- 环境变量如何覆盖配置
- 哪些字段必须校验
