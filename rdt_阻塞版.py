import math

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
        # self._send_to = None
        # self._recv_from = None
        self.debug = debug
        self.seq = 0
        self.seq_ack = 0
        self.buffer_size = 2048
        self.address = None
        self.identity = None

    def accept(self) -> ('RDTSocket', (str, int)):
        """
        Accept a connection. The socket must be bound to an address and listening for
        connections. The return value is a pair (conn, address) where conn is a new
        socket object usable to send and receive data on the connection, and address
        is the address bound to the socket on the other end of the connection.

        This function should be blocking.
        """
        conn, addr = RDTSocket(self._rate), None
        ##receive syn
        # conn.set_recv_from(super().recvfrom)
        # conn.set_send_to(self.sendto)
        # conn.set_send_to(conn.sendto)
        conn.set_identity(0)
        # use port 6666 to receive first SYN
        data, addr = self.recvfrom(conn.buffer_size)
        syn_packet = self.reception(data)

        if syn_packet.test_the_packet(SYN=1):
            conn.set_number_receive(syn_packet)
            ##send syn,ack
            syn_ack_packet = Packet(SYN=1, ACK=1, SEQ_ACK=conn.seq_ack, SEQ=conn.seq)
            # use conn to transfer syn_ack_packet and it will be allot a new port, then always use conn but not server
            # server just need to receive the first SYN for each client
            conn.transmission(syn_ack_packet, addr)

            # receive ack
            data2, addr2 = conn.recvfrom(conn.buffer_size)
            ack_packet = conn.reception(data2)
            ##need to judge
            if ack_packet.test_the_packet(ACK=1):
                conn.set_number_receive(ack_packet)
                if self.debug:
                    print('开启 Port:' + str(addr2[1]) + ' 的连接')
            else:
                pass
            # need to be modified
        conn.set_address(addr)

        return conn, addr

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        # self.set_send_to(self.sendto)
        # self.set_recv_from(super().recvfrom)
        self.set_identity(1)

        ##send syn
        syn_packet = Packet(SYN=1)
        # while True:
        self.transmission(syn_packet, address)

        # receive syn ack
        data, addr = self.recvfrom(self.buffer_size)
        syn_ack_packet = self.reception(data)
        # need to add time out situation

        if syn_ack_packet.test_the_packet(SYN=1, ACK=1):
            self.set_number_receive(syn_ack_packet)
            # send ack
            ack_packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            self.transmission(ack_packet, addr)
        else:
            pass
            # when the packet is wrong

        # set address after three times handshake
        self.set_address(addr)

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
        # receive fin
        while True:
            packet = self.reception(self.recvfrom(bufsize)[0])
            data = packet.PAYLOAD

            # When closing
            if packet.test_the_packet():
                self.set_number_receive(packet)
                if packet.test_the_packet(FIN=1, ACK=1):
                    break
                elif packet.test_the_packet(ACK=1):
                    ack_packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
                    self.transmission(ack_packet, self.address)
                    self.set_number_send(ack_packet)
                    break
                else:
                    continue
        return data

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        # assert self._send_to, "Connection not established yet. Use sendto instead."
        message_list = cut_the_message(self.buffer_size, bytes)
        for i in range(len(message_list)):
            while True:
                packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack, data=message_list[i])
                self.set_number_send(packet)
                self.transmission(packet, self.address)
                ack_packet = self.reception(self.recvfrom(self.buffer_size)[0])
                if ack_packet.test_the_packet(ACK=1):
                    self.set_number_receive(ack_packet)
                    break
                else:
                    continue

        # need to be modified

    def close(self):
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither futher sends nor receives are allowed.
        """

        # send fin
        if self.identity:
            fin_packet = Packet(ACK=1, FIN=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            self.transmission(fin_packet, self.address)

            # receive ack
            while True:
                ack_packet1 = self.reception(self.recvfrom(self.buffer_size)[0])
                # judge the packet
                if ack_packet1.test_the_packet(ACK=1):
                    self.set_number_receive(ack_packet1)
                    # receive fin
                    while True:
                        fin_packet2 = self.reception(self.recvfrom(self.buffer_size)[0])
                        # judge the packet
                        if fin_packet2.test_the_packet(FIN=1):
                            self.set_number_receive(fin_packet2)
                            # send ack
                            ack_packet2 = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
                            self.transmission(ack_packet2, self.address)
                            break
                        else:
                            continue
                    break
                else:
                    continue
        else:
            # send ack
            ack_packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            self.transmission(ack_packet, self.address)
            # send fin,ack
            fin_ack_packet = Packet(ACK=1, FIN=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            self.transmission(fin_ack_packet, self.address)
            # receive ack
            re = self.recvfrom(self.buffer_size)
            packet = Packet.from_bytes(re[0])
            if self.debug:
                print('Receive:', packet)
            data = packet.PAYLOAD
            if packet.test_the_packet(ACK=1):
                self.set_number_receive(packet)
                if self.debug:
                    print('关闭 Port:' + str(re[1][1]) + ' 的连接')
            else:
                pass

        super().close()

    # def set_send_to(self, send_to):
    #     self._send_to = send_to
    #
    # def set_recv_from(self, recv_from):
    #     self._recv_from = recv_from

    def set_address(self, address):
        self.address = address

    def set_buffer_size(self, bufsize):
        self.buffer_size = bufsize

    def set_number_receive(self, packet: Packet):
        self.seq = packet.SEQ_ACK
        self.seq_ack += packet.LEN + packet.FIN + packet.SYN

    def set_number_send(self, packet: Packet):
        self.seq += packet.LEN

    def set_identity(self, id: int):
        self.identity = id

    def transmission(self, packet, addr):
        self.sendto(packet.to_bytes(), addr)
        if self.debug:
            print('Send:', packet)

    def reception(self, data):
        packet = Packet.from_bytes(data)
        if self.debug:
            print('Receive:', packet)
        return packet


def cut_the_message(buffer_size=2048, message=b''):
    pointer = 0
    message_in_part = []
    buffer_size -= 48
    length = math.floor(len(message) / buffer_size)
    for i in range(length):
        message_in_part.append(message[pointer:pointer + buffer_size])
        pointer += buffer_size
    message_in_part.append(message[pointer:])
    return message_in_part


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


# def checksum(payload):
#     sum = 0
#     for byte in payload:
#         sum += byte
#     sum = -(sum % 256)
#     return sum & 0xff


class Queue:

    def __init__(self):
        self.items = []

    def push(self, value):
        self.items.append(value)

    def pop(self):
        self.items.pop(0)
