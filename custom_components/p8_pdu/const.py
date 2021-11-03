from homeassistant.components.media_player.const import (
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON
)

DOMAIN = "p8_pdu"
CONF_ADDRESS = "address"
SIGNAL_PDU_REGISTERED = "pdu_registered"
SIGNAL_PDU_UPDATE = "pdu_update"
SIGNAL_PDU_CURRENT_UPDATE = "pdu_update_current"
SIGNAL_PDU_VOLTAGE_UPDATE = "pdu_update_voltage"
SIGNAL_PDU_FREQUENCY_UPDATE = "pdu_update_frequency"
SIGNAL_PDU_POWER_UPDATE = "pdu_update_power"
SIGNAL_PDU_DISSIPATION_UPDATE = "pdu_update_dissipation"
SIGNAL_SWITCH_READY = "pdu_switch_ready"

SUPPORT_P8PDU = (
      SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
)

