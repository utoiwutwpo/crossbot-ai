"""
导出 Skill 开源数据包 — 保证 skills/ 里的 JSON 与后端引擎代码永远同步。

用法（在 backend 目录下）：
    ../.venv/Scripts/python.exe ../tools/export_skill_data.py

生成：
    skills/gpsr-compliance-checker/data/gpsr_rules.json
    skills/eu-marketplace-rules/data/platforms.json
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from app.experts.gpsr import CE_RULES, COUNTRY_LANGUAGE, LANG_HEADER  # noqa: E402
from app.experts.platform_registry import PLATFORMS                    # noqa: E402
from app.experts.safety_gate import SAFETY_LEXICON                     # noqa: E402

SKILLS = Path(__file__).resolve().parent.parent / "skills"


def export_gpsr():
    out = SKILLS / "gpsr-compliance-checker" / "data"
    out.mkdir(parents=True, exist_ok=True)
    rules = []
    for r in CE_RULES:
        rules.append({
            "category": r["category"], "label": r["label"],
            "trigger_keywords": r["keywords"],
            "directives": r["directives"],
            "risk": r["risk"], "extra_requirements": r["extra"],
            "warnings_by_language": r["warnings"],
        })
    data = {
        "version": "2026-10-24",
        "regulation": "GPSR (EU) 2023/988 — General Product Safety Regulation",
        "ce_categories": rules,
        "country_to_warning_language": COUNTRY_LANGUAGE,
        "warning_language_headers": LANG_HEADER,
        "safety_incident_lexicon": SAFETY_LEXICON,
        "disclaimer": ("工程辅助工具，不构成法律意见；具体类目适用指令以"
                       "欧盟官方文本与认证机构意见为准。"),
    }
    (out / "gpsr_rules.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ gpsr_rules.json（{len(rules)} 个 CE 类目，"
          f"{sum(len(v) for v in SAFETY_LEXICON.values())} 个安全词）")


def export_platforms():
    out = SKILLS / "eu-marketplace-rules" / "data"
    out.mkdir(parents=True, exist_ok=True)
    data = {
        "version": "2026-10-24",
        "platforms": PLATFORMS,
    }
    (out / "platforms.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ platforms.json（{len(PLATFORMS)} 个平台）")


if __name__ == "__main__":
    export_gpsr()
    export_platforms()
