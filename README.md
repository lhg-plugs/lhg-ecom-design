<!-- About 简介（推送后填写到仓库 About 栏）：
小白也能做出高点击主图：产品卖点提炼、主图五张图策划、详情页结构、尺寸规范脚本校验、点击率要素清单，一套电商视觉组合拳。 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-ecom-design
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, ecommerce, taobao, jd, pinduoduo, douyin -->

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="lhg-ecom-design — 小白也能做出高点击主图">
</p>

> **一句话介绍**：小白也能做出高点击主图：产品卖点提炼、主图五张图策划、详情页结构、尺寸规范脚本校验、点击率要素清单，一套电商视觉组合拳。

**一键安装**：在 Claude Code 里运行

```bash
/plugin marketplace add lhg-plugs/lhg-ecom-design
/plugin install lhg-ecom-design@lhg-plugs
```

## 它能帮你做出什么

每条产出先过确定性脚本自查，再交人工复核清单——数字全部数自仓库里的审计脚本，不靠模型"自觉"。

| 自查脚本 | 规则数 | blocker | warning | nit | 覆盖 |
|---|---|---|---|---|---|
| `scripts/audit/design_audit.py` | 13 | 4 | 9 | 0 | 尺寸合规、文件体积、格式、命名、集合、无障碍、人工自查 |
| **合计** | **13** | **4** | **9** | **0** | |

- **零 LLM 成本**：规则是纯 Python 脚本，零第三方依赖，本地运行。
- **坏 / 好对照可验**：`fixtures/` 里备有坏/好用例，冒烟测试断言命中情况。
- **冒烟全绿**：`python3 smoke_test.py` 47 项全部通过（JSON 合法、frontmatter 完整、命令/skill/agent 齐全）。

## 它是什么

`lhg-ecom-design` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **4 个命令**（小白入口）：`audit` 点击率要素人工评审、`design` 产品一句话 → 主图五张图策划案、`detail-page` 详情页结构策划、`size-check` 图片目录一键体检
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：lhg-ed-detail-page, lhg-ed-main-image, lhg-ed-selling, lhg-ed-size-spec
- **3 个专家 agent**：auditor, design-planner, main-image-reviewer
- **2 个 hooks**（`hooks/`：post_image_warn.py, pre_export_check.py），关键操作前自动把关
- **13 条确定性自查规则**：纯 Python 脚本，见上表

## 为什么是它

不是一个 prompt，而是一套互相兜底的机制：

1. **确定性脚本（机器）+ 人工复核清单（人）**：先跑 `scripts/` 下的审计脚本（共 13 条规则），发现分三级：**blocker**（必须修）、**warning**（修或写豁免理由）、**nit**（顺手修）；再按对应 skill 的复核清单过一遍脚本抓不到的（内容真实性、越权、口径一致）。blocker 清零才算做完；为清零改规则算作弊，不许。
2. **硬门，不是提醒**：hooks 在关键操作前自动拦截或警告（见 `hooks/`），而不是只在文档里写一句"请注意"。
3. **方法论沉淀在 skill 里**：流程、检查清单、口径都写在 `skills/` 的方法论里，命令只是入口；换个 agent 平台也能复用同一套做法。
4. **可验，不是可信**：`fixtures/` 备有坏/好对照用例，`smoke_test.py` 一键验证，规则有没有生效、自己跑一遍就知道。

## 快速上手

```bash
# 1. 安装（Claude Code 里运行）
/plugin marketplace add lhg-plugs/lhg-ecom-design
/plugin install lhg-ecom-design@lhg-plugs

# 2. 产品一句话 → 主图五张图策划案：卖点提炼、五张图分镜（钩子/卖点/场景/细节/
/lhg-ecom-design:design "便携充电宝" --platform 淘宝
```

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-ecom-design:audit` | 点击率要素人工评审：首图卖点、价格锚点、信任背书等 12 项清单逐项打分，输出通过/不通过结论。 | `/lhg-ecom-design:audit ./images` |
| `/lhg-ecom-design:design` | 产品一句话 → 主图五张图策划案：卖点提炼、五张图分镜（钩子/卖点/场景/细节/信任）、尺寸规范、点击率要素清单。 | `/lhg-ecom-design:design "便携充电宝" --platform 淘宝` |
| `/lhg-ecom-design:detail-page` | 详情页结构策划：按"首屏钩子→卖点展开→场景→参数→信任→行动"输出分屏大纲与每屏文案要点。 | `/lhg-ecom-design:detail-page "便携充电宝"` |
| `/lhg-ecom-design:size-check` | 图片目录一键体检：主图尺寸/比例合规、文件过大、命名问题、缺 alt 等 14 条确定性规则秒出报告。 | `/lhg-ecom-design:size-check ./images --platform 拼多多` |

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你需要点击率要素人工评审时 → 用 `/lhg-ecom-design:audit`
- 你需要产品一句话 → 主图五张图策划案时 → 用 `/lhg-ecom-design:design`
- 你需要详情页结构策划时 → 用 `/lhg-ecom-design:detail-page`

**什么时候不用：**

- 你只需要其中一个零散能力时 → 本插件是成套流程，单点需求用更轻量的 skill 更合适
- 你希望 AI 完全自由发挥、不接受任何自查与硬门时 → 它的规则审计与 hooks 会介入（可关，但那就别装它）
- 你的场景不在上面命令表覆盖范围内时 → 先看命令表，没有对应命令就别硬套

## 目录结构

```
lhg-ecom-design/
├── smoke_test.py          # 一键冒烟测试
├── ATTRIBUTION.md         # 灵感来源与许可声明
├── LICENSE                # MIT
├── README.md              # 本文件
├── .claude-plugin/
├── agents/
├── commands/
├── fixtures/
├── hooks/
├── scripts/
├── skills/
```

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（本次实测 47 项全部通过）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-ecom-design/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

同门插件见 [lhg-plugs](https://github.com/lhg-plugs)，86 个插件的完整矩阵在 [marketplace](https://github.com/lhg-plugs/marketplace) 维护。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
