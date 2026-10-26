<!-- About 简介（推送后填写到仓库 About 栏）：
小白也能做出高点击主图的 Claude Code 插件 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-ecom-design
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, ecommerce, taobao, product-image, design -->

# lhg-ecom-design：小白也能做出高点击主图

> **一句话介绍**：给 AI 助手装上"电商视觉专家"——产品卖点提炼、主图五张图策划、详情页结构、14 条确定性规则做尺寸规范脚本校验、12 项点击率要素清单，小白也能做出点得动的主图。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-ecom-design
> /plugin install lhg-ecom-design@lhg-plugs
> ```

## 它是什么

`lhg-ecom-design` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **4 个命令**（小白入口）：`design` 产品一句话→主图策划案，`detail-page` 详情页结构策划，`size-check` 图片尺寸脚本校验，`audit` 点击率要素人工评审
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：卖点提炼、主图五张图、详情页结构、尺寸规范库
- **3 个专家 agent**：视觉策划、主图评审、独立审计
- **2 个硬门 hooks**：commit 前图片审计拦截、写入大图体积警告（均可一键豁免）
- **14 条确定性审计规则**：纯 Python、零第三方依赖，图片尺寸用文件头解析（不用装 PIL），秒出报告

尺寸规范库 2026-10-11 核实（淘宝 800×800/第五张白底/详情宽 750、拼多多 750×750、抖音 9:16 竖屏；来源为第三方教程汇总，非平台官方最新文档，库内已逐项标注）。

## 4 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-ecom-design:design` | 产品一句话 → 主图五张图策划案（卖点→分镜→尺寸校验→点击率清单） | `/lhg-ecom-design:design "便携充电宝" --platform 淘宝` |
| `/lhg-ecom-design:detail-page` | 详情页分屏大纲（钩子→卖点→场景→参数→信任→行动） | `/lhg-ecom-design:detail-page "便携充电宝"` |
| `/lhg-ecom-design:size-check` | 图片目录一键体检（尺寸/比例/体积/格式/命名/alt） | `/lhg-ecom-design:size-check ./images --platform 拼多多` |
| `/lhg-ecom-design:audit` | 12 项点击率要素人工评审，输出通过/不通过 | `/lhg-ecom-design:audit ./images` |

## 自查说明

自查 = 确定性脚本（机器）+ 人工评审清单（人）：

1. 先跑 `scripts/audit/design_audit.py`（14 条规则），零 LLM 成本；
2. 发现分两级：**blocker**（必须修，commit 前 hook 会拦截：尺寸过小、主图非正方形、不支持的格式、超 3MB）、**warning**（建议修：超 500KB、主图不足 5 张、文件名中文/空格、缺 alt）；
3. 再按 `audit` 命令的 12 项清单过一遍脚本抓不到的（首图 3 秒可读性、禁用词、盗图嫌疑）——首图文字占比脚本无法识别图片内文字，会出一项 warning 提醒人工自查，这是诚实的设计。

blocker 清零才算做完；为清零改规则算作弊，不许。

## 目录结构

```
lhg-ecom-design/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 4 个命令：design / detail-page / size-check / audit
├── skills/                  # 4 个平台中立 skill（lhg-ed-selling/main-image/detail-page/size-spec）
├── agents/                  # 3 个专家 agent（design-planner / main-image-reviewer / auditor）
├── hooks/                   # 2 个硬门（commit 前图片审计拦截 / 大图体积警告）+ 豁免说明
├── scripts/audit/           # 14 条确定性审计规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你要上新品，不知道主图 5 张分别讲什么时 → 用 `/lhg-ecom-design:design`
- 你有一批成图，想在上传前确认尺寸/比例/体积合规时 → 跑 `/lhg-ecom-design:size-check`
- 你老链接点击率长期低于类目均值，怀疑主图讲错了故事时 → 跑 `/lhg-ecom-design:audit` 重做
- 你要给设计师/美工写需求，不想返工三遍时 → 把策划案和尺寸卡直接贴过去

**什么时候不用：**

- 你要的是 AI 直接生成图片本身 → 本插件做的是"策划+校验"，出图请用图像生成工具，成图拿回来用 `size-check` 验
- 你的平台不在淘宝/京东/拼多多/抖音四家之内 → 尺寸规范库没有覆盖，脚本会按淘宝默认口径跑，可能误报
- 你希望 AI 自由发挥、不接受 commit 拦截 → 硬门会让你烦（可关，但那就别装它）

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack) | 小白一句话 → 高质量全栈应用 | `/plugin install lhg-fullstack@lhg-plugs` |
| [lhg-video-edit](https://github.com/lhg-plugs/lhg-video-edit) | 一句话把口播素材剪成爆款短视频（+口播脚本子命令） | `/plugin install lhg-video-edit@lhg-plugs` |
| [lhg-ecom-design](https://github.com/lhg-plugs/lhg-ecom-design) | 电商视觉专家：卖点到高点击主图一键策划 | `/plugin install lhg-ecom-design@lhg-plugs` |
| [lhg-ecom-report](https://github.com/lhg-plugs/lhg-ecom-report) | 电商复盘专家：店铺数据到周/月复盘报告 | `/plugin install lhg-ecom-report@lhg-plugs` |
| *（后续插件在此追加，保持表格格式一致）* | | |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、14 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-ecom-design/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
