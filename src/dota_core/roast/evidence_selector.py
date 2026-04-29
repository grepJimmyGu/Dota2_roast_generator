"""
Select the most roast-worthy match examples for LLM context.

Maps to spec: packages/core/analysis/evidence_selector.py
"""
from __future__ import annotations
from dota_core.roast.models import PlayerMatchStats

ROLE_NAMES = {1: "carry", 2: "mid", 3: "offlane", 4: "pos4", 5: "pos5"}


def _match_evidence(m: PlayerMatchStats, reason: str) -> dict:
    return {
        "match_id":              m.match_id,
        "hero":                  m.hero_name or f"Hero#{m.hero_id}",
        "role":                  ROLE_NAMES.get(m.position, f"pos{m.position}"),
        "result":                "win" if m.won else ("loss" if m.won is False else "unknown"),
        "duration_min":          round(m.duration_min, 1),
        "kills":                 m.kills,
        "deaths":                m.deaths,
        "assists":               m.assists,
        "gpm":                   round(m.gold_per_min) if m.gold_per_min else None,
        "hero_damage":           round(m.hero_damage)  if m.hero_damage  else None,
        "tower_damage":          round(m.tower_damage) if m.tower_damage else None,
        "overall_score":         m.overall_score,
        "problem_tags":          m.roast_tags,
        "short_evidence_summary": reason,
    }


def select_critique_evidence(matches: list[PlayerMatchStats], max_examples: int = 4) -> dict:
    """
    Select up to max_examples concrete matches for LLM citation.

    Selection strategy:
      worst_loss_example:       loss with high deaths or lowest overall score
      best_win_example:         win with highest overall score or big damage
      most_typical_problem_match: match with the most recurring problem tags
      funniest_roastable_match: sharpest stat contradiction (farm ≠ damage, etc.)
    """
    if not matches:
        return {}

    losses = [m for m in matches if m.won is False]
    wins   = [m for m in matches if m.won is True]

    # worst_loss: most deaths + lowest score
    worst_loss = None
    if losses:
        worst_loss = max(
            losses,
            key=lambda m: (m.deaths or 0) * 2 + (100 - (m.overall_score or 50)),
        )

    # best_win: highest overall score among wins
    best_win = None
    if wins:
        best_win = max(wins, key=lambda m: m.overall_score or 0)

    # most_typical_problem: most roast tags fired
    typical = max(matches, key=lambda m: len(m.roast_tags))

    # funniest contradiction: high net worth but low score (farm ≠ impact)
    def _contradiction_score(m: PlayerMatchStats) -> float:
        # High farm, low damage → carry farming without fighting
        carry_paradox = (
            (m.net_worth or 0) / 1000
            - (m.hero_damage or 0) / 5000
            if m.position == 1 else 0
        )
        # High score but lost (throw)
        throw_paradox = (
            (m.overall_score or 0) / 10
            if m.won is False and (m.early_position_score or 0) > 55 else 0
        )
        # Support with no damage and no wards (scored poorly)
        support_void = (
            (50 - (m.overall_score or 50))
            if m.position in {4, 5} else 0
        )
        return carry_paradox + throw_paradox + support_void

    funniest = max(matches, key=_contradiction_score)

    selected: dict[str, dict | None] = {}

    if worst_loss:
        selected["worst_loss_example"] = _match_evidence(
            worst_loss,
            f"死了{worst_loss.deaths}次，综合评分{worst_loss.overall_score:.0f}" if worst_loss.deaths and worst_loss.overall_score else "表现最差的败场"
        )
    if best_win:
        selected["best_win_example"] = _match_evidence(
            best_win,
            f"最佳胜场，评分{best_win.overall_score:.0f}" if best_win.overall_score else "最佳胜场"
        )
    already = {id(worst_loss), id(best_win)}
    if typical and id(typical) not in already:
        selected["most_typical_problem_match"] = _match_evidence(
            typical,
            f"最具代表性的问题场次：{', '.join(typical.roast_tags[:2])}"
        )
        already.add(id(typical))
    if funniest and id(funniest) not in already:
        selected["funniest_roastable_match"] = _match_evidence(
            funniest,
            "数据矛盾最明显的场次，适合重点吐槽"
        )

    return selected
