### Pulse-Eight PDU Devices ###

from .const import *
from .switch import PDUOutlet

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import DEFAULT_SCAN_INTERVAL
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.helpers.typing import (
    HomeAssistantType,
    ConfigType
)
import logging
import p8_pdu as pdu
from datetime import datetime

from typing import Sequence, TypeVar, Union
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")  # pylint: disable=invalid-name

# This version of ensure_list interprets an empty dict as no value
def ensure_list(value: Union[T, Sequence[T]]) -> Sequence[T]:
    """Wrap value in list if it is not one."""
    if value is None or (isinstance(value, dict) and not value):
        return []
    return value if isinstance(value, list) else [value]

# schema for configuration.yaml entries
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            ensure_list,
            [
                vol.Schema(
                    {
                        # address is required, name is optional
                        vol.Required(CONF_ADDRESS): cv.string,
                        vol.Optional(CONF_NAME): cv.string,
                    }
                )
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistantType, config: ConfigEntry) -> bool:
    ''' set up the p8_pdu integration '''

    if (DOMAIN not in config) or (DOMAIN in hass.data):
        return False

    def _pdu_start_listening(hass: HomeAssistantType):
        ''' create a new task to listen for p8_pdu updates '''

        class Callbacks(pdu.P8PDUCallbacks):        
            def on_initialised(self, pdu):
                _LOGGER.debug("on_initialised: {}".format(str(pdu)))
                dispatcher_send(hass, SIGNAL_PDU_REGISTERED, pdu)
                # notify the config flow, so new devices can be configured
                hass.async_create_task(
                    hass.config_entries.flow.async_init(
                        DOMAIN, context={"source": DOMAIN}, data=pdu
                    )
                )

            def on_outlet_state_changed(self, outlet, state):
                dispatcher_send(hass, SIGNAL_PDU_UPDATE, outlet, state)

            def on_current_changed(self, pdu, state):
                dispatcher_send(hass, SIGNAL_PDU_CURRENT_UPDATE, pdu, state)

            def on_voltage_changed(self, pdu, state):
                dispatcher_send(hass, SIGNAL_PDU_VOLTAGE_UPDATE, pdu, state)

            def on_frequency_changed(self, pdu, state):
                dispatcher_send(hass, SIGNAL_PDU_FREQUENCY_UPDATE, pdu, state)

            def on_power_changed(self, pdu, state):
                dispatcher_send(hass, SIGNAL_PDU_POWER_UPDATE, pdu, state)

            def on_dissipation_changed(self, pdu, state):
                dispatcher_send(hass, SIGNAL_PDU_DISSIPATION_UPDATE, pdu, state)

        p = pdu.P8PDUManager(Callbacks())
        hass.async_create_task(p.start_async())
        return p

    hass.data[DOMAIN] = {
        'manager': _pdu_start_listening(hass),
        'devices': {},
        'config': config[DOMAIN],
    }

    if not hass.config_entries.async_entries(DOMAIN):
        # import devices that are defined in configuration.yaml
        for entry in config[DOMAIN]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": config_entries.SOURCE_IMPORT},
                    data={
                        "address": entry["address"],
                        "name": entry["name"],
                    },
                )
            )

    return True

async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    ''' set up a device that has been configured by the user '''
    if entry.unique_id is None:
        raise Exception("no unique id set up: %")
        entry.unique_id = entry.data[CONF_ADDRESS]

    platform = EntityPlatform(
        hass=hass,
        logger=_LOGGER,
        domain=DOMAIN,
        platform_name=DOMAIN,
        platform=None,
        scan_interval=DEFAULT_SCAN_INTERVAL,
        entity_namespace=None,
    )
    platform.config_entry = entry

    mp = PDU(hass, hass.data[DOMAIN]['manager'], str(entry.unique_id), platform, entry.data['name'])
    hass.data[DOMAIN]['devices'][entry.unique_id] = {
        'device': mp,
        'outlets': {}
    }
    _LOGGER.debug("add pdu entity {}".format(str(entry.unique_id)))
    await platform.async_add_entities([mp])

    # forward to switch
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, SWITCH_DOMAIN))

    return True

class PDU(Entity):
    ''' pulse-eight PDU '''

    def __init__(self, hass, manager, address, platform, name=None):
        self.hass = hass
        self.address = address
        self.manager = manager
        self._platform = platform
        self._dev = None # set when p8_pdu detects this device
        self._outlets = {}
        self._primary = None
        self._added = False
        self._sw_registered = False
        self._name = name if name is not None else serial
        self._add_entities = None
        self._outlets_registered = False
        self._switch_ready = False
        async_dispatcher_connect(hass, SIGNAL_PDU_REGISTERED, self._pdu_registered)
        async_dispatcher_connect(hass, SIGNAL_PDU_CURRENT_UPDATE, self._pdu_update)
        async_dispatcher_connect(hass, SIGNAL_PDU_VOLTAGE_UPDATE, self._pdu_update)
        async_dispatcher_connect(hass, SIGNAL_PDU_FREQUENCY_UPDATE, self._pdu_update)
        async_dispatcher_connect(hass, SIGNAL_PDU_POWER_UPDATE, self._pdu_update)
        async_dispatcher_connect(hass, SIGNAL_PDU_DISSIPATION_UPDATE, self._pdu_update)
        async_dispatcher_connect(hass, SIGNAL_SWITCH_READY, self._sig_switch_ready)

        _LOGGER.debug("pdu entity created for {}".format(str(self.address)))

    @property
    def dev(self):
        ''' mx_remote device instance for this device '''
        if self._dev is None:
            self._dev = self.manager.get_by_address(self.address)
        return self._dev

    @property
    def should_poll(self):
        return False

    @property
    def available(self):
        return (self.dev is not None) and self.dev.logged_in

    async def async_added_to_hass(self) -> None:
        self._added = True
        await self._pdu_register_outlets()

    async def pdu_register_outlets(self):
        await self._pdu_register_outlets()

    async def _pdu_register_outlets(self):
        ''' register the outlets of this device as new switch devices '''
        if self.dev is None or not self._added or not self._sw_registered:
            return False

        if self._outlets_registered:
            return True

        if len(self.dev.outlets) == 0:
            return False

        if not self._switch_ready:
            return False

        for outlet in self.dev.outlets:
            if (not outlet.name in self._outlets.keys()):
                # only register outlets that we don't know
                no = PDUOutlet(self.hass, outlet)
                self._outlets[outlet.name] = no
                if self._primary is None:
                    self._primary = no
                self.hass.data[DOMAIN]['devices'][self.dev.address]['outlets'][outlet.name] = no
                dispatcher_send(self.hass, "pdu_new_outlet", no)
                _LOGGER.debug("new outlet: {}".format(str(outlet)))
        self._outlets_registered = True

    async def _pdu_registered(self, pdu):
        _LOGGER.debug("pdu_registered {}".format(str(pdu)))
        self._sw_registered = True
        await self._pdu_register_outlets()
        self.async_write_ha_state()

    async def _sig_switch_ready(self):
        self._switch_ready = True
        if self._sw_registered:
            await self._pdu_register_outlets()

    async def _pdu_update(self, dev, state):
        if isinstance(dev, str):
            if (dev != self.address):
                return
        elif (dev.address == self.address):
            self._dev = dev
        else:
            return
        if self._added:
            await self._pdu_register_outlets()
            self.async_write_ha_state()

    @property
    def name(self):
        return self._name

    @property
    def device_state_attributes(self):
        data = {}
        data['address'] = self.address
        dev = self.dev
        if dev is not None:
            data['current'] = dev.current
            data['voltage'] = dev.voltage
            data['power'] = dev.power
            data['dissipation'] = dev.dissipation
            data['frequency'] = dev.frequency
        return data

    @property
    def device_info(self):
        info = {
            'identifiers': {
                ("p8_pdu", self.address)
             },
            'name': self.name,
            'manufacturer': 'Pulse-Eight',
        }
        #dev = self.dev
        #if dev is not None:
        #    info['sw_version'] = dev.version
        #    info['model'] = dev.name
        return info

    @property
    def unique_id(self):
        return self.address

    @property
    def state(self):
        if (self.dev is None) or (self.dev.outlets is None):
            return STATE_UNKNOWN
        for outlet in self.dev.outlets:
            if outlet.powered_on:
                return STATE_ON
        return STATE_OFF

    @property
    def supported_features(self):
        return ()

