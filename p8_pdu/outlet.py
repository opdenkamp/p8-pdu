from .async_wrap import async_wrap

class P8PDUOutlet:
    """ One outlet of a PDU """

    def __init__(self, pdu, outlet):
        self._pdu = pdu
        self._outlet = outlet
        self._state = None
        self._current = None
        self._volt = None
        self._freq = None
        self._power = None
        self._dissipation = None

    @property
    def pdu(self):
        return self._pdu

    @property
    def outlet(self):
        return self._outlet

    @property
    def connected(self):
        return self.pdu.connected

    @property
    def address(self):
        return self.pdu.address

    @property
    def name(self):
        return "{} outlet {}".format(str(self.pdu.address), str(self.outlet))

    @property
    def state(self):
        return self._state

    @property
    def powered_on(self):
        return self.state

    @state.setter
    def state(self, val):
        if (val == 'on') or (val):
            self.on()
        elif (val == 'off') or (not val):
            self.off()

    @property
    def state_str(self):
        if self.state is None:
            return "unknown"
        return "on" if self.state else "off"

    @property
    def current(self):
        return self._current

    @property
    def voltage(self):
        return self._volt

    @property
    def frequency(self):
        return self._freq

    @property
    def dissipation(self):
        return self._dissipation

    @property
    def power(self):
        return self._power

    @property
    def have_details(self):
        if (self.state is None):
            return False
        if (self.outlet != 1):
            return True
        return ((self.current is not None) and (self.voltage is not None) and (self.frequency is not None) and
                (self.power is not None) and (self.dissipation is not None))

    def on(self):
        self.pdu.tx_command("sw o0{} on imme".format(str(self.outlet)), self._on_cmd_exec, 'on')

    @async_wrap
    def async_on(self):
        return self.on()

    def off(self):
        self.pdu.tx_command("sw o0{} off imme".format(str(self.outlet)), self._on_cmd_exec, 'off')

    @async_wrap
    def async_off(self):
        return self.off()

    def tx_refresh_state(self):
        self.pdu.tx_command("read status o0{} simple".format(str(self.outlet)), self._on_refresh_state)

    def tx_refresh(self):
        """ transmit a refresh outlet state command """
        self.tx_refresh_state()
        if (self.outlet == 1):
            self.pdu.tx_command("read meter dev o0{} curr simple".format(str(self.outlet)), self._on_refresh_meter, "current")
            self.pdu.tx_command("read meter dev o0{} volt simple".format(str(self.outlet)), self._on_refresh_meter, "voltage")
            self.pdu.tx_command("read meter dev o0{} pow simple".format(str(self.outlet)), self._on_refresh_meter, "power")
            self.pdu.tx_command("read meter dev o0{} freq simple".format(str(self.outlet)), self._on_refresh_meter, "frequency")
            self.pdu.tx_command("read meter dev o0{} pd simple".format(str(self.outlet)), self._on_refresh_meter, "dissipation")

    def _on_cmd_exec(self, param, state):
        #print("{} cmd exec, param={}".format(str(self), param))
        self._on_refresh_state(None, param)

    def _on_refresh_state(self, param, state):
        #print("{} refresh state, state={}".format(str(self), state))
        if (state == 'pending'):
            self.tx_refresh_state()
            return
        ns = (state == 'on')
        if (self._state is None) or (self._state != ns):
            self._state = ns
            if self.pdu.callbacks is not None:
                self.pdu.callbacks.on_outlet_state_changed(self, state)

    def _on_refresh_meter(self, param, state):
        if (param == "current"):
            if (self._current is None) or (self._current != state):
                self._current = state
                if self.pdu.callbacks is not None:
                    self.pdu.callbacks.on_current_changed(self.pdu, state)
        elif (param == "voltage"):
            if (self._volt is None) or (self._volt != state):
                self._volt = state
                if self.pdu.callbacks is not None:
                    self.pdu.callbacks.on_voltage_changed(self.pdu, state)
        elif (param == "frequency"):
            if (self._freq is None) or (self._freq != state):
                self._freq = state
                if self.pdu.callbacks is not None:
                    self.pdu.callbacks.on_frequency_changed(self.pdu, state)
        elif (param == "dissipation"):
            if (self._dissipation is None) or (self._dissipation != state):
                self._dissipation = state
                if self.pdu.callbacks is not None:
                    self.pdu.callbacks.on_dissipation_changed(self.pdu, state)
        elif (param == "power"):
            if (self._power is None) or (self._power != state):
                self._power = state
                if self.pdu.callbacks is not None:
                    self.pdu.callbacks.on_power_changed(self.pdu, state)

    def __repr__(self):
        return "[{} outlet {}]".format(str(self.pdu), str(self.outlet))
