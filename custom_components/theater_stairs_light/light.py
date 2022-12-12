"""Platform for light integration"""
from __future__ import annotations
import sys
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN

sys.path.append("custom_components/new_light")
from new_light import NewLight

light_entity = "light.theater_stairs_group"
harmony_entity = "remote.theater_harmony_hub"
# switch_action = "zigbee2mqtt/Theater Switch/action"
motion_sensor_action = "zigbee2mqtt/Theater Stairs Motion Sensor"
motion_sensor_action2 = "zigbee2mqtt/Mudroom High Motion Sensor"
dartboard_entity = "light.dart_board"
brightness_step = 43
motion_sensor_brightness = 128
has_harmony = True
has_motion_sensor = True
has_switch = False


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the light platform."""
    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return
    ent = TheaterStairsLight()
    add_entities([ent])


class TheaterStairsLight(NewLight):
    """Theater Stairs Light."""

    def __init__(self) -> None:
        """Initialize Theater Stairs Light."""
        super(TheaterStairsLight, self).__init__(
            "Theater Stairs", domain=DOMAIN, debug=False, debug_rl=False
        )

        self.motion_sensor_brightness = 128
        self.entities["light.theater_stairs_group"] = None
        self.motion_sensors.append("Theater Stairs Motion Sensor")
        self.motion_sensors.append("Mudroom High Motion Sensor")
        self.motion_disable_entities.append("remote.theater_harmony_hub")
        self.motion_disable_entities.append("light.dart_board")
