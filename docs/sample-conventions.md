# DraftCore 样例约定

## 1. 目的

本文定义 DraftCore 在 `samples/` 目录下管理测试样例的最小约定，用于统一：

- 解析器输入样例的组织方式
- 预期输出的表达方式
- 集成测试和验收测试对样例的复用方式

目标是先把样例结构和约束固定下来，再逐步补充真实文件。

## 2. 总体原则

- 样例优先服务于 MVP 主流程，而不是追求覆盖所有边角格式
- 一个样例只表达一个主要意图，避免单个文件承担过多断言
- 原始输入和预期结果分开存放，方便复用和替换
- 允许降级的行为必须显式写清楚，不能靠测试代码猜
- 样例名称应能让人直接看出用途

## 3. 目录约定

建议采用以下结构：

```text
samples/
  assets/
  expected/
```

含义如下：

- `samples/assets/`：原始输入样例，按素材类型或场景组织
- `samples/expected/`：与输入样例对应的期望结果，使用文本或结构化文件表达

在目录真正开始填充前，允许先保留空目录；当前仓库已经开始实际使用这两个目录。

## 4. 命名约定

文件名建议遵循以下模式：

```text
<领域>-<场景>-<编号>.<扩展名>
```

例如：

- `parser-md-basic-01.md`
- `parser-docx-partial-01.docx`
- `workflow-reuse-template-01.md`
- `workflow-export-report-01.json`

命名要求：

- 使用小写英文和中划线
- 编号从 `01` 开始
- 同一场景下，输入样例与期望文件使用相同主名，方便映射

## 5. 输入样例要求

每个输入样例至少应能回答以下问题：

- 这个样例用于验证哪个模块或场景
- 输入是否完整、可正常抽取，还是故意构造的降级场景
- 哪些内容是断言重点

建议优先补以下类型：

- `md` / `txt` 正常文本样例
- `docx` 可部分抽取样例
- `pptx` 含标题与正文的样例
- 图片路径级登记样例
- 模板与历史成果样例

## 6. 期望结果约定

`samples/expected/` 中的期望结果应优先使用可读、可比较的文本格式：

- 结构化结果优先使用 `json`
- 简单文本结果可使用 `md` 或 `txt`
- 需要说明降级原因时，可附加 `yaml` 或 `md` 说明文件

期望结果至少应表达：

- 关键字段或关键文本片段
- 允许为空的字段
- 允许降级但不允许整体失败的部分
- 明确失败时应出现的状态或提示

## 7. 测试映射约定

测试代码读取样例时，建议遵循以下映射规则：

- 一个输入样例对应一个主期望文件
- 测试通过文件主名进行匹配
- 同一输入如需多个断言视角，可追加后缀

对于端到端验收场景，允许使用“多输入样例 + 一个场景期望文件”的组织方式：

- 输入样例仍放在 `samples/assets/`
- 场景级期望文件放在 `samples/expected/`
- 场景期望文件应显式写出涉及哪些输入样例，以及关键验收断言

例如：

```text
samples/assets/parser-docx-partial-01.docx
samples/expected/parser-docx-partial-01.json
samples/expected/parser-docx-partial-01.degraded.md
```

这样可以让解析结果断言和降级说明断言分开维护。

端到端场景示例：

```text
samples/assets/workflow-raw-01.md
samples/assets/workflow-template-01.md
samples/assets/workflow-reference-01.txt
samples/expected/acceptance-task1-01.json
samples/expected/acceptance-task2-01.json
```

## 8. 分层使用建议

- 单元测试：复用小而聚焦的样例，只验证单模块输出
- 集成测试：组合多个样例，验证数据库、文件和服务协作
- 端到端测试：围绕 PRD 场景组织样例，验证完整流程闭环

不要为了方便单测而修改样例语义，测试应适配样例约定，而不是反过来。

## 9. 首批落地建议

在正式编码前，先补齐以下最小集合即可：

1. `samples/assets/` 的目录骨架
2. 至少 1 组 `md` 文本样例
3. 至少 1 组 `docx` 降级样例
4. 至少 1 组 `pptx` 文本抽取样例
5. 至少 1 组模板或历史成果样例
6. 与上述样例一一对应的 `expected/` 文件

当前已落地最小集合：

1. `workflow-raw-01.md` 与对应解析期望
2. `workflow-template-01.md` 与对应解析期望
3. `workflow-reference-01.txt` 与对应解析期望
4. `workflow-image-01.png` 与对应解析期望
5. `acceptance-task1-01.json` 用于任务 1 验收
6. `acceptance-task2-01.json` 用于任务 2 验收

## 10. 验收标准

当团队能直接回答以下问题时，可认为样例约定已经足够支撑开发：

- 新样例该放到哪里
- 输入和期望结果如何对应
- 降级行为如何表达
- 哪些样例用于单测，哪些用于工作流测试
- 新增解析器时应如何补样例
