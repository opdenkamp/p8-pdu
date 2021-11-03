import time
from .command import *
from .const import *
from .outlet import *
from telnetlib import Telnet, NOP
import _thread as thread
from enum import Enum

class P8PDU:
    FND_NEED_MORE = -1
    FND_PROMPT_ERROR = -2
    FND_NOT_FOUND = -3

    def __init__(self, addr, callbacks=None):
        self.addr = addr
        self.callbacks = callbacks
        self._conn = None
        self.reset()
        self.connect()

    def connect(self):
        """ open a connection to the pdu and log in """
        if self._conn is not None:
            self.close()
        thread.start_new_thread(self._connect, ())

    @property
    def address(self):
        return self.addr

    @property
    def logged_in(self):
        return (self._state == P8LoginState.LOGGED_IN)

    @property
    def connected(self):
        return self.logged_in

    @property
    def voltage(self):
        return self.outlets[0].voltage

    @property
    def current(self):
        return self.outlets[0].current

    @property
    def frequency(self):
        return self.outlets[0].frequency

    @property
    def dissipation(self):
        return self.outlets[0].dissipation

    @property
    def power(self):
        return self.outlets[0].power

    def _delay_connect(self, delay=5):
        self._stop = False
        t = time.time()
        while ((time.time() - t) < delay) and (not self._stop):
            time.sleep(0.5)
        if self._stop:
            return
        self._connect()

    def _connect(self):
        #print("opening connection to {}".format(str(self.addr)))
        self._conn = Telnet(self.addr, 23)
        self._last_refresh = time.time()
        while not self._stop:
            try:
                self._read()
                if not self._stop:
                    self._check_refresh()
            except Exception:
                self._on_connection_error()
                return

    def _on_connection_error(self):
        #print("connection to {} lost".format(str(self.addr)))
        self._stop = True
        self._conn = None
        if self.callbacks is not None:
            self.callbacks.on_connection_lost(self)
        self._delay_connect()

    def reset(self):
        """ reset the connection state """
        self._buf = ""
        self._stop = False
        self._cmd = []
        self._state = P8LoginState.NOT_LOGGED_IN
        self.outlets = []
        outlet = 1
        while (outlet <= 8):
            self.outlets.append(P8PDUOutlet(self, outlet))
            outlet = outlet + 1
        self._have_details = False

    @property
    def have_details(self):
        if not self.logged_in:
            return False
        for outlet in self.outlets:
            if not outlet.have_details:
                return False
        return True

    def tx(self, msg:str):
        """ Transmit the given string + newline """
        if (self._conn is None):
            # not connected
            return False
        # write to telnet
        self._conn.write(bytearray(msg + '\r\n', 'ascii'))
        return True

    def refresh(self):
        """ send a refresh state command for all outlets """
        for outlet in self.outlets:
            outlet.tx_refresh()

    def tx_cmd_state(self):
        if (len(self._cmd) == 0):
            return P8PDUCommand.CMD_STATE_IDLE
        return self._cmd[0].state

    def on_pdu_available(self):
        """ called after logging in successfully """
        self.refresh()

    def find_prompt(self, prompt:str):
        """ check whether the given prompt is found in the rx buffer """
        if (len(self._buf) < len(prompt)):
            # not enough data in the buffer
            return self.FND_NEED_MORE
        if (self._buf.find("Access denied") >= 0) or (self._buf.find("Incorrect user name or password") >= 0):
            # we're not or no longer logged in
            return self.FND_PROMPT_ERROR
        # check whether the prompt is found
        pos = self._buf.find(prompt)
        if (pos < 0):
            # not found
            return self.FND_NOT_FOUND
        # found, return the number of bytes used
        return pos + len(prompt)

    def rx_prompt(self, prompt:str, txmsg:str, stateIfOk:P8LoginState):
        """ transmit the given response and update the state if the prompt is found """
        pos = self.find_prompt(prompt)
        if (pos >= 0):
            # prompt found, update the state
            self._state = stateIfOk
            if txmsg is not None:
                # transmit response
                self.tx(txmsg)
            # return the number of bytes used
            return pos
        if (pos == self.FND_PROMPT_ERROR):
            # error detected, reset the state
            raise Exception("login error")
            return -1
        # not found
        return 0

    def tx_next_command(self):
        """ transmit the next command in the buffer, if there is a command to transmit """
        if (self.tx_cmd_state() != P8PDUCommand.CMD_STATE_IDLE):
            # still busy with the current command
            return
        if (len(self._cmd) == 0):
            # queue is empty
            return
        # transmit the next command
        self._cmd[0].tx()

    def line_from_buf(self):
        """ get the length of the next line from the buffer and strip chars that we don't need from the start """
        # trim newlines, spaces and prompt chars at the start
        while (len(self._buf) > 0) and ((self._buf[0] == '\r') or (self._buf[0] == '\n') or (self._buf[0] == ' ') or (self._buf[0] == '>')):
            self._buf = self._buf[1:]

        p = self._buf.find('\r')
        if (p >= 0):
            return p
        return 0

    def rx_process_command(self):
        """ process received data while logged in """
        linelen = self.line_from_buf()
        if (linelen > 0):
            # check whether we've just received the hello msg from the server
            if (self._buf.find("Telnet server") >= 0):
                self.on_pdu_available()
                return linelen

            if (len(self._cmd) == 0):
                # no command was sent. just ignore this
                return linelen

            # check whether we've just received the echo for the command that we sent
            if (self._cmd[0].on_response(self._buf[0:linelen])):
                self._cmd = self._cmd[1:]
                self.tx_next_command()
        return linelen

    def rx_process(self):
        """ process received data """
        bytesTaken = 0

        # first check the login state
        if (self._state == P8LoginState.NOT_LOGGED_IN):
            bytesTaken = self.rx_prompt("Login: ", "teladmin", P8LoginState.LOGIN_SENT)
        elif (self._state == P8LoginState.LOGIN_SENT):
            bytesTaken = self.rx_prompt("teladmin", None, P8LoginState.WAITING_PWD_PROMPT)
        elif (self._state == P8LoginState.WAITING_PWD_PROMPT):
            bytesTaken = self.rx_prompt("Password: ", "telpwd", P8LoginState.PWD_SENT)
        elif (self._state == P8LoginState.PWD_SENT):
            bytesTaken = self.rx_prompt("******", None, P8LoginState.WAITING_LOGIN)
        elif (self._state == P8LoginState.WAITING_LOGIN):
            bytesTaken = self.rx_prompt("Logged in successfully", None, P8LoginState.LOGGED_IN)
            if (bytesTaken > 0):
                if self.callbacks is not None:
                    self.callbacks.on_connected(self)
        # logged in, process the data as command
        elif (self._state == P8LoginState.LOGGED_IN):
            bytesTaken = self.rx_process_command()

        # trim newlines at the end of the buffer
        while (bytesTaken < len(self._buf)) and ((self._buf[bytesTaken] == '\n') or (self._buf[bytesTaken] == '\r')):
            bytesTaken = bytesTaken + 1

        # remove the part of the buffer that we've used
        if (bytesTaken > 0):
            if not self._have_details and self.have_details:
                self._have_details = True
                if self.callbacks is not None:
                    self.callbacks.on_initialised(self)
            self._buf = self._buf[bytesTaken:]

        return bytesTaken

    def close(self):
        """ close the connection to the PDU """
        self._stop = True
        self.tx_nop()

    def tx_nop(self):
        """ transmit a NOP, to keep the connection alive """
        if (self._conn is None):
            return False
        self._conn.write(NOP)
        return True

    def tx_command(self, command, callback, param=None):
        """ add a command to transmit to the tx buffer and transmit it, if it's the only command in the buffer """
        cmd = P8PDUCommand(self, command, callback, param)
        self._cmd.append(cmd)
        self.tx_next_command()

    def _read(self):
        buf = self._conn.read_until(b'\n', 1.0)
        if len(buf) > 0:
            try:
                self._buf = self._buf + buf.decode('ascii')
            except Exception as e:
                pass
            self.rx_process()

    def _check_refresh(self):
        if ((time.time() - self._last_refresh) >= 10.0):
            self.refresh()
            self._last_refresh = time.time()

    def __str__(self):
        return "[{}]".format(self.addr)
