import netifaces
import socket
import _thread as thread
from .const import *

class P8PDUDetect:
    """ P8 PDU detection """
    def __init__(self, callback, ip="0.0.0.0", port=UDP_PORT):
        self.callback = callback
        self.ip = ip
        self.port = port
        self._stop = False
        self.tx_magic = b'\xFF\xFF\x45\x4E\x91'
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.bind((ip, port))
        thread.start_new_thread(self._listen, ())

    def close(self):
        self._stop = True

    def _listen(self):
        while not self._stop:
            payload, addr = self.socket.recvfrom(132)
            if len(payload) == 132:
                addr, _ = addr
                self.callback(addr)

    def tx_discover(self, bcast):
        #print("discover to {}:{}".format(str(bcast), str(UDP_PORT)))
        self.socket.sendto(self.tx_magic, (bcast, UDP_PORT))

    def tx_discover_all(self):
        ifaces = [iface for iface in netifaces.interfaces() if iface != 'lo']
        for ifname in ifaces:
            addresses = netifaces.ifaddresses(ifname)
            if netifaces.AF_INET not in addresses:
                continue
            for addr in addresses[netifaces.AF_INET]:
                if 'broadcast' in addr:
                    self.tx_discover(addr['broadcast'])

