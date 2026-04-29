"""
Test scoring pipeline on a single match.
Usage: PYTHONPATH=src python test_match.py <steam_account_id>
"""
import sys
from dota_core.ingest.player_fetch import get_ranked_matches
from dota_core.ingest.match_fetch import get_match_detail
from dota_core.scoring.score_match import score_match
from dota_core.scoring.features import extract_phase_stats
from dota_core.benchmarks.fetch import get_phase_benchmarks
from dota_core.benchmarks.transform import build_phase_benchmarks
from dota_core.scoring.adjusters import game_closeness, benchmark_multiplier
from dota_core.domain.heroes import hero_name


def run(steam_account_id: int):
    print(f"\n{'='*60}")
    print(f"Steam ID: {steam_account_id}")
    print(f"{'='*60}")

    # Step 1: fetch the most recent ranked match
    print("\n[1] Fetching most recent ranked match...")
    df = get_ranked_matches(steam_account_id, total=1, batch_size=1)
    if df.empty:
        print("No ranked matches found.")
        return

    row = df.iloc[0]
    match_id     = int(row["match_id"])
    hero_id      = int(row["heroId"]) if row["heroId"] else 0
    position     = int(row["position"]) if row["position"] else 0
    duration_sec = int(row["duration_seconds"])

    print(f"  match_id             : {match_id}")
    print(f"  hero_id              : {hero_id}  ({hero_name(hero_id)})")
    print(f"  position             : {position}")
    print(f"  duration             : {duration_sec//60}m {duration_sec%60}s")
    print(f"  won                  : {row['won']}")
    print(f"  average_rank         : {row['average_rank']}")
    print(f"  kills/deaths/assists : {row['kills']}/{row['deaths']}/{row['assists']}")

    # Step 2: fetch per-minute detail
    print(f"\n[2] Fetching per-minute detail for match {match_id}...")
    detail = get_match_detail(match_id, steam_account_id)
    if detail is None:
        print("  WARNING: No detail data returned (replay may not be parsed).")
    else:
        stats = detail.get("stats") or {}
        print(f"  networthPerMinute   : {(stats.get('networthPerMinute') or [])[:5]} ...")
        print(f"  heroDamagePerMinute : {(stats.get('heroDamagePerMinute') or [])[:5]} ...")
        print(f"  lastHitsPerMinute   : {(stats.get('lastHitsPerMinute') or [])[:5]} ...")
        print(f"  killEvents count    : {len(stats.get('killEvents') or [])}")
        print(f"  assistEvents count  : {len(stats.get('assistEvents') or [])}")

    # Step 3: fetch phase benchmarks
    print(f"\n[3] Fetching phase benchmarks (hero={hero_id}/{hero_name(hero_id)}, rank={row['average_rank']}, pos={position})...")
    phase_bms = get_phase_benchmarks(
        hero_id=hero_id,
        position=position,
        average_rank=row.get("average_rank"),
        duration_min=duration_sec // 60,
    )
    for phase, bm_pair in phase_bms.items():
        for bm_type in ("hero", "position"):
            bm = bm_pair.get(bm_type)
            label = f"[{phase}/{bm_type}]"  # phase is now early_game/mid_game/late_game
            if bm:
                stats_str = "  ".join(f"{s}={bm.get(s)}" for s in ["kills", "heroDamage", "towerDamage", "cs"])
                print(f"  {label:25s} n={bm.get('matchCount')}  {stats_str}")
            else:
                print(f"  {label:25s} No data")

    # Step 4: extract phase stats
    print(f"\n[4] Phase stat extraction...")
    if detail:
        phase_data = extract_phase_stats(
            detail,
            duration_seconds=duration_sec,
            hero_id=hero_id,
            position=position,
        )
        for phase, stats_dict in phase_data.items():
            print(f"\n  [{phase}]")
            for k, v in stats_dict.items():
                if v is not None:
                    print(f"    {k:25s}: {v:.4f}" if isinstance(v, float) else f"    {k:25s}: {v}")
    else:
        print("  Skipped (no detail data).")

    # Step 5: score the match
    closeness  = game_closeness(row.to_dict())
    multiplier = benchmark_multiplier(closeness, row.get("won"))
    print(f"\n[5] Scoring...")
    print(f"  radiant_kills / dire_kills : {row.get('radiant_kills')} / {row.get('dire_kills')}")
    print(f"  game_closeness             : {closeness:.3f}  (0=stomp, 1=even)")
    print(f"  benchmark_multiplier       : {multiplier:.3f}  (>1 = harder benchmark for stomp win)")

    scores = score_match(
        match_row=row.to_dict(),
        player_detail=detail,
        phase_benchmarks=phase_bms,
    )
    print(f"\n  {'Metric':<30} {'Score':>8}")
    print(f"  {'-'*40}")
    for k, v in scores.items():
        if k == "game_closeness":
            continue
        val = f"{v:.2f}" if v is not None else "N/A"
        print(f"  {k:<30} {val:>8}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: PYTHONPATH=src python test_match.py <steam_account_id>")
        sys.exit(1)
    run(int(sys.argv[1]))
