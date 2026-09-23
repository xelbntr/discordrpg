from enum import IntEnum
from core.lib.db import GearTier


class GearConverter(IntEnum):
    GearTier.common = 10
    GearTier.rare = 25
    GearTier.legendary = 60
    GearTier.prismatic_i = 150
    GearTier.prismatic_ii = 350
    GearTier.prismatic_iii = 800

