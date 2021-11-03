import p8_pdu
import logging
import time

logging.basicConfig(level=logging.DEBUG)

class PDUTest(p8_pdu.P8PDUCallbacks):
    def __init__(self):
        self.pduman = p8_pdu.P8PDUManager(self)

    def test(self):
        self.pduman.start()
        t = time.time()
        v = True
        while True:
            time.sleep(0.5)
            if (time.time() - t) >= 10:
                v = not v
                for _, pdu in self.pduman.DEVICES.items():
                    pdu.outlets[6].state = v
                t = time.time()

PDUTest().test()
