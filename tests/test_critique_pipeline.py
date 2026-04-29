"""
Unit tests for the critique pipeline analysis modules.
Tests use mock match data — no DB, no API calls required.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dota_core.roast.models import PlayerMatchStats
from dota_core.roast.multi_match_summary import summarize_last_matches
from dota_core.roast.role_pattern_summary import summarize_role_patterns
from dota_core.roast.evidence_selector import select_critique_evidence
from dota_core.roast.longform_context_builder import build_longform_critique_context
from dota_core.roast.longform_prompt_builder import build_longform_critique_prompt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _match(
    match_id=1, hero="Anti-Mage", position=1, won=True,
    kills=5, deaths=3, assists=2, duration_min=35.0,
    overall_score=58.0, early=65.0, mid=55.0, late=55.0,
    weaknesses=None, strengths=None,
    hero_damage=20000.0, tower_damage=3000.0, net_worth=18000.0, gpm=500.0,
) -> PlayerMatchStats:
    return PlayerMatchStats(
        match_id=match_id, hero_id=1, hero_name=hero,
        position=position, won=won,
        duration_min=duration_min,
        kills=kills, deaths=deaths, assists=assists,
        overall_score=overall_score, position_score=overall_score, hero_score=overall_score,
        early_position_score=early, mid_position_score=mid, late_position_score=late,
        weaknesses=weaknesses or [], strengths=strengths or [],
        hero_damage=hero_damage, tower_damage=tower_damage,
        net_worth=net_worth, gold_per_min=gpm,
    )


def carry_high_farm_low_damage_matches() -> list[PlayerMatchStats]:
    """10 carry games: high net worth but low hero damage and low overall score."""
    return [
        _match(
            match_id=i, hero="Spectre", position=1,
            won=(i % 3 != 0), kills=3, deaths=4, assists=5,
            overall_score=38.0, hero_damage=8000.0, tower_damage=1000.0,
            net_worth=22000.0, gpm=580.0,
            weaknesses=["Hero Damage", "Tower Damage"],
        )
        for i in range(1, 11)
    ]


def support_low_vision_high_deaths_matches() -> list[PlayerMatchStats]:
    """10 support games: high deaths, weak vision (no strengths)."""
    return [
        _match(
            match_id=i, hero="Crystal Maiden", position=5,
            won=(i % 4 == 0), kills=1, deaths=8, assists=10,
            overall_score=31.0, hero_damage=5000.0, tower_damage=500.0,
            weaknesses=["Lane Presence", "Net Worth", "Tower Damage"],
        )
        for i in range(1, 11)
    ]


def mixed_role_matches() -> list[PlayerMatchStats]:
    """Mixed roles — 4 carry, 3 mid, 2 offlane, 1 support."""
    roles = [1, 1, 1, 1, 2, 2, 2, 3, 3, 5]
    return [
        _match(match_id=i, position=roles[i - 1], overall_score=48.0)
        for i in range(1, 11)
    ]


def mid_low_rotation_matches() -> list[PlayerMatchStats]:
    """10 mid games with low score and Tower Damage weakness."""
    return [
        _match(
            match_id=i, hero="Storm Spirit", position=2,
            won=(i % 3 == 0), overall_score=40.0,
            hero_damage=18000.0, tower_damage=800.0,
            weaknesses=["Tower Damage", "Assists"],
        )
        for i in range(1, 11)
    ]


def offlane_no_initiation_matches() -> list[PlayerMatchStats]:
    """10 offlane games with very low tower damage and aggression weakness."""
    return [
        _match(
            match_id=i, hero="Axe", position=3,
            won=(i % 2 == 0), overall_score=35.0,
            hero_damage=12000.0, tower_damage=600.0,
            weaknesses=["Aggression", "Tower Damage"],
        )
        for i in range(1, 11)
    ]


# ---------------------------------------------------------------------------
# Tests: primary_role detection
# ---------------------------------------------------------------------------

def test_carry_primary_role():
    summary = summarize_last_matches(carry_high_farm_low_damage_matches())
    assert summary["primary_role"] == "carry"


def test_support_primary_role():
    summary = summarize_last_matches(support_low_vision_high_deaths_matches())
    assert summary["primary_role"] == "pos5"


def test_mixed_role_primary():
    summary = summarize_last_matches(mixed_role_matches())
    assert summary["primary_role"] == "carry"   # 4/10


def test_mid_primary_role():
    summary = summarize_last_matches(mid_low_rotation_matches())
    assert summary["primary_role"] == "mid"


def test_offlane_primary_role():
    summary = summarize_last_matches(offlane_no_initiation_matches())
    assert summary["primary_role"] == "offlane"


# ---------------------------------------------------------------------------
# Tests: tag aggregation
# ---------------------------------------------------------------------------

def test_carry_tags_aggregated():
    # Populate roast_tags directly (tag engine is tested separately)
    matches = carry_high_farm_low_damage_matches()
    for m in matches:
        m.roast_tags = ["low_hero_damage", "low_objective_damage"]
    summary = summarize_last_matches(matches)
    tags = summary["most_common_problem_tags"]
    assert "low_hero_damage" in tags
    assert "low_objective_damage" in tags


def test_support_tags_aggregated():
    matches = support_low_vision_high_deaths_matches()
    for m in matches:
        m.roast_tags = ["high_death", "pos5_no_impact"]
    summary = summarize_last_matches(matches)
    tags = summary["most_common_problem_tags"]
    assert len(tags) >= 2


# ---------------------------------------------------------------------------
# Tests: evidence selection
# ---------------------------------------------------------------------------

def test_evidence_has_3_examples_when_available():
    # Varied matches ensure deduplication allows 3+ distinct examples
    varied = [
        _match(match_id=i, position=1, won=(i < 6),
               kills=i, deaths=10-i, overall_score=30.0 + i*3,
               weaknesses=["Hero Damage"] if i % 2 == 0 else ["Tower Damage"])
        for i in range(1, 11)
    ]
    evidence = select_critique_evidence(varied)
    assert len(evidence) >= 3, f"Expected >= 3 evidence items, got {len(evidence)}"


def test_evidence_from_support():
    evidence = select_critique_evidence(support_low_vision_high_deaths_matches())
    assert len(evidence) >= 1


def test_evidence_empty_for_empty_matches():
    evidence = select_critique_evidence([])
    assert evidence == {}


# ---------------------------------------------------------------------------
# Tests: prompt validation
# ---------------------------------------------------------------------------

def test_prompt_contains_min_length_requirement():
    matches = carry_high_farm_low_damage_matches()
    context = build_longform_critique_context(matches)
    system_prompt, user_prompt = build_longform_critique_prompt(context)
    assert "350" in system_prompt, "Prompt must specify minimum 350 Chinese words"


def test_prompt_contains_safety_constraints():
    matches = support_low_vision_high_deaths_matches()
    context = build_longform_critique_context(matches)
    system_prompt, _ = build_longform_critique_prompt(context)
    assert "real-life identity" in system_prompt or "harassment" in system_prompt


def test_prompt_requires_concrete_examples():
    matches = mid_low_rotation_matches()
    context = build_longform_critique_context(matches)
    system_prompt, _ = build_longform_critique_prompt(context)
    assert "3" in system_prompt and ("example" in system_prompt or "evidence" in system_prompt)


def test_prompt_includes_player_context():
    matches = offlane_no_initiation_matches()
    context = build_longform_critique_context(matches, {"playerName": "TestPlayer"})
    _, user_prompt = build_longform_critique_prompt(context)
    assert "TestPlayer" in user_prompt


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
