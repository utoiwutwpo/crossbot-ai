"""
质量验证脚本 — 上线前的「真实 LLM 质量门禁」

用法（项目根目录）：
    backend/.venv/Scripts/python.exe tools/verify_quality.py

行为：
- backend/.env 配了 LLM_API_KEY → 跑真实生成，输出波兰语/罗马尼亚语/德语样张供人工判读
- 未配置 → 明确告知，并输出 Mock 基线（仅验证管道连通，不代表真实质量）

检查项（每语言）：生成成功 / 标题字数 ≤ 平台上限 / GPSR 合规块存在 / 非空描述
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings                              # noqa: E402
from app.experts.product_description import ProductDescriptionExpert  # noqa: E402
from app.experts.gpsr import check as gpsr_check             # noqa: E402
from app.schemas import ProductDescriptionRequest            # noqa: E402

CASES = [
    # (平台, 语言, 产品名, 关键词) — 对应 PL/RO 社群投放的主打场景
    ("allegro", "pl", "Smart Sleep Mask", ["sleep", "bluetooth", "mask"]),
    ("emag", "ro", "Smart Sleep Mask", ["sleep", "bluetooth", "mask"]),
    ("otto", "de", "Wireless Earbuds Pro", ["wireless", "earbuds", "bluetooth"]),
    ("tiktok", "en", "LED Makeup Mirror", ["makeup", "led", "mirror"]),
]


def main() -> int:
    mode = "真实 LLM（智谱 GLM-4）" if settings.llm_api_key else "Mock（未配 LLM_API_KEY，仅验证管道）"
    print(f"=== CrossBot AI 质量验证 | 模式: {mode} ===\n")
    expert = ProductDescriptionExpert()
    failures = 0

    for platform, lang, name, kws in CASES:
        req = ProductDescriptionRequest(
            product_name=name, keywords=kws, platform=platform, language=lang)
        try:
            out = expert.generate(req)
        except Exception as e:
            print(f"[FAIL] {platform}/{lang}: 生成异常 {e}")
            failures += 1
            continue

        cfg_rules = {
            "allegro": 75, "emag": 150, "otto": 70, "tiktok": 255,
        }
        title_ok = len(out.title) <= cfg_rules[platform]
        desc_ok = len(out.description) >= 50
        gpsr = gpsr_check(name, kws, platform)
        gpsr_ok = (not gpsr["ce_required"]) or bool(out.gpsr_block)

        status = "PASS" if (title_ok and desc_ok and gpsr_ok) else "FAIL"
        if status == "FAIL":
            failures += 1
        print(f"[{status}] {platform}/{lang} 标题{len(out.title)}字(≤{cfg_rules[platform]})"
              f" 描述{len(out.description)}字 GPSR块={bool(out.gpsr_block)} 分={out.optimization_score}")
        print(f"  标题: {out.title}")
        print(f"  五点1: {out.bullet_points[0].heading} — {out.bullet_points[0].content[:90]}")
        print(f"  描述: {out.description[:120]}…")
        print()

    if not settings.llm_api_key:
        print("⚠️ 当前为 Mock 基线：只证明管道连通。判读真实 PL/RO 质量请在 backend/.env 填 LLM_API_KEY 后重跑。")
    print(f"=== 结果: {len(CASES) - failures}/{len(CASES)} 通过 ===")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
