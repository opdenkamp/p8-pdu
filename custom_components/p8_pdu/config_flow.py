import logging
from typing import Any, Dict, Optional
from homeassistant import config_entries
from homeassistant.helpers import (
    config_entry_flow,
    discovery
)
from homeassistant.const import (
    CONF_NAME,
)
import p8_pdu as pdu
from .const import DOMAIN, CONF_ADDRESS

_LOGGER = logging.getLogger(__name__)

class P8PDUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        self.dev = None
        self.name = None

    async def async_step_p8_pdu(self, dev: pdu.P8PDU) -> Dict[str, Any]:
        ''' device detected by p8_pdu '''

        # serial is unique for production units
        await self.async_set_unique_id(dev.address)
        self._abort_if_unique_id_configured()

        # show new device found entry
        self.dev = dev
        self.name = 'PDU {}'.format(dev.address)
        _LOGGER.debug("config flow for pdu {}".format(str(dev)))
        self.context.update({"title_placeholders": {'address': self.dev.address}})
        return await self.async_step_user()

    async def async_step_user(self, user_input: Optional[Dict] = None) -> Dict[str, Any]:
        ''' new device found entry clicked '''

        _LOGGER.debug("step user, input = {}, dev = {}".format(str(user_input), str(self.dev)))
        if user_input is None:
            if self.dev is None:
                return self.async_abort(reason="wait_detect")
            # user didn't click accept yet
            return self.async_show_form(
                step_id = "user",
                description_placeholders = {
                    'address': self.dev.address,
                },
                errors={},
            )

        # create a new config entry
        config = {
            CONF_ADDRESS: self.dev.address,
            CONF_NAME: self.name,
        }
        return self.async_create_entry(
            title=self.name,
            data=config,
        )

    async def async_step_import(self, info):
        ''' entry imported from configuration.yaml '''

        address = info.get("address")
        name = info.get("name")
        await self.async_set_unique_id(address)
        config = {
            CONF_ADDRESS: address,
            CONF_NAME: name,
        }
        self._abort_if_unique_id_configured(
            updates=config,
        )
        return self.async_create_entry(
            title="{} (import from configuration.yaml)".format(address),
            data=config,
        )


