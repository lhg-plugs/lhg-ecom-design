---
description: 图片目录一键体检：主图尺寸/比例合规、文件过大、命名问题、缺 alt 等 14 条确定性规则秒出报告。
argument-hint: ["图片目录"] [--platform 淘宝] [--format json|text]
---

# /lhg-ecom-design:size-check —— 图片尺寸规范脚本校验

对 `$ARGUMENTS` 指定的图片目录跑确定性审计。格式：`"<图片目录>" [--platform 淘宝|京东|拼多多|抖音] [--format json|text]`。

## 执行

1. 运行：
   - `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/design_audit.py --target <图片目录> --platform <平台> --format <格式>`
2. 按 blocker / warning 分级呈现结果：
   - **blocker**（必须修）：尺寸过小、主图非正方形（淘宝/京东/拼多多）、不支持的格式（BMP/TIFF）、文件超 3MB
   - **warning**（建议修）：单张超 500KB、主图少于 5 张、文件名含中文或空格、详情页宽度超 790px、缺 alt
3. 每条 blocker 给出修复动作（重导出尺寸 / 压缩 / 转格式），修完重跑直到 blocker 清零。

## 说明
- 尺寸规范依据 `lhg-ed-size-spec`（2026-10-11 核实，第三方教程汇总，非平台官方最新文档）。脚本里凡引用具体数字的规则，detail 都带"以平台最新规范为准"的提醒。
- 首图文字占比脚本无法识别图片内文字，会出一项 warning 提醒人工按 checklist 自查，这是诚实的设计不是 bug。
