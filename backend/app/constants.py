SKILL_FIELDS = [
    "form", "stamina", "speed", "goalkeeper", "defending", "playmaking",
    "winger", "passing", "scoring", "set_pieces", "leadership", "experience", "loyalty",
]

# Subset tracked by CHPP sync (no speed / leadership / experience / loyalty).
CHPP_SKILL_FIELDS = [
    "form", "stamina", "goalkeeper", "defending", "playmaking",
    "winger", "passing", "scoring", "set_pieces",
]

# Fields comparable across CHPP and HRF snapshots (intersection of the two sets above).
MIXED_SOURCE_FIELDS = [f for f in SKILL_FIELDS if f in frozenset(CHPP_SKILL_FIELDS)]
