from core.lib.db import GearTier

GEAR_CONVERTER: dict[GearTier, int] = {
    GearTier.common: 10,
    GearTier.rare: 25,
    GearTier.legendary: 60,
    GearTier.prismatic_i: 150,
    GearTier.prismatic_ii: 350,
    GearTier.prismatic_iii: 800,
}