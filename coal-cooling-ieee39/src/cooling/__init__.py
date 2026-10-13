"""Coal-plant wet recirculating cold-end prototype models and scaling helpers."""

from .prototype_500mw import WetRecircPrototype500, PrototypeResult
from .scale import scale_prototype_to_unit
from .pavail import available_power_mw

__all__ = [
    "WetRecircPrototype500",
    "PrototypeResult",
    "scale_prototype_to_unit",
    "available_power_mw",
]
