# DraftCore 开发环境说明

## 1. 目的

本文定义 DraftCore 第一版的本地开发环境约定，确保开发者在 Windows 本地环境中可以稳定完成项目初始化、依赖安装、数据库启动和本地调试。

## 2. 适用范围

- 单机开发
- Windows 优先
- Python 项目初始化
- 本地 SQLite 开发
- 本地文件样例调试

本文不覆盖 CI/CD、发布流水线或生产部署。

## 3. 推荐环境

### 3.1 操作系统

- Windows 10 或 Windows 11

### 3.2 Python 版本

- 推荐：Python 3.12
- 最低支持建议：Python 3.11

统一建议在第一版开发期间固定一个主版本，避免依赖和类型行为在多人或多环境之间漂移。

### 3.3 包管理方式

建议二选一，并在项目初始化时尽早固定：

- `uv`
- `pip` + `venv`

如果没有特殊要求，推荐优先使用 `uv`，因为它在 Windows 本地初始化速度更快，也更适合后续管理开发依赖。

## 4. 推荐依赖分层

### 4.1 运行时依赖

- `typer`
- `sqlmodel`
- `sqlalchemy`
- `pydantic`
- `python-docx`
- `python-pptx`
- `tomli` 或 Python 3.11+ 内置 `tomllib`

### 4.2 开发依赖

- `pytest`
- `pytest-cov`
- `ruff`
- `mypy`

是否在第一版引入 `pre-commit` 可以后置，但建议尽早决定。

## 5. 本地初始化流程

以下流程是建议顺序，不要求当前仓库已经具备这些文件。

### 5.1 创建虚拟环境

使用 `uv`：

```powershell
uv venv
```

使用 `venv`：

```powershell
python -m venv .venv
```

### 5.2 激活环境

```powershell
.venv\Scripts\Activate.ps1
```

### 5.3 安装依赖

```powershell
uv sync
```

或：

```powershell
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 5.4 验证 Python 可用

```powershell
python --version
```

### 5.5 验证 CLI 可执行

```powershell
python -m draftcore.app.cli --help
```

## 6. 建议的本地目录约定

建议在工作区内明确以下目录：

```text
draftcore/
  app/
  data/
    db/
    outputs/
  samples/
    assets/
    expected/
  tests/
```

约定说明：

- `data/db/`：本地 SQLite 文件
- `data/outputs/`：导出的 Markdown 和最终报告
- `samples/assets/`：用于调试解析器和工作流的样例素材
- `samples/expected/`：样例素材的预期解析结果
- `tests/`：测试代码

## 7. 本地数据库约定

- 默认数据库使用 SQLite
- 默认数据库文件建议放在 `data/db/draftcore.db`
- 开发期允许删除重建数据库
- 正式进入真实数据测试前，建议保留单独的样例数据库和临时数据库

## 8. 开发期常用命令建议

这些命令在项目初始化后应尽快稳定下来：

```powershell
python -m draftcore.app.cli --help
pytest
ruff check .
mypy draftcore
```

## 9. 样例数据准备建议

在开始实现解析器和工作流前，建议准备最小样例集：

- 1 个 `md` 样例
- 1 个 `txt` 样例
- 1 个 `docx` 样例
- 1 个 `pptx` 样例
- 2 个图片样例
- 1 份模板素材
- 1 份历史参考成果

这些样例应尽量覆盖：

- 正常可抽取文本
- 可登记但只能部分抽取
- 路径级管理但不参与正文语义复用

## 10. 开发环境验收标准

当以下条件满足时，可认为开发环境已准备就绪：

- 本地 Python 版本符合约定
- 虚拟环境可以正常激活
- 依赖可以完整安装
- 可以运行基本静态检查和测试命令
- 可以创建和访问本地 SQLite 文件
- 可以读取本地样例素材

## 11. 待后续补充项

本文当前只固定最小约定，后续可以继续补充：

- `pyproject.toml` 结构
- 格式化与 lint 统一配置
- `pre-commit` 约定
- 发布构建方式
