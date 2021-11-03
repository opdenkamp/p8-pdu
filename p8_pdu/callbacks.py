class P8PDUCallbacks:
    def on_connected(self, pdu):
        print("{} connected".format(str(pdu)))

    def on_connection_lost(self, pdu):
        print("{} connection lost".format(str(pdu)))

    def on_initialised(self, pdu):
        print("{} initialised".format(str(pdu)))

    def on_outlet_state_changed(self, outlet, state):
        print("{}: {}".format(str(outlet), outlet.state_str))

    def on_current_changed(self, pdu, state):
        print("{} current: {}A".format(str(pdu), state))

    def on_voltage_changed(self, pdu, state):
        print("{} voltage: {}V".format(str(pdu), state))

    def on_frequency_changed(self, pdu, state):
        print("{} frequency: {}Hz".format(str(pdu), state))

    def on_dissipation_changed(self, pdu, state):
        print("{} dissipation: {}W".format(str(pdu), state))

    def on_power_changed(self, pdu, state):
        print("{} power: {}W".format(str(pdu), state))

    def on_power_factor_changed(self, pdu, state):
        print("{} power factor: {}".format(str(pdu), state))
