from .async_wrap import async_wrap
from .detect import *
from .pdu import *
import _thread as thread
import time

class P8PDUManager:
    DEVICES = {}

    def __init__(self, callbacks=None):
        self.callbacks = callbacks
        self._stop = False
        self.detect = P8PDUDetect(self.on_pdu_found)

    def _discover(self):
        t = time.time()
        while not self._stop:
            if (time.time() - t) >= 10:
                self.detect.tx_discover_all()
                t = time.time()
            time.sleep(0.5)

    def start(self):
        self._stop = False
        self.detect.tx_discover_all()
        thread.start_new_thread(self._discover, ())

    @async_wrap
    def start_async(self):
        return self.start()

    def stop(self):
        self._stop = True
        for _, dev in self.DEVICES.items():
            dev.close()
        self.DEVICES = {}

    def on_pdu_found(self, addr):
        if addr not in self.DEVICES.keys():
            self.DEVICES[addr] = P8PDU(addr, self.callbacks)

    def get_by_address(self, addr):
        return self.DEVICES[addr] if addr in self.DEVICES.keys() else None
