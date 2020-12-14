from USocket import UnreliableSocket
import threading
import time
from packet import Packet


class RDTSocket(UnreliableSocket):
    """
    The functions with which you are to build your RDT.
    -   recvfrom(bufsize)->bytes, addr
    -   sendto(bytes, address)
    -   bind(address)

    You can set the mode of the socket.
    -   settimeout(timeout)
    -   setblocking(flag)
    By default, a socket is created in the blocking mode.
    https://docs.python.org/3/library/socket.html#socket-timeouts

    """

    def __init__(self, rate=None, debug=True):
        super().__init__(rate=rate)
        self._rate = rate
        self._send_to = None
        self._recv_from = None
        self.debug = debug
        self.seq = 0
        self.seq_ack = 0
        self.buffer_size = 2048
        self.address = None

    def accept(self) -> ('RDTSocket', (str, int)):
        """
        Accept a connection. The socket must be bound to an address and listening for
        connections. The return value is a pair (conn, address) where conn is a new
        socket object usable to send and receive data on the connection, and address
        is the address bound to the socket on the other end of the connection.

        This function should be blocking.
        """
        # conn, addr = RDTSocket(self._rate), None
        ##receive syn
        self.set_recv_from(super().recvfrom)
        data, addr = self._recv_from(self.buffer_size)
        self.set_address(addr)
        syn_packet = Packet.from_bytes(data)
        ##need to judge
        self.set_seq_and_ack(syn_packet)
        print(syn_packet)

        ##send syn,ack
        self.set_send_to(self.sendto)
        if syn_packet.SYN == 1:
            syn_ack_packet = Packet(SYN=1, ACK=1, SEQ_ACK=self.seq_ack, SEQ=self.seq)
            self._send_to(syn_ack_packet.to_bytes(), addr)
            print(syn_ack_packet)

            # receive ack
            data2, addr2 = self._recv_from(self.buffer_size)
            ack_packet = Packet()
            ack_packet = ack_packet.from_bytes(data2)
            ##need to judge
            self.set_seq_and_ack(ack_packet)
            print(ack_packet)
            if ack_packet.ACK == 1:
                pass
            else:
                pass
            # need to be modified

        return self, addr

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        ##send syn
        syn_packet = Packet(SYN=1)
        self.set_send_to(self.sendto)
        # while True:
        self._send_to(syn_packet.to_bytes(), address)
        # time.sleep(0.1)
        print(syn_packet)

        # receive syn ack
        self.set_recv_from(super().recvfrom)
        data, addr = self._recv_from(self.buffer_size)
        syn_ack_packet = Packet.from_bytes(data)
        self.set_seq_and_ack(syn_ack_packet)
        self.set_address(address)
        print(syn_ack_packet)
        # need to add time out situation

        # send ack
        if syn_ack_packet.SYN == 1 and syn_ack_packet.ACK == 1:
            ack_packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            print(ack_packet)
            self._send_to(ack_packet.to_bytes(), address)
        else:
            pass
            # when the packet is wrong

    # return payload(in byte)
    def recv(self, bufsize: int) -> bytes:
        """
        Receive data from the socket.
        The return value is a bytes object representing the data received.
        The maximum amount of data to be received at once is specified by bufsize.

        Note that ONLY data send by the peer should be accepted.
        In other words, if someone else sends data to you from another address,
        it MUST NOT affect the data returned by this function.
        """
        # data = None
        # assert self._recv_from, "Connection not established yet. Use recvfrom instead."

        packet = Packet.from_bytes(self._recv_from(bufsize)[0])
        print(packet)
        data = packet.PAYLOAD
        self.set_seq_and_ack(packet)
        # When closing
        while packet.FIN:
            packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            print(packet)
            self._send_to(packet.to_bytes(), self.address)
            packet = Packet(ACK=1, FIN=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            print(packet)
            self._send_to(packet.to_bytes(), self.address)
            re = self._recv_from(bufsize)
            packet = Packet.from_bytes(re[0])
            print(packet)
            data = packet.PAYLOAD
            self.set_seq_and_ack(packet)
            if packet.ACK:
                print('关闭 Port:' + str(re[1][1]) + ' 的连接')
                break

        return data

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        # assert self._send_to, "Connection not established yet. Use sendto instead."
        packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack, data=bytes)
        print(packet)
        self._send_to(packet.to_bytes(), self.address)
        # need to be modified

    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither futher sends nor receives are allowed.
        """

        # send fin
        fin_packet = Packet(FIN=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
        print(fin_packet)
        self._send_to(fin_packet.to_bytes(), self.address)

        # receive ack
        while True:
            ack_packet1 = Packet.from_bytes(self._recv_from(self.buffer_size)[0])
            print(ack_packet1)
            # judge the packet
            if ack_packet1.ACK == 1:
                self.set_seq_and_ack(ack_packet1)
                # receive fin
                while True:
                    fin_packet2 = Packet.from_bytes(self._recv_from(self.buffer_size)[0])
                    print(fin_packet2)
                    # judge the packet
                    if fin_packet2.FIN == 1:
                        self.set_seq_and_ack(fin_packet2)
                        # send ack
                        ack_packet2 = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
                        print(ack_packet2)
                        self._send_to(ack_packet2.to_bytes(), self.address)
                        break
                    else:
                        continue
                break
            else:
                continue

        super().close()

    def set_send_to(self, send_to):
        self._send_to = send_to

    def set_recv_from(self, recv_from):
        self._recv_from = recv_from

    def set_address(self, address):
        self.address = address

    def set_buffer_size(self, bufsize):
        self.buffer_size = bufsize

    def set_seq_and_ack(self, packet: Packet):
        self.seq = packet.SEQ_ACK
        self.seq_ack += packet.LEN + packet.FIN + packet.SYN


"""
You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.

"""

"""
Reliable Data Transfer Segment

Segment Format:

|0 1 2 3 4 5 6 7 8|0 1 2 3 4 5 6 7 8|0 1 2 3 4 5 6 7 8|0 1 2 3 4 5 6 7 8| 
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           (NO USE)          |S|F|A|              CHECKSUM             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                              SEQ                                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                            SEQ ACK                                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                              LEN                                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                                       |
/                            PAYLOAD                                    /
/                                                                       /
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+


Flags:
 - S-SYN                      Synchronize
 - F-FIN                      Finish
 - A-ACK                      Acknowledge

Ranges:
 - Payload Length           0 - 2^32  (append zeros to the end if length < 1440)
 - Sequence Number          0 - 2^32
 - Acknowledgement Number   0 - 2^32
 - CHECKSUM                 0 - 2^16


Size of sender's window     16
"""


def checksum(payload):
    sum = 0
    for byte in payload:
        sum += byte
    sum = -(sum % 256)
    return sum & 0xff


if __name__ == '__main__':
    import struct

    # payload = 'akjdfakdfjsdaf'
    # o = checksum(bytes(payload.encode("UTF-8")))
    # print(o)
