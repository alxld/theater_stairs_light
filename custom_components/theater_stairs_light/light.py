"""Platform for light integration"""
from __future__ import annotations
import logging, json, sys

# from enum import Enum
# import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers import event
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_FLASH,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_MAX_MIREDS,
    ATTR_MIN_MIREDS,
    ATTR_TRANSITION,
    # ATTR_WHITE_VALUE,
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    SUPPORT_EFFECT,
    SUPPORT_FLASH,
    SUPPORT_TRANSITION,
    # SUPPORT_WHITE_VALUE,
    LightEntity,
    ATTR_COLOR_MODE,
    ATTR_SUPPORTED_COLOR_MODES,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_OFFSET,
    CONF_UNIQUE_ID,
    EVENT_HOMEASSISTANT_START,
    STATE_ON,
    STATE_UNAVAILABLE,
)

sys.path.append("custom_components/right_light")
from right_light import RightLight

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

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

    @callback
    async def switch_message_received(topic: str, payload: str, qos: int) -> None:
        """A new MQTT message has been received."""
        await ent.switch_message_received(topic, payload, qos)

    @callback
    async def motion_sensor_message_received(
        topic: str, payload: str, qos: int
    ) -> None:
        """A new motion sensor MQTT message has been received"""
        await ent.motion_sensor_message_received(topic, json.loads(payload), qos)

    @callback
    async def motion_sensor_message_received2(
        topic: str, payload: str, qos: int
    ) -> None:
        """A new motion sensor MQTT message has been received"""
        await ent.motion_sensor_message_received2(topic, json.loads(payload), qos)

    if has_switch:
        await hass.components.mqtt.async_subscribe(
            switch_action, switch_message_received
        )
    if has_motion_sensor:
        await hass.components.mqtt.async_subscribe(
            motion_sensor_action, motion_sensor_message_received
        )
        await hass.components.mqtt.async_subscribe(
            motion_sensor_action2, motion_sensor_message_received2
        )


class TheaterStairsLight(LightEntity):
    """Theater Stairs Light."""

    def __init__(self) -> None:
        """Initialize Theater Stairs Light."""
        self._light = light_entity
        self._name = "Theater Stairs"
        # self._state = 'off'
        self._brightness = 0
        self._brightness_override = 0
        self._hs_color: Optional[Tuple[float, float]] = None
        self._color_temp: Optional[int] = None
        self._rgb_color: Optional[Tuple[int, int, int]] = None
        self._min_mireds: int = 154
        self._max_mireds: int = 500
        self._mode = "Off"
        self._is_on = False
        self._available = True
        self._occupancy = False
        self._occupancy2 = False
        self.entity_id = generate_entity_id(ENTITY_ID_FORMAT, self._name, [])
        # self._white_value: Optional[int] = None
        self._effect_list: Optional[List[str]] = None
        self._effect: Optional[str] = None
        self._supported_features: int = 0
        self._supported_features |= SUPPORT_BRIGHTNESS
        self._supported_features |= SUPPORT_COLOR_TEMP
        # self._supported_features |= SUPPORT_COLOR
        self._supported_features |= SUPPORT_TRANSITION
        # self._supported_features |= SUPPORT_WHITE_VALUE

        # Record whether a switch was used to turn on this light
        self.switched_on = False

        # Track if the Harmony is on
        self.harmony_on = False

        # Track if dart board is on
        self.dartboard_on = False

        # self.hass.states.async_set(f"light.{self._name}", "Initialized")
        _LOGGER.info(f"{self._name} Light initialized")

    async def async_added_to_hass(self) -> None:
        """Instantiate RightLight"""
        self._rightlight = RightLight(self._light, self.hass)

        #        #temp = self.hass.states.get(harmony_entity).new_state
        #        #_LOGGER.error(f"Harmony state: {temp}")
        if has_harmony:
            event.async_track_state_change_event(
                self.hass, harmony_entity, self.harmony_update
            )
        event.async_track_state_change_event(
            self.hass, dartboard_entity, self.dartboard_update
        )

        self.async_schedule_update_ha_state(force_refresh=True)

        # Not working.  Light starts up an sends None=>Off, Off=>Off, Off=>On, but not sure if that's always the case
        # event.async_track_state_change_event(self.hass, self._light, self.light_update)

    @callback
    async def harmony_update(self, this_event):
        """Track harmony updates"""
        ev = this_event.as_dict()
        ns = ev["data"]["new_state"].state
        if ns == "on":
            self.harmony_on = True
        else:
            self.harmony_on = False

    @callback
    async def dartboard_update(self, this_event):
        """Track dartboard updates"""
        ev = this_event.as_dict()
        ns = ev["data"]["new_state"].state
        if ns == "on":
            self.dartboard_on = True
        else:
            self.dartboard_on = False
        _LOGGER.error(f"{self._name} dartboard tracking: {ev} => {self.dartboard_on}")

    @property
    def should_poll(self):
        """Allows for color updates to be polled"""
        return True

    @property
    def name(self) -> str:
        """Return the display name of this light."""
        return self._name

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._is_on

    @property
    def device_info(self):
        prop = {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            "name": self._name,
            "manufacturer": "Aaron",
        }
        return prop

    @property
    def unique_id(self):
        """Return the unique id of the light."""
        return self.entity_id

    @property
    def available(self) -> bool:
        """Return whether the light group is available."""
        return self._available

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def hs_color(self) -> Optional[Tuple[float, float]]:
        """Return the hue and saturation color value [float, float]."""
        return self._hs_color

    @property
    def color_temp(self) -> Optional[int]:
        """Return the CT color value in mireds."""
        return self._color_temp

    @property
    def min_mireds(self) -> int:
        """Return the coldest color_temp that this light group supports."""
        return self._min_mireds

    @property
    def max_mireds(self) -> int:
        """Return the warmest color_temp that this light group supports."""
        return self._max_mireds

    # @property
    # def white_value(self) -> Optional[int]:
    #    """Return the white value of this light group between 0..255."""
    #    return self._white_value

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [int, int, int]."""
        return self._rgb_color

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    async def async_turn_on(self, **kwargs) -> None:
        """Instruct the light to turn on."""
        _LOGGER.error(f"{self._name} LIGHT ASYNC_TURN_ON: {kwargs}")
        if "brightness" in kwargs:
            self._brightness = kwargs["brightness"]
        elif self._brightness == 0:
            self._brightness = 255

        if "source" in kwargs and kwargs["source"] == "MotionSensor":
            pass
        else:
            self.switched_on = True

        if "source" in kwargs and kwargs["source"] == "Switch":
            # Assume RightLight mode for all switch presses
            rl = True
        elif self._is_on == False:
            # If light is off, default to RightLight mode (can be overriden with color/colortemp attributes)
            rl = True
        else:
            rl = False
        # rl = True

        #        def_br = 255 if self._brightness == 0 else self._brightness
        #        self._brightness = kwargs.get(ATTR_BRIGHTNESS, def_br)
        self._is_on = True
        self._mode = "On"
        data = {ATTR_ENTITY_ID: self._light, "transition": 0.1}

        if ATTR_HS_COLOR in kwargs:
            rl = False
            data[ATTR_HS_COLOR] = kwargs[ATTR_HS_COLOR]
        if ATTR_RGB_COLOR in kwargs:
            rl = False
            data[ATTR_RGB_COLOR] = kwargs[ATTR_RGB_COLOR]
        if ATTR_BRIGHTNESS in kwargs:
            data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]
        if ATTR_COLOR_TEMP in kwargs:
            rl = False
            data[ATTR_COLOR_TEMP] = kwargs[ATTR_COLOR_TEMP]
        if ATTR_COLOR_MODE in kwargs:
            rl = False
            data[ATTR_COLOR_MODE] = kwargs[ATTR_COLOR_MODE]
        # if ATTR_WHITE_VALUE in kwargs:
        #    rl = False
        #    data[ATTR_WHITE_VALUE] = kwargs[ATTR_WHITE_VALUE]
        if ATTR_TRANSITION in kwargs:
            data[ATTR_TRANSITION] = kwargs[ATTR_TRANSITION]

        if rl:
            await self._rightlight.turn_on(
                brightness=self._brightness,
                brightness_override=self._brightness_override,
            )
        else:
            await self._rightlight.turn_on_specific(data)

        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_turn_on_mode(self, **kwargs: Any) -> None:
        self._mode = kwargs.get("mode", "Vivid")
        self._is_on = True
        self._brightness = 255
        self.switched_on = True
        await self._rightlight.turn_on(mode=self._mode)
        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._brightness = 0
        self._brightness_override = 0
        self._is_on = False
        self.switched_on = False
        await self._rightlight.disable_and_turn_off()

        self.async_schedule_update_ha_state(force_refresh=True)

    async def up_brightness(self, **kwargs) -> None:
        """Increase brightness by one step"""
        if self._brightness == None:
            self._brightness = brightness_step
        elif self._brightness > (255 - brightness_step):
            self._brightness = 255
            self._brightness_override = self._brightness_override + brightness_step
        else:
            self._brightness = self._brightness + brightness_step

        await self.async_turn_on(brightness=self._brightness, **kwargs)

    async def down_brightness(self, **kwargs) -> None:
        """Decrease brightness by one step"""
        if self._brightness == None:
            await self.async_turn_off(**kwargs)
        elif self._brightness_override > 0:
            self._brightness_override = 0
            await self.async_turn_on(brightness=self._brightness, **kwargs)
        elif self._brightness < brightness_step:
            await self.async_turn_off(**kwargs)
        else:
            self._brightness = self._brightness - brightness_step
            await self.async_turn_on(brightness=self._brightness, **kwargs)

    async def async_update(self):
        """Query light and determine the state."""
        # _LOGGER.error(f"{self._name} LIGHT ASYNC_UPDATE")
        state = self.hass.states.get(self._light)

        if state == None:
            return

        self._hs_color = state.attributes.get(ATTR_HS_COLOR, self._hs_color)
        self._rgb_color = state.attributes.get(ATTR_RGB_COLOR, self._rgb_color)
        self._color_temp = state.attributes.get(ATTR_COLOR_TEMP, self._color_temp)
        self._min_mireds = state.attributes.get(ATTR_MIN_MIREDS, 154)
        self._max_mireds = state.attributes.get(ATTR_MAX_MIREDS, 500)
        self._effect_list = state.attributes.get(ATTR_EFFECT_LIST)

    async def switch_message_received(self, topic: str, payload: str, qos: int) -> None:
        """A new MQTT message has been received."""
        # self.hass.states.async_set(f"light.{self._name}", f"ENT: {payload}")

        self.switched_on = True
        if payload == "on-press":
            self._brightness_override = 0
            await self.async_turn_on(source="Switch", brightness=255)
        elif payload == "on-hold":
            await self.async_turn_on_mode(mode="Vivid", source="Switch")
        elif payload == "off-press":
            self.switched_on = False
            await self.async_turn_off(source="Switch")
        elif payload == "up-press":
            await self.up_brightness(source="Switch")
        elif payload == "up-hold":
            await self.async_turn_on_mode(mode="Bright", source="Switch")
        elif payload == "down-press":
            await self.down_brightness(source="Switch")
        else:
            _LOGGER.error(f"{self._name} Light Fail: {payload}")

    async def motion_sensor_message_received(
        self, topic: str, payload: str, qos: int
    ) -> None:
        """A new MQTT message has been received."""
        if self._occupancy == payload["occupancy"]:
            # No change to state
            return

        self._occupancy = payload["occupancy"]

        # Disable motion sensor tracking if the lights are switched on or the harmony is on
        if has_harmony:
            if self.switched_on or self.harmony_on or self.dartboard_on:
                return
        else:
            if self.switched_on:
                return

        if self._occupancy:
            await self.async_turn_on(
                brightness=motion_sensor_brightness, source="MotionSensor"
            )
        else:
            if not self._occupancy2:
                await self.async_turn_off()

    async def motion_sensor_message_received2(
        self, topic: str, payload: str, qos: int
    ) -> None:
        """A new MQTT message has been received."""
        if self._occupancy2 == payload["occupancy"]:
            # No change to state
            return

        self._occupancy2 = payload["occupancy"]

        # Disable motion sensor tracking if the lights are switched on or the harmony is on
        if has_harmony:
            if self.switched_on or self.harmony_on or self.dartboard_on:
                return
        else:
            if self.switched_on:
                return

        if self._occupancy2:
            await self.async_turn_on(
                brightness=motion_sensor_brightness, source="MotionSensor"
            )
        else:
            if not self._occupancy:
                await self.async_turn_off()
