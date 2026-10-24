# CrossBot AI Skills — 欧洲跨境电商 Agent Skills（开源）

把 CrossBot AI 的核心合规与规则能力打包成 [Agent Skills](https://github.com/anthropics/skills)
格式，可直接装进 Claude Code / Cursor / Codex / Windsurf 等任何支持 Skills 的 AI Agent。

## 可用 Skills

| Skill | 目录 | 能力 |
|---|---|---|
| **gpsr-compliance-checker** | [`gpsr-compliance-checker/`](gpsr-compliance-checker/) | GPSR (EU) 2023/988 合规体检：7 类 CE 类目识别、欧代/警示语检查清单、可直接粘贴的多语言合规块、**差评安全词扫描 + 15 天 Safety Gate 上报预警** |
| **eu-marketplace-rules** | [`eu-marketplace-rules/`](eu-marketplace-rules/) | 欧洲 13 平台 Listing 规则库：标题字数/必需语言/GPSR 要点（Amazon EU+US、Allegro、Otto、Kaufland、Zalando、bol.com、Cdiscount、eMAG、Fruugo、eBay、Walmart、TikTok Shop） |

## 安装

```bash
# Claude Code
npx skills add <repo-url> --skill gpsr-compliance-checker -g
npx skills add <repo-url> --skill eu-marketplace-rules -g
```

或手动把 skill 目录复制到 Agent 的 skills 目录。

## 使用示例

- 「检查我的 Kids Building Blocks listing 是否符合 GPSR，生成德语合规块」
- 「我收到一条差评说充电宝冒烟了，我该怎么办？」→ 触发 15 天上报预警
- 「Allegro 上架标题最多多少字符？用什么语言？」

## 数据同步

Skill 内的 `data/*.json` 由仓库脚本从 CrossBot AI 后端引擎导出，规则与
生产服务一致。本地重新生成：

```bash
cd backend && ../.venv/Scripts/python.exe ../tools/export_skill_data.py
```

## 免责声明

输出为工程辅助建议，不构成法律意见。平台规则与法规以官方最新文本为准。

## License

MIT
