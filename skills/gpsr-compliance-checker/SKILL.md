---
name: gpsr-compliance-checker
description: "GPSR (EU) 2023/988 合规体检器。检查电商 listing 是否符合欧盟通用产品安全法规：CE 类目识别、欧代/欧盟责任人、当地语言警示语、法定检查清单、可直接粘贴的 GPSR 合规块。适用于 Amazon EU / eBay / Allegro / Otto / Kaufland / Zalando / bol.com 等欧洲平台的中国及非欧盟卖家。Use when: seller asks about GPSR compliance, CE marking, EU responsible person, product safety warnings, listing takedown risk in the EU."
---

# GPSR 合规体检（EU 2023/988）

自 2024-12-13 起强制执行：缺少欧盟责任人（欧代）或当地语言警示语的 listing
会被平台下架。Amazon EU 自 2025 Q1 起在上架前强制校验 CE + 欧代。

## 工作流程

1. **载入规则库**：读取本目录 `data/gpsr_rules.json`
   （7 个 CE 类目 / 国家→警示语语言映射 / 安全事件词库）。
2. **类目识别**：对用户提供的「产品名 + 关键词」做小写子串匹配，
   找出命中的 CE 类目（按命中关键词数排序）。
3. **计算语言要求**：根据销售平台/国家，查
   `country_to_warning_language` 得到必需的警示语语言。
4. **输出体检报告**，包含以下 7 项法定检查（Art.9）：
   - 制造商名称 + 邮政地址 + 联系方式
   - 欧盟授权代表（欧代）— 中国卖家必备
   - 产品标识（型号/批次/序列号）
   - 当地语言安全警示与说明书
   - 商品图片（产品 + 标签/包装）
   - CE 标识（CE 类目强制）
5. **生成 GPSR 合规块**：按必需语言输出可直接粘贴进 listing 的合规文本
   （欧代占位 + 当地语言警示语，取自 `warnings_by_language`）。

## 输出格式

```
🛡️ GPSR 体检报告
- 识别类目：<label>（<directives>）
- 风险等级：high / medium / low
- 必需警示语语言：<languages>
- 检查清单：7 项逐条 ✅/⚠️/❌
- 缺失项修复建议（引用 extra_requirements）

📋 GPSR 合规块（直接粘贴）：
[EN/DE/FR...] Safety & Compliance Information ...
Responsible Economic Operator (EU): [欧代名称], [地址], [邮箱]
Product: <name> | Model/Batch: [型号]
• <当地语言警示语>
```

## 安全事件预警（Art.35 — 15 天上报义务）

如果用户粘贴了买家差评/退货反馈，用 `safety_incident_lexicon`（69 个
安全词，覆盖 fire/electrical/choking/mechanical/allergy 五类）扫描。
**命中任一安全词必须立即警告用户**：

> GPSR Art.35：制造商/欧代「知晓」严重事故后 **15 日内** 必须上报
> （严重风险走 EU Safety Gate 门户）。「知晓」从看到差评那一刻起计时。

并给出行动清单：停售评估 → 保留样品证据 → 15 天内 Safety Gate 上报 →
通知欧代 → 复核 DoC 标准版本 → 全渠道撤下同批次风险品。

## 平台规则速查

需要具体平台的标题字数/语言/GPSR 执行细节时，配合
`eu-marketplace-rules` Skill 使用（或读其 `data/platforms.json`）。

## 免责声明

本 Skill 输出为工程辅助建议，不构成法律意见；具体类目适用指令以
欧盟官方文本（EUR-Lex）与认证机构意见为准。
