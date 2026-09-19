#!/usr/bin/env python3
"""AGENTS.md 模型与推理路由器（Jev 版）

依据 mai-unstoppable/AGENTS.md「模型与推理深度」分级表，把任务描述路由到
优先模型 + 起始推理深度。置信度低于阈值时升级给主代理（表内第 5 档原则）。

用法：
    python3 model-router.py "任务描述文本"
    python3 model-router.py            # 交互式逐条输入
"""
import json
import sys

from typesafe_sdk import Choice, Score, TypeSafeClient

# AGENTS.md 分级表（2026-09-15 核对版）
TIERS = {
    "mechanical": {
        "model": "gpt-5.6-luna", "effort": "low",
        "desc": "路径清点、字段提取、标签遗漏、冻结文本逐项比对；工具即可完成则不委派",
    },
    "general": {
        "model": "gpt-5.6-sol", "effort": "medium",
        "desc": "已有母稿的平台改写、素材说明、常规来源核查、同口径数据整理",
    },
    "engineering": {
        "model": "gpt-5.6-terra", "effort": "medium",
        "desc": "代码与工程文件定位、明确需求的 Remotion/官网局部实现、可复现修复",
    },
    "review": {
        "model": "gpt-5.6-sol", "effort": "high",
        "desc": "复杂稿件事实复核、指标口径冲突、重要成片或工程验收（工程逻辑复核可用 terra）",
    },
    "deep": {
        "model": "主代理(必要时 gpt-6-astra)", "effort": "high~xhigh",
        "desc": "多轮仍无法定位的故障、跨内容策略取舍、叙事与技术强耦合、重大不确定性",
    },
}

STATE_TMPL = (
    "个人媒体项目（内容单元为中心）的任务分派。可执行档位及标准：\n"
    + "\n".join(f"- {k}: {v['desc']}" for k, v in TIERS.items())
    + "\n\n任务描述：{task}"
)

EFFORT_RUBRIC = [
    "1.0 需检查假设、反例、跨文件逻辑（验收级）",
    "0.7 常规多步工作，需要中等推理",
    "0.4 机械核对、输入完整规则确定",
    "0.0 纯检索或单步操作",
]


def route(client, task: str) -> dict:
    r = client.system_one(
        state=STATE_TMPL.format(task=task),
        questions={
            "tier": Choice(
                instructions="按分级表标准，该任务最属于哪一档？"
                             "注意：工具（脚本/命令）即可完成的不委派，选 mechanical。",
                criteria={k: v["desc"] for k, v in TIERS.items()},
            ),
            "effort_need": Score(
                instructions="该任务的推理深度需求，0 到 1",
                criteria=EFFORT_RUBRIC,
            ),
        },
    )
    tier = r.answers["tier"]
    effort = r.answers["effort_need"].score
    conf = tier.confidence
    result = {
        "tier": tier.choice,
        "model": TIERS[tier.choice]["model"],
        "effort_hint": TIERS[tier.choice]["effort"],
        "jev_effort_score": round(effort, 2),
        "confidence": round(conf, 2),
        "probabilities": tier.probabilities,
    }
    # 门控：低置信升级给主代理（AGENTS.md 第 5 档原则）
    if conf < 0.6:
        result["gate"] = "LOW CONFIDENCE -> 主代理直接处理或重新描述任务"
    return result


if __name__ == "__main__":
    tasks = sys.argv[1:] or [ln.strip() for ln in sys.stdin if ln.strip()]
    with TypeSafeClient() as c:
        for t in tasks:
            res = route(c, t)
            print(f"任务: {t[:60]}")
            print(json.dumps(res, ensure_ascii=False, indent=2))
            print("-" * 60)
