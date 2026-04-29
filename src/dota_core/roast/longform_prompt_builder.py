"""
Build the final LLM prompt from the structured context.

Maps to spec: packages/core/roast/longform_prompt_builder.py
"""
from __future__ import annotations
import json


_SYSTEM_PROMPT = """You are a Dota 2 long-form performance critique generator.

You will receive a structured summary of a player's last matches, including role distribution, \
average stats, recurring problem tags, and selected evidence examples.

Your task is to write a Chinese long-form critique that sounds like a sharp, sarcastic, \
experienced Dota 2 player or streamer reviewing this player's recent performance.

This is not a generic insult generator. The critique must be grounded in the data.

Writing requirements:
- Write in Chinese
- Minimum 350 Chinese words
- Use a sarcastic Dota pub tone
- Be funny, specific, and sharp
- Analyze performance by role
- Mention the primary role
- Mention recurring patterns across the last 10 matches
- Cite at least 3 concrete match examples from the provided evidence
- Explain why the tags were triggered
- Connect the critique to role responsibilities
- End with a memorable punchline

Safety and quality rules:
- Only criticize in-game performance, decisions, stats, role execution, itemization, vision, \
tempo, and objective impact
- Do not criticize real-life identity, intelligence, appearance, gender, nationality, race, \
religion, sexuality, disability, or mental health
- Do not use threats, harassment instructions, slurs, or sexual insults
- Do not fabricate stats not present in the context
- If a stat field is null or missing, do not mention it
- Do not make the critique purely abusive — it must remain data-backed
- Make it feel like a data-backed roast, not random flaming

Return a JSON object with this exact schema:
{
  "title": "短标题（10字以内）",
  "primary_role": "主要位置",
  "overall_verdict": "一句话总结（20字以内）",
  "critique": "正文（至少350中文字）",
  "key_problem_tags": ["问题标签1", "问题标签2"],
  "evidence_used": [{"match_id": "...", "reason": "引用原因"}],
  "final_punchline": "结尾神评论（30字以内）",
  "tone": "light | medium | high"
}

Return ONLY the JSON object. No markdown, no code fences, no additional text.
"""

# TODO (Future RAG): inject high-quality critique examples, role-specific
# punchline templates, hero-specific jokes, and writing style examples here
# via a retrieval step before constructing the user prompt.


def build_longform_critique_prompt(context: dict, language: str = "zh") -> tuple[str, str]:
    """
    Build (system_prompt, user_prompt) for the LLM.
    language parameter reserved for future EN support; currently always zh.
    """
    # Omit null fields from evidence to reduce token count
    evidence = context.get("selected_evidence", {})
    clean_evidence: dict = {}
    for key, val in evidence.items():
        if val is None:
            continue
        clean_evidence[key] = {k: v for k, v in val.items() if v is not None}

    # Build compact context for user prompt
    user_context = {
        "player_name":            context.get("player_name"),
        "total_matches":          context.get("total_matches"),
        "primary_role":           context.get("primary_role"),
        "critique_focus":         context.get("critique_focus"),
        "tone_level":             context.get("tone_level"),
        "overall_summary": {
            k: v for k, v in (context.get("overall_summary") or {}).items()
            if v is not None and v != [] and v != {}
        },
        "role_patterns": context.get("role_patterns", {}),
        "recurring_roast_tags":   context.get("recurring_roast_tags", []),
        "selected_evidence":      clean_evidence,
    }

    user_prompt = f"Player context (JSON):\n{json.dumps(user_context, ensure_ascii=False, indent=2)}"

    return _SYSTEM_PROMPT, user_prompt
