"""All Stratz GraphQL query strings, grouped by domain."""

# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Search queries
# ---------------------------------------------------------------------------

SEARCH_PLAYERS = """
query SearchPlayers($query: String!) {
  search(query: $query) {
    players {
      steamAccountId
      steamAccount {
        name
        avatar
      }
    }
  }
}
"""

# ---------------------------------------------------------------------------
# Match queries
# ---------------------------------------------------------------------------

# Per-minute stat arrays — only available via individual match queries
MATCH_DETAILED = """
query MatchDetailed($matchId: Long!, $steamAccountId: Long!) {
  match(id: $matchId) {
    id
    durationSeconds
    didRadiantWin
    averageRank
    radiantKills
    direKills
    players(steamAccountId: $steamAccountId) {
      heroId
      position
      isRadiant
      assists
      deaths
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

# ---------------------------------------------------------------------------
# Benchmark queries
# ---------------------------------------------------------------------------

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
