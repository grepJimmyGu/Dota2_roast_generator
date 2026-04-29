# DEPRECATED: moved to src/dota_core/ingest/queries.py — update imports accordingly

PLAYER_RANKED_MATCHES = """
query PlayerRankedMatches($steamAccountId: Long!, $take: Int!, $skip: Int!) {
  player(steamAccountId: $steamAccountId) {
    steamAccountId
    matches(request: {
      lobbyTypeIds: [7],
      take: $take,
      skip: $skip
    }) {
      id
      didRadiantWin
      durationSeconds
      startDateTime
      averageRank
      radiantKills
      direKills
      players(steamAccountId: $steamAccountId) {
        heroId
        isRadiant
        position
        kills
        deaths
        assists
        goldPerMinute
        experiencePerMinute
        heroDamage
        heroHealing
        towerDamage
        imp
        award
      }
    }
  }
}
"""

# Per-minute stat arrays — only available via individual match queries
MATCH_DETAILED = """
query MatchDetailed($matchId: Long!, $steamAccountId: Long!) {
  match(id: $matchId) {
    id
    durationSeconds
    players(steamAccountId: $steamAccountId) {
      heroId
      position
      isRadiant
      stats {
        networthPerMinute
        heroDamagePerMinute
        healPerMinute
        towerDamagePerMinute
        lastHitsPerMinute
        deniesPerMinute
        goldPerMinute
        impPerMinute
        actionsPerMinute
        killEvents {
          time
        }
        assistEvents {
          time
        }
      }
    }
  }
}
"""

# bracketBasicIds: HERALD_GUARDIAN, CRUSADER_ARCHON, LEGEND_ANCIENT, DIVINE_IMMORTAL
# positionIds:     POSITION_1 … POSITION_5
# minTime/maxTime: in-game minutes (e.g. 0/15 for lane phase)
HERO_BENCHMARKS = """
query HeroBenchmarks(
  $heroId: Short!,
  $bracketBasicIds: [RankBracketBasicEnum],
  $positionIds: [MatchPlayerPositionType],
  $minTime: Int,
  $maxTime: Int
) {
  heroStats {
    stats(
      heroIds: [$heroId],
      bracketBasicIds: $bracketBasicIds,
      positionIds: $positionIds,
      minTime: $minTime,
      maxTime: $maxTime
    ) {
      heroId
      matchCount
      kills
      deaths
      assists
      heroDamage
      towerDamage
      cs
      dn
    }
  }
}
"""

POSITION_BENCHMARKS = """
query PositionBenchmarks(
  $bracketBasicIds: [RankBracketBasicEnum],
  $positionIds: [MatchPlayerPositionType],
  $minTime: Int,
  $maxTime: Int
) {
  heroStats {
    stats(
      bracketBasicIds: $bracketBasicIds,
      positionIds: $positionIds,
      minTime: $minTime,
      maxTime: $maxTime
    ) {
      matchCount
      kills
      deaths
      assists
      heroDamage
      towerDamage
      cs
      dn
    }
  }
}
"""

PLAYER_HERO_PERFORMANCE = """
query PlayerHeroPerformance($steamAccountId: Long!) {
  player(steamAccountId: $steamAccountId) {
    heroesPerformance(request: { lobbyTypeIds: [7] }) {
      heroId
      winCount
      matchCount
      avgKills
      avgDeaths
      avgAssists
      avgGoldPerMinute
      avgExperiencePerMinute
      imp
    }
  }
}
"""

PLAYER_INFO = """
query PlayerInfo($steamAccountId: Long!) {
  player(steamAccountId: $steamAccountId) {
    steamAccountId
    steamAccount {
      name
      avatar
    }
    matchCount
    winCount
  }
}
"""
