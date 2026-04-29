"""
Unit tests for the roast tag system.
No DB, no API calls required.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dota_core.roast.roast_tags import (
    ROAST_TAG_REGISTRY, RoastTag,
    get_roast_tag, get_tags_for_role,
    get_tag_descriptions, get_tag_roast_angles, get_tag_labels_zh,
)
from dota_core.roast.tag_rules.common  import tag_common
from dota_core.roast.tag_rules.carry   import tag_carry
from dota_core.roast.tag_rules.mid     import tag_mid
from dota_core.roast.tag_rules.offlane import tag_offlane
from dota_core.roast.tag_rules.pos4    import tag_pos4
from dota_core.roast.tag_rules.pos5    import tag_pos5
from dota_core.roast.tag_engine        import run_tag_rules


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _player(
    position=1, won=True, kills=5, deaths=3, assists=6,
    duration_min=38.0, overall_score=52.0,
    early=55.0, mid=50.0, late=50.0,
    hero_damage=22000.0, tower_damage=3000.0,
    net_worth=19000.0, gpm=490.0, last_hits=250.0,
) -> dict:
    return dict(
        position=position, won=won, kills=kills, deaths=deaths, assists=assists,
        duration_min=duration_min, overall_score=overall_score,
        early_position_score=early, mid_position_score=mid, late_position_score=late,
        hero_damage=hero_damage, tower_damage=tower_damage,
        net_worth=net_worth, gold_per_min=gpm, last_hits=last_hits,
    )


# ---------------------------------------------------------------------------
# Registry integrity tests
# ---------------------------------------------------------------------------

def test_all_tag_ids_unique():
    ids = list(ROAST_TAG_REGISTRY.keys())
    assert len(ids) == len(set(ids)), "Duplicate tag IDs found"


def test_all_tags_have_required_fields():
    for tag_id, tag in ROAST_TAG_REGISTRY.items():
        assert tag.label_zh,        f"{tag_id} missing label_zh"
        assert tag.description,     f"{tag_id} missing description"
        assert tag.severity_score,  f"{tag_id} missing severity_score"
        assert tag.roles,           f"{tag_id} missing roles"
        assert tag.roast_angle,     f"{tag_id} missing roast_angle"


def test_total_tag_count():
    # 12 common + 10 carry + 10 mid + 10 offlane + 10 pos4 + 10 pos5 = 62
    assert len(ROAST_TAG_REGISTRY) == 62, f"Expected 62 tags, got {len(ROAST_TAG_REGISTRY)}"


def test_get_roast_tag_found():
    tag = get_roast_tag("low_damage_high_farm")
    assert tag is not None
    assert tag.tag_id == "low_damage_high_farm"


def test_get_roast_tag_not_found():
    assert get_roast_tag("nonexistent_tag") is None


def test_get_tags_for_carry_includes_common_and_carry():
    tags = get_tags_for_role("carry")
    ids  = {t.tag_id for t in tags}
    assert "high_death"          in ids   # common
    assert "farm_black_hole"     in ids   # carry-specific
    assert "low_damage_high_farm" in ids  # carry-specific
    # should NOT include pos5-only tags
    assert "no_vision_support" not in ids


def test_get_tags_for_pos5_includes_common_and_pos5():
    tags = get_tags_for_role("pos5")
    ids  = {t.tag_id for t in tags}
    assert "high_death"       in ids
    assert "no_vision_support" in ids
    assert "farm_black_hole"  not in ids


def test_get_tag_labels_zh():
    labels = get_tag_labels_zh(["low_damage_high_farm", "afk_farmer"])
    assert labels == ["高经济低输出", "单机刷子"]


def test_get_tag_descriptions_returns_strings():
    descs = get_tag_descriptions(["high_death", "comeback_thrower"])
    assert len(descs) == 2
    assert all(isinstance(d, str) and len(d) > 5 for d in descs)


def test_get_tag_roast_angles():
    angles = get_tag_roast_angles(["farm_black_hole"])
    assert len(angles) == 1
    assert "资源" in angles[0]


# ---------------------------------------------------------------------------
# Rule function tests — correct tags fire
# ---------------------------------------------------------------------------

def test_high_death_fires():
    p = _player(deaths=9, duration_min=35)
    tags = tag_common(p, p)
    assert "high_death" in tags


def test_high_death_does_not_fire_for_low_deaths():
    p = _player(deaths=3, duration_min=40)
    tags = tag_common(p, p)
    assert "high_death" not in tags


def test_low_impact_win_fires():
    p = _player(won=True, overall_score=38.0)
    tags = tag_common(p, p)
    assert "low_impact_win" in tags


def test_low_impact_loss_fires():
    p = _player(won=False, overall_score=32.0)
    tags = tag_common(p, p)
    assert "low_impact_loss" in tags


def test_comeback_thrower_fires():
    p = _player(won=False, early=70.0, late=35.0, overall_score=45.0)
    tags = tag_common(p, p)
    assert "comeback_thrower" in tags


def test_comeback_thrower_does_not_fire_on_win():
    p = _player(won=True, early=70.0, late=35.0)
    tags = tag_common(p, p)
    assert "comeback_thrower" not in tags


def test_carry_farm_black_hole_fires():
    p = _player(position=1, gpm=560, net_worth=24000, hero_damage=5000, tower_damage=800)
    tags = tag_carry(p, p)
    assert "farm_black_hole" in tags


def test_carry_lane_disaster_fires():
    p = _player(position=1, early=28.0, last_hits=80, duration_min=35)
    tags = tag_carry(p, p)
    assert "carry_lane_disaster" in tags


def test_mid_no_rotation_fires():
    p = _player(position=2, kills=2, assists=3, duration_min=40, mid=38.0)
    tags = tag_mid(p, p)
    assert "no_rotation_mid" in tags


def test_mid_no_scaling_fires():
    p = _player(position=2, mid=36.0, late=38.0, hero_damage=10000)
    tags = tag_mid(p, p)
    assert "mid_no_scaling" in tags


def test_offlane_suicide_initiator_fires():
    p = _player(position=3, kills=2, deaths=9, assists=4)
    tags = tag_offlane(p, p)
    assert "suicide_initiator" in tags


def test_offlane_lost_lane_fires():
    p = _player(position=3, early=30.0, deaths=6)
    tags = tag_offlane(p, p)
    assert "lost_hard_lane" in tags


def test_pos4_no_impact_fires():
    p = _player(position=4, overall_score=36.0, assists=4, kills=1)
    tags = tag_pos4(p, p)
    assert "pos4_no_impact" in tags


def test_pos4_feed_fires():
    p = _player(position=4, deaths=8, kills=1, assists=5)
    tags = tag_pos4(p, p)
    assert "pos4_feed" in tags


def test_pos5_feed_fires():
    p = _player(position=5, deaths=10, duration_min=35)
    tags = tag_pos5(p, p)
    assert "pos5_feed" in tags


def test_pos5_no_impact_fires():
    p = _player(position=5, overall_score=32.0, assists=3, kills=1)
    tags = tag_pos5(p, p)
    assert "pos5_no_impact" in tags


# ---------------------------------------------------------------------------
# Missing data safety tests
# ---------------------------------------------------------------------------

def test_missing_hero_damage_does_not_crash():
    p = _player()
    p.pop("hero_damage", None)
    p["hero_damage"] = None
    tags = tag_common(p, p)   # should not raise
    assert isinstance(tags, list)


def test_missing_deaths_does_not_crash():
    p = _player()
    p["deaths"] = None
    tags = tag_common(p, p)
    assert "high_death" not in tags


def test_empty_player_dict_does_not_crash():
    tags = run_tag_rules({})
    assert isinstance(tags, list)


def test_all_none_fields_do_not_crash():
    p = {k: None for k in [
        "position", "won", "kills", "deaths", "assists", "duration_min",
        "overall_score", "early_position_score", "mid_position_score", "late_position_score",
        "hero_damage", "tower_damage", "net_worth", "gold_per_min", "last_hits",
    ]}
    p["duration_min"] = 1.0  # avoid division by zero
    for fn in [tag_common, tag_carry, tag_mid, tag_offlane, tag_pos4, tag_pos5]:
        result = fn(p, p)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# run_tag_rules integration
# ---------------------------------------------------------------------------

def test_run_tag_rules_sorted_by_severity():
    p = _player(position=1, deaths=10, won=False, overall_score=28.0,
                early=28.0, mid=30.0, late=28.0, hero_damage=4000, gpm=550, net_worth=22000)
    tags = run_tag_rules(p)
    assert len(tags) > 0
    severities = [ROAST_TAG_REGISTRY[t].severity_score for t in tags if t in ROAST_TAG_REGISTRY]
    assert severities == sorted(severities, reverse=True)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
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
