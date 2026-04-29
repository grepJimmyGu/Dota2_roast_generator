"""
Roast tag registry — all structured gameplay-based critique tags.

Maps to spec: packages/core/domain/roast_tags.py

Design principles:
  - Tags are based solely on in-game performance, role responsibility, and match stats.
  - No tags attack real-life identity, appearance, gender, nationality, or any personal attribute.
  - Sarcasm is Dota-flavored and data-grounded.
  - Tags marked evidence_fields document what data is needed; tags only fire when that data exists.

TODO (Future RAG): each tag_id can serve as a key for retrieving example critique passages,
hero-specific punchlines, and role-specific writing patterns from a RAG database.
"""
from __future__ import annotations
from dataclasses import dataclass, field

ALL_ROLES = ["carry", "mid", "offlane", "pos4", "pos5"]


@dataclass(frozen=True)
class RoastTag:
    tag_id:          str
    label_zh:        str
    label_en:        str
    description:     str
    severity_score:  int          # 1 (mild) → 5 (brutal)
    roles:           tuple[str, ...]
    roast_angle:     str          # the specific sarcastic framing
    evidence_fields: tuple[str, ...]  # data fields needed to trigger this tag


# ---------------------------------------------------------------------------
# Registry builder
# ---------------------------------------------------------------------------

def _t(
    tag_id: str,
    label_zh: str,
    label_en: str,
    description: str,
    severity_score: int,
    roles: list[str],
    roast_angle: str,
    evidence_fields: list[str],
) -> RoastTag:
    return RoastTag(
        tag_id=tag_id,
        label_zh=label_zh,
        label_en=label_en,
        description=description,
        severity_score=severity_score,
        roles=tuple(roles),
        roast_angle=roast_angle,
        evidence_fields=tuple(evidence_fields),
    )


# ---------------------------------------------------------------------------
# Common tags (all roles)
# ---------------------------------------------------------------------------

_COMMON_TAGS: list[RoastTag] = [
    _t("high_death", "死亡过多", "High Death Count",
       "死亡次数明显偏高，且没有换到足够击杀、视野、空间或团战收益。",
       3, ALL_ROLES,
       "移动提款机，复活时间比在线时间还稳定。",
       ["deaths", "duration_min"]),

    _t("low_impact_win", "躺赢混子", "Low Impact Win",
       "比赛赢了，但个人参团、输出、推塔、视野或控制贡献偏低。",
       2, ALL_ROLES,
       "赢是赢了，但更像坐上了队友开的顺风车。",
       ["won", "overall_score"]),

    _t("low_impact_loss", "输了且没作用", "Low Impact Loss",
       "比赛输了，同时多个关键贡献指标偏低。",
       4, ALL_ROLES,
       "输的时候没能救场，甚至很难证明自己参加了这把比赛。",
       ["won", "overall_score"]),

    _t("low_teamfight_participation", "低参团", "Low Teamfight Participation",
       "参团率低于该位置合理预期，长期脱离团队节奏。",
       4, ALL_ROLES,
       "队友在打 Dota，你在打单机剧情模式。",
       ["assists", "kills", "duration_min"]),

    _t("bad_itemization", "出装离谱", "Bad Itemization",
       "出装和局势、英雄职责或敌方阵容不匹配。",
       4, ALL_ROLES,
       "装备栏看起来像是系统随机推荐的。",
       ["items"]),  # requires item data — currently unavailable

    _t("no_bkb_core", "核心没 BKB", "Core Missing BKB",
       "核心位在需要魔免或保命装的局势中没有及时补 BKB，导致中后期频繁阵亡。",
       4, ["carry", "mid", "offlane"],
       "把自己当魔免单位，结果进场三秒开始读秒。",
       ["items", "deaths"]),  # requires item data

    _t("fed_enemy_core", "养肥对面核心", "Fed Enemy Core",
       "多次死亡或对线崩盘导致敌方核心快速发育。",
       4, ALL_ROLES,
       "你不是在打对面核心，你是在帮他做天使投资。",
       ["deaths", "early_position_score"]),

    _t("comeback_thrower", "优势局战犯", "Comeback Thrower",
       "队伍曾有明显优势，但该玩家后期连续失误、低输出或关键死亡导致被翻盘。",
       5, ALL_ROLES,
       "对面本来都准备点了，是你把他们重新劝回游戏。",
       ["won", "early_position_score", "late_position_score"]),

    _t("low_objective_damage", "不推塔", "Low Objective Damage",
       "塔伤或目标贡献明显偏低，尤其是核心或推进型英雄。",
       3, ALL_ROLES,
       "对建筑非常友善，像是签了不拆迁协议。",
       ["tower_damage"]),

    _t("low_hero_damage", "英雄伤害低", "Low Hero Damage",
       "英雄伤害明显低于该位置或英雄应有水平。",
       4, ALL_ROLES,
       "团战里最稳定的输出，是你的存在感输出。",
       ["hero_damage", "duration_min"]),

    _t("late_power_spike", "成型太慢", "Late Power Spike",
       "关键装备或强势期来得太晚，错过了比赛节奏窗口。",
       3, ["carry", "mid", "offlane"],
       "英雄是后期英雄，但这把后期没等到你上线。",
       ["early_position_score", "mid_position_score", "late_position_score"]),

    _t("good_stats_low_impact", "数据好看没作用", "Good Stats Low Impact",
       "KDA 或经济看起来不错，但关键团战、推塔、参团或视野贡献不足。",
       3, ALL_ROLES,
       "数据像 MVP，作用像观众席。",
       ["overall_score", "kills", "assists"]),
]

# ---------------------------------------------------------------------------
# Carry tags
# ---------------------------------------------------------------------------

_CARRY_TAGS: list[RoastTag] = [
    _t("farm_black_hole", "刷钱黑洞", "Farm Black Hole",
       "吃了大量资源，但没有把经济转化成输出、推塔或团战影响力。",
       5, ["carry"],
       "把全队资源吸进去，再把作用蒸发掉。",
       ["net_worth", "gold_per_min", "hero_damage", "tower_damage"]),

    _t("afk_farmer", "单机刷子", "AFK Farmer",
       "长时间低参团，主要时间花在刷野或带线，但没有形成足够牵制或后期接管。",
       4, ["carry"],
       "你不是一号位，你是野区长期租客。",
       ["assists", "kills", "last_hits", "duration_min"]),

    _t("paper_carry", "纸糊大哥", "Paper Carry",
       "作为核心频繁死亡，缺少保命意识或防御装备。",
       4, ["carry"],
       "装备还没发挥作用，人先蒸发了。",
       ["deaths", "duration_min"]),

    _t("late_no_impact", "后期没接管", "No Late Game Impact",
       "比赛进入中后期后，核心仍然没有明显团战、推塔或输出贡献。",
       5, ["carry"],
       "队友等你后期，等来的是版本更新。",
       ["late_position_score", "hero_damage", "tower_damage"]),

    _t("carry_no_objective", "不推塔大哥", "Carry Ignores Objectives",
       "一号位塔伤过低，没有把优势转化成地图资源和建筑压力。",
       3, ["carry"],
       "补刀很积极，拆塔很克制。",
       ["tower_damage"]),

    _t("greedy_item_punished", "贪装被惩罚", "Punished for Greedy Items",
       "过度追求输出或发育装，缺少 BKB、林肯、撒旦等必要保命道具，导致关键死亡。",
       4, ["carry"],
       "贪到最后，装备是有了，比赛没了。",
       ["items", "deaths"]),  # requires item data

    _t("low_damage_high_farm", "高经济低输出", "High Farm Low Damage",
       "经济排名靠前，但英雄伤害排名偏低，资源转化率不足。",
       5, ["carry", "mid"],
       "钱刷到了，作用忘买了。",
       ["net_worth", "gold_per_min", "hero_damage"]),

    _t("useless_six_slot", "六神无用", "Useless Six-Slot",
       "游戏时间很长、装备很多，但团战影响力依然很低。",
       5, ["carry"],
       "装备栏像展览馆，团战像游客。",
       ["duration_min", "overall_score", "hero_damage"]),

    _t("carry_lane_disaster", "大哥对线崩盘", "Carry Lane Disaster",
       "对线期补刀、经济或死亡表现很差，导致核心发育起点过低。",
       4, ["carry"],
       "开局不是劣势，是直接自爆。",
       ["early_position_score", "last_hits"]),

    _t("carry_fed_offlane", "养肥对面三号位", "Fed Enemy Offlaner",
       "对线期被敌方三号位压制，甚至让对面三号位提前成型。",
       4, ["carry"],
       "帮对面三号位完成了创业融资。",
       ["early_position_score", "deaths"]),
]

# ---------------------------------------------------------------------------
# Mid tags
# ---------------------------------------------------------------------------

_MID_TAGS: list[RoastTag] = [
    _t("mid_lane_lost", "中路被爆", "Lost Mid Lane",
       "中路对线明显落后，经济、等级或死亡情况劣势明显。",
       4, ["mid"],
       "中路不是对线，是给对面中单做启动仪式。",
       ["early_position_score", "deaths"]),

    _t("no_rotation_mid", "中单不游走", "No Mid Rotation",
       "前中期击杀参与和地图影响力偏低，没有帮助边路打开局面。",
       4, ["mid"],
       "对面中单在全图旅游，你在中路参加补刀训练营。",
       ["kills", "assists", "mid_position_score"]),

    _t("tempo_vacuum", "节奏真空", "Tempo Vacuum",
       "中单没有打出该位置应有的节奏压制或地图威胁。",
       4, ["mid"],
       "地图上没有你的节奏，只有你的补刀轨迹。",
       ["mid_position_score", "assists", "hero_damage"]),

    _t("mid_fed_enemy", "养肥对面中单", "Fed Enemy Mid",
       "被敌方中单击杀或压制，让对方过早进入强势节奏。",
       4, ["mid"],
       "你不是中单，是对面中单的启动器。",
       ["deaths", "early_position_score"]),

    _t("rune_control_fail", "控符失败", "Rune Control Fail",
       "神符控制明显不足，影响中路续航和游走节奏。",
       3, ["mid"],
       "神符跟你像异地恋，全程没见几次。",
       ["rune_pickups"]),  # requires rune data — currently unavailable

    _t("low_damage_mid", "中单输出低", "Low Mid Damage",
       "中单英雄伤害明显偏低，未承担法核或节奏核心输出责任。",
       4, ["mid"],
       "法核打成法辅，输出全靠想象。",
       ["hero_damage", "duration_min"]),

    _t("mid_no_scaling", "没节奏也没后期", "No Tempo No Scaling",
       "前期没有节奏，中后期也没有输出或控制贡献。",
       5, ["mid"],
       "前期没声音，后期没画面，全场静音模式。",
       ["mid_position_score", "late_position_score", "hero_damage"]),

    _t("spell_misser", "技能随缘", "Spell Misser",
       "关键技能命中率低，控制或爆发没有打到关键目标。",
       3, ["mid"],
       "技能不是放出去的，是许愿出去的。",
       ["spell_accuracy"]),  # requires spell data — currently unavailable

    _t("mid_died_solo", "中路单杀提款", "Solo-Killed in Mid",
       "对线期被单杀或早期死亡过多。",
       4, ["mid"],
       "中路开了提款服务，对面刷卡很顺。",
       ["deaths", "kills", "early_position_score"]),

    _t("passive_mid", "和平发育中单", "Passive Mid Farmer",
       "击杀参与、游走和压制力偏低，过度沉迷中路发育。",
       3, ["mid"],
       "你不是中单，你是中路线管。",
       ["kills", "assists", "hero_damage"]),
]

# ---------------------------------------------------------------------------
# Offlane tags
# ---------------------------------------------------------------------------

_OFFLANE_TAGS: list[RoastTag] = [
    _t("no_initiation", "没先手", "No Initiation",
       "三号位没有承担开团职责，控制、先手或团战发起贡献不足。",
       5, ["offlane"],
       "团战没人开，你站在那里像等公交。",
       ["assists", "kills", "mid_position_score"]),

    _t("paper_offlaner", "纸糊前排", "Paper Offlaner",
       "死亡不少，但没有有效承伤、骗技能或制造空间。",
       4, ["offlane"],
       "名义上是前排，实际上一碰就碎。",
       ["deaths", "duration_min", "overall_score"]),

    _t("fake_core_offlane", "伪大哥三号位", "Fake Core Offlaner",
       "出装偏自私，缺少团队装、先手装或功能装。",
       4, ["offlane"],
       "三号位的职责没做，一号位的资源先抢了。",
       ["items", "net_worth"]),  # requires item data

    _t("no_space_created", "没制造空间", "No Space Created",
       "没有通过压制、带线、开团或吸引火力为核心创造发育空间。",
       4, ["offlane"],
       "你不是制造空间，是压缩队友生存空间。",
       ["assists", "overall_score", "tower_damage"]),

    _t("fed_enemy_carry", "养肥对面大哥", "Fed Enemy Carry",
       "对线期没能限制敌方大哥，甚至让对面核心无压力发育。",
       4, ["offlane"],
       "对面大哥这把发育环境像五星级度假村。",
       ["early_position_score", "deaths"]),

    _t("bad_aura_timing", "团队装太慢", "Late Aura Items",
       "Pipe、Crimson、Greaves、Blink 等关键团队或开团装备时间过晚。",
       3, ["offlane"],
       "团队装不是没出，是快递还在路上。",
       ["items"]),  # requires item timing data

    _t("offlane_no_damage_no_tank", "三无三号位", "No Damage No Tank",
       "伤害、承伤、控制贡献都偏低。",
       5, ["offlane"],
       "三号位三无产品：不肉、没控、没伤害。",
       ["hero_damage", "overall_score", "deaths"]),

    _t("blink_no_action", "有跳不打架", "Blink No Action",
       "出到跳刀后仍然击杀参与低，没有形成先手威胁。",
       4, ["offlane"],
       "跳刀买来像装饰品，只负责占格子。",
       ["items", "kills", "assists"]),  # requires item data

    _t("suicide_initiator", "开团式献祭", "Suicide Initiator",
       "经常先进场先死，但没有换到关键控制、击杀或技能。",
       4, ["offlane"],
       "你不是开团，是给团战按开始按钮然后退场。",
       ["deaths", "kills", "assists"]),

    _t("lost_hard_lane", "劣势路真劣势", "Lost the Hard Lane",
       "劣势路对线崩盘，经济低、死亡多，没能牵制敌方核心。",
       4, ["offlane"],
       "劣势路被你打出了名字本意。",
       ["early_position_score", "deaths"]),
]

# ---------------------------------------------------------------------------
# Pos 4 tags
# ---------------------------------------------------------------------------

_POS4_TAGS: list[RoastTag] = [
    _t("pos4_no_roam", "四号位不游走", "Pos4 No Roam",
       "前中期游走、击杀参与和边路支援不足。",
       4, ["pos4"],
       "四号位不游走，像给地图开了定位锁。",
       ["kills", "assists", "mid_position_score"]),

    _t("pos4_low_control", "控制不足", "Low Crowd Control",
       "控制时长、stun 或关键技能命中贡献偏低。",
       4, ["pos4"],
       "技能都在，但控制像没联网。",
       ["stun_duration"]),  # requires stun data — currently unavailable

    _t("pos4_greedy", "四号位贪经济", "Greedy Pos4",
       "经济占用偏高，但辅助道具、视野或团队贡献不足。",
       4, ["pos4"],
       "名字是辅助，心里住着一号位。",
       ["gold_per_min", "assists", "hero_damage"]),

    _t("pos4_no_impact", "四号位没存在感", "Pos4 No Impact",
       "参团、控制、伤害和节奏贡献都不明显。",
       4, ["pos4"],
       "这把四号位最大的贡献，是让队友怀疑少排了一个人。",
       ["overall_score", "assists", "kills"]),

    _t("pos4_feed", "游走送人头", "Roaming Feeder",
       "死亡多，但没有换到有效击杀、视野、压制或节奏。",
       4, ["pos4"],
       "你不是游走，是移动送货上门。",
       ["deaths", "kills", "assists"]),

    _t("pos4_no_save", "不救人", "No Saves",
       "有救人英雄、技能或道具条件，但没有形成有效保护。",
       3, ["pos4"],
       "队友快死了，你在旁边做见证人。",
       ["saves"]),  # requires save tracking — currently unavailable

    _t("pos4_bad_lane", "对线帮倒忙", "Bad Lane Support",
       "对线期没能帮助三号位，反而导致己方劣势路更难打。",
       4, ["pos4"],
       "劣势路已经难了，你还给它加了专家模式。",
       ["early_position_score", "assists"]),

    _t("pos4_no_vision_help", "不帮视野", "No Vision Help",
       "作为四号位几乎不补充关键视野或反眼。",
       3, ["pos4"],
       "视野外包失败，地图黑得很平均。",
       ["observer_wards", "sentry_wards"]),  # requires ward data

    _t("pos4_damage_padding", "伤害刷子", "Damage Padding",
       "伤害数据看起来不错，但关键控制、救人、开团和节奏贡献不足。",
       3, ["pos4"],
       "伤害是刷出来了，比赛影响力还在加载。",
       ["hero_damage", "assists", "overall_score"]),

    _t("pos4_item_delay", "关键道具慢", "Late Key Items",
       "Force Staff、Glimmer、Blink、Shard 等关键功能装时间过晚。",
       3, ["pos4"],
       "救人装明天到，队友今天先走。",
       ["items"]),  # requires item timing data
]

# ---------------------------------------------------------------------------
# Pos 5 tags
# ---------------------------------------------------------------------------

_POS5_TAGS: list[RoastTag] = [
    _t("no_vision_support", "不做视野", "No Vision",
       "眼位数量明显不足，导致团队缺少地图信息。",
       5, ["pos5"],
       "地图黑得像停电，队友进野区像开盲盒。",
       ["observer_wards"]),  # requires ward data

    _t("bad_vision_support", "视野质量差", "Poor Vision Quality",
       "虽然买眼或插眼，但关键区域无视野，或眼位容易被反。",
       4, ["pos5"],
       "眼是插了，但像是插给自己心安的。",
       ["observer_wards", "sentry_wards"]),  # requires ward data

    _t("pos5_feed", "五号位狂送", "Pos5 Feeding",
       "死亡过多，且没有用死亡换到视野、技能、救人或团战收益。",
       4, ["pos5"],
       "移动工资包，刷新就上线。",
       ["deaths", "duration_min"]),

    _t("no_save_support", "不保人", "No Saves",
       "没有有效保护核心，救人技能或道具使用价值偏低。",
       4, ["pos5"],
       "大哥被切的时候，你像现场观众。",
       ["saves"]),  # requires save tracking

    _t("greedy_pos5", "五号位贪经济", "Greedy Pos5",
       "五号位经济占用偏高，但视野、团队道具或保护贡献不足。",
       4, ["pos5"],
       "你说你是五号位，但装备路线有自己的野心。",
       ["gold_per_min", "assists"]),

    _t("no_lane_protection", "不保线", "No Lane Protection",
       "对线期没有保护己方大哥，导致核心开局发育困难。",
       4, ["pos5"],
       "大哥不是被对面打崩的，是被你放养长大的。",
       ["early_position_score", "assists"]),

    _t("low_disable_support", "没控制", "Low Disable",
       "控制、打断或限制敌方核心的贡献偏低。",
       3, ["pos5"],
       "技能栏挺热闹，控制效果很安静。",
       ["stun_duration"]),  # requires stun data

    _t("late_support_items", "辅助装太慢", "Late Support Items",
       "Force Staff、Glimmer Cape、Lotus、Shard 等关键辅助装备过晚。",
       3, ["pos5"],
       "救人装到货的时候，队友已经投胎了。",
       ["items"]),  # requires item timing data

    _t("pos5_no_impact", "五号位无存在感", "Pos5 No Impact",
       "视野、保人、控制、参团等贡献都偏低。",
       4, ["pos5"],
       "团队里最稳定的位置，是你在小地图上的空白。",
       ["overall_score", "assists", "kills"]),

    _t("died_with_spells", "有技能不放就死", "Died With Spells",
       "有关键技能或道具但死亡前没有使用，导致团战价值浪费。",
       4, ["pos5"],
       "技能带进泉水，主打一个来世再放。",
       ["spell_usage"]),  # requires spell tracking
]

# ---------------------------------------------------------------------------
# Central registry
# ---------------------------------------------------------------------------

ROAST_TAG_REGISTRY: dict[str, RoastTag] = {
    tag.tag_id: tag
    for tag in _COMMON_TAGS + _CARRY_TAGS + _MID_TAGS + _OFFLANE_TAGS + _POS4_TAGS + _POS5_TAGS
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_roast_tag(tag_id: str) -> RoastTag | None:
    return ROAST_TAG_REGISTRY.get(tag_id)


def get_tags_for_role(role: str) -> list[RoastTag]:
    """Return all tags applicable to a role (common + role-specific)."""
    return [t for t in ROAST_TAG_REGISTRY.values() if role in t.roles]


def get_tag_descriptions(tag_ids: list[str]) -> list[str]:
    return [t.description for tag_id in tag_ids if (t := ROAST_TAG_REGISTRY.get(tag_id))]


def get_tag_roast_angles(tag_ids: list[str]) -> list[str]:
    return [t.roast_angle for tag_id in tag_ids if (t := ROAST_TAG_REGISTRY.get(tag_id))]


def get_tag_labels_zh(tag_ids: list[str]) -> list[str]:
    return [t.label_zh for tag_id in tag_ids if (t := ROAST_TAG_REGISTRY.get(tag_id))]
