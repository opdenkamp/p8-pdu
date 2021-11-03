class P8PDUCommand:
    CMD_STATE_SENT = 0
    CMD_STATE_AWAITING = 1
    CMD_STATE_IDLE = 2

    def __init__(self, pdu, cmd, callback, param=None):
        self._pdu = pdu
        self.cmd = cmd
        self.callback = callback
        self.cb_param = param
        self.state = self.CMD_STATE_IDLE

    def tx(self):
        if self.state != self.CMD_STATE_IDLE:
            raise Exception("command {} already transmitted".format(self.cmd))
        self.state = self.CMD_STATE_SENT
        self._pdu.tx(self.cmd)

    def on_response(self, resp):
        if (self.state == self.CMD_STATE_SENT):
            pos = self._pdu.find_prompt(self.cmd)
            if (pos >= 0):
                # echo received
                self.state = self.CMD_STATE_AWAITING
        elif (self.state == self.CMD_STATE_AWAITING):
            # response received
            #print("response to '{}': '{}'".format(self.cmd, resp))
            if self.callback is not None:
                self.callback(self.cb_param, resp)
            self.state = self.CMD_STATE_IDLE
            return True
        return False

