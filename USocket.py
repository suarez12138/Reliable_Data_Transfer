from socket import socket, AF_INET, SOCK_DGRAM, inet_aton, inet_ntoa
import time

sockets = {}
network = ('127.0.0.1', 6666)

#byte转地址（元组）
def bytes_to_addr(bytes):
    return inet_ntoa(bytes[:4]), int.from_bytes(bytes[4:8], 'big')

#地址转byte格式
def addr_to_bytes(addr):
    return inet_aton(addr[0]) + addr[1].to_bytes(4, 'big')

#获得send to函数，调速，在sendto 里发送
def get_sendto(id, rate=None):
    if rate:
        def sendto(data: bytes, addr):
            time.sleep(len(data) / rate)
            sockets[id].sendto(addr_to_bytes(addr) + data, network)

        return sendto
    else:
        def sendto(data: bytes, addr):
            sockets[id].sendto(addr_to_bytes(addr) + data, network)

        return sendto


class UnreliableSocket:
    def __init__(self, rate=None):
        assert rate == None or rate > 0, 'Rate should be positive or None.'
        sockets[id(self)] = socket(AF_INET, SOCK_DGRAM)
        self.sendto = get_sendto(id(self), rate)
#绑定
    def bind(self, address: (str, int)):
        sockets[id(self)].bind(address)
#收消息，收到来自正确网络的则返回data8位起的后面＋前八位转成地址（一个元组：前四位是ip地址，后四位是port）
    def recvfrom(self, bufsize) -> bytes:
        data, frm = sockets[id(self)].recvfrom(bufsize)
        addr = bytes_to_addr(data[:8])

        # if frm == network:
        return data[8:], addr
        # else:
        #     return self.recvfrom(bufsize)


    def settimeout(self, value):
        sockets[id(self)].settimeout(value)
#获得time out时长
    def gettimeout(self):
        return sockets[id(self)].gettimeout()

    def setblocking(self, flag):
        sockets[id(self)].setblocking(flag)

    def getblocking(self):
        sockets[id(self)].getblocking()
#获取地址
    def getsockname(self):
        return sockets[id(self)].getsockname()

    def close(self):
        sockets[id(self)].close()
