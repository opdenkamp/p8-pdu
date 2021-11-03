""" Support for Pulse-Eight PDU """
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
import logging
from .const import *
from homeassistant.helpers.typing import (
    HomeAssistantType,
    ConfigType
)

_LOGGER = logging.getLogger(__name__)
#_LOGGER.setLevel(logging.DEBUG)

async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry, async_add_entities) -> bool:
    @callback
    def async_add_pdu_outlet(outlet):
        _LOGGER.debug("register outlet {} - {} = {}".format(outlet.name, outlet.outlet.pdu.address, entry.unique_id))
        if outlet.outlet.pdu.address == entry.unique_id:
            async_add_entities([outlet])
    async_dispatcher_connect(hass, "pdu_new_outlet", async_add_pdu_outlet)
    dispatcher_send(hass, SIGNAL_SWITCH_READY)
    return True

class PDUOutlet(SwitchEntity):
    def __init__(self, hass, outlet):
        self.hass = hass
        self.outlet = outlet
        async_dispatcher_connect(hass, SIGNAL_PDU_UPDATE, self._outlet_update)
        async_dispatcher_connect(hass, SIGNAL_PDU_VOLTAGE_UPDATE, self._pdu_update)
        async_dispatcher_connect(hass, SIGNAL_PDU_FREQUENCY_UPDATE, self._pdu_update)

    @property
    def should_poll(self):
        return False

    @property
    def available(self):
        return self.outlet.connected

    @property
    def voltage(self):
        return self.outlet.pdu.voltage

    @property
    def frequency(self):
        return self.outlet.pdu.frequency

    @property
    def name(self):
        return 'PDU {} outlet {}'.format(self.outlet.pdu.address, self.outlet.outlet)

    @property
    def device_state_attributes(self):
        return {
            'voltage': self.voltage,
            'frequency': self.frequency,
            'outlet': self.outlet.outlet
        }

    @property
    def device_info(self):
        return {
            'identifiers': {
                ("p8_pdu", self.outlet.pdu.address, 'outlet', self.outlet.outlet)
             },
            'name': self.name,
            'manufacturer': 'Pulse-Eight',
            'via_device': (DOMAIN, self.outlet.pdu.address),
        }

    @property
    def unique_id(self):
        return self.name

    @property
    def is_on(self):
        return self.outlet.powered_on

    async def async_turn_on(self, **kwargs):
        await self.outlet.async_on()

    async def async_turn_off(self, **kwargs):
        await self.outlet.async_off()

    async def _outlet_update(self, outlet, state):
        if (self.entity_id is not None) and (self.outlet == outlet):
            self.async_write_ha_state()

    async def _pdu_update(self, pdu, state):
        if (self.entity_id is not None) and (self.outlet.pdu == pdu):
            self.async_write_ha_state()

