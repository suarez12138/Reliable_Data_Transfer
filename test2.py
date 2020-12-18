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
        self._send_to = None
        self._recv_from = None
        self.debug = debug
        self.seq = 0
        self.seq_ack = 0
        self.buffer_size = 2048
        self.address = None
        self.identity = None
        # 121822 新增一个收的buffer
        # ack_list 收包进程
        self.ack_list = []
        self.ack_list_size = 100
        self.receive_buffer = []
        self.receive_buffer_size = 1000

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
        conn.set_recv_from(super().recvfrom)
        conn.set_send_to(self.sendto)
        conn.set_identity(0)

        data, addr = conn._recv_from(conn.buffer_size)
        conn.set_address(addr)
        syn_packet = conn.reception(data)

        if syn_packet.test_the_packet(SYN=1):
            conn.set_number_receive(syn_packet)
            ##send syn,ack
            syn_ack_packet = Packet(SYN=1, ACK=1, SEQ_ACK=conn.seq_ack, SEQ=conn.seq)
            conn.transmission(syn_ack_packet, addr)

            # receive ack
            data2, addr2 = conn._recv_from(conn.buffer_size)
            ack_packet = conn.reception(data2)
            ##need to judge
            if ack_packet.test_the_packet(ACK=1):
                conn.set_number_receive(ack_packet)
                if self.debug:
                    print('开启 Port:' + str(addr2[1]) + ' 的连接')
            else:
                pass
            # need to be modified

        return conn, addr

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        self.set_send_to(self.sendto)
        self.set_recv_from(super().recvfrom)
        self.set_identity(1)
        self.set_address(address)

        ##send syn
        syn_packet = Packet(SYN=1)
        # while True:
        self.transmission(syn_packet, address)

        # receive syn ack
        data, addr = self._recv_from(self.buffer_size)
        syn_ack_packet = self.reception(data)
        # need to add time out situation

        if syn_ack_packet.test_the_packet(SYN=1, ACK=1):
            self.set_number_receive(syn_ack_packet)
            # send ack
            ack_packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            self.transmission(ack_packet, self.address)
        else:
            pass
            # when the packet is wrong

    # return payload(in byte)
    # def recv(self, bufsize: int) -> bytes:
    #     """
    #     Receive data from the socket.
    #     The return value is a bytes object representing the data received.
    #     The maximum amount of data to be received at once is specified by bufsize.
    #
    #     Note that ONLY data send by the peer should be accepted.
    #     In other words, if someone else sends data to you from another address,
    #     it MUST NOT affect the data returned by this function.
    #     """
    #     # data = None
    #     # assert self._recv_from, "Connection not established yet. Use recvfrom instead."
    #     # receive fin
    #     while True:
    #         packet = self.reception(self._recv_from(bufsize)[0])
    #         data = packet.PAYLOAD
    #
    #         # When closing
    #         if packet.test_the_packet():
    #             self.set_number_receive(packet)
    #             if packet.test_the_packet(FIN=1, ACK=1):
    #                 break
    #             elif packet.test_the_packet(ACK=1):
    #                 ack_packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
    #                 self.transmission(ack_packet, self.address)
    #                 self.set_number_send(ack_packet)
    #                 break
    #             else:
    #                 continue
    #     return data
    # 121822:
    def recv_many(self):
        while True:
            packet_bytes, addr = self._recv_from(self.buffer_size)
            if len(self.ack_list) < self.ack_list_size:
                self.ack_list.append((packet_bytes, addr))

    def recv(self, bufsize: int) -> bytes:
        """
        Receive data from the socket.
        The return value is a bytes object representing the data received.
        The maximum amount of data to be received at once is specified by bufsize.

        Note that ONLY data send by the peer should be accepted.
        In other words, if someone else sends data to you from another address,
        it MUST NOT affect the data returned by this function.
        """
        # 思路：
        # data = None
        # assert self._recv_from, "Connection not established yet. Use recvfrom instead."
        # receive fin
        # 代码参考：
        # while True:
        #     packet = self.reception(self._recv_from(bufsize)[0])
        #     data = packet.PAYLOAD
        #
        #     # When closing
        #     if packet.test_the_packet():
        #         self.set_number_receive(packet)
        #         if packet.test_the_packet(FIN=1, ACK=1):
        #             break
        #         elif packet.test_the_packet(ACK=1):
        #             ack_packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
        #             self.transmission(ack_packet, self.address)
        #             self.set_number_send(ack_packet)
        #             break
        #         else:
        #             continue
        # return data
        # 思路：
        data = b''  # 存储payload
        flag_fin = 0  # 设置 FIN 的 flag
        #      1.开一个进程收包
        recv = threading.Thread(target=self.recv_many)
        recv.start()
        #    while:
        packet_send = Packet(SEQ_ACK=self.seq_ack, SEQ=self.seq)  # 预先创建一个发包
        while 1:
            # 2. 从list里拿一个收到的包
            if len(self.ack_list) == 0:
                continue
            packet_bytes, addr = self.ack_list[0]
            del self.ack_list[0]
            packet = Packet.from_bytes(packet_bytes)
            #           3. 检查addr是不是自己的
            if addr != self.address:
                continue
            #           4. 检查checksum是不是一个好包
            if packet.CHECKSUM != Packet.checksum(packet_bytes):
                continue
            # debug model:
            self.reception(packet_bytes)
            #           6. 检查是不是fin
            if packet.test_the_packet(FIN=1):
                flag_fin = 1
                self.set_number_receive(packet)
                packet_send = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
                self.transmission(packet_send, self.address)
                #                                                因为 ACK = 1
                packet_send = Packet(FIN=1, ACK=1, SEQ=self.seq + 1, SEQ_ACK=self.seq_ack)
                self.transmission(packet_send, self.address)
            elif flag_fin == 1 and packet.test_the_packet(ACK=1):
                return data
            else:
                #           7. 如果来的seq = 我的ack： 返回ack = seq+len, data
                if packet.SEQ == self.seq_ack:
                    self.seq_ack += packet.LEN
                    data += packet.PAYLOAD
                    # 检查 buffer ， 看是否可以连上
                    data, self.seq_ack = self.check_receive_buffer(data)
                    # 返回包
                    packet_send = Packet(SEQ_ACK=self.seq_ack, SEQ=self.seq)
                    self.transmission(packet_send, self.address)
                #           8. 如果来的seq > 我的ack：
                #           如果可以就将包存在buffer里，返回我本来的ack
                elif packet.SEQ > self.seq_ack:
                    if len(self.receive_buffer) < self.receive_buffer_size:
                        self.receive_buffer.append(packet)
                    self.transmission(packet_send, self.address)

    def check_receive_buffer(self, data):
        flag = 1
        while flag:
            flag = 0
            for packet in self.receive_buffer:
                if self.seq_ack == packet.SEQ:  # 找到了一个可以接上的包，一系列操作，继续循环
                    self.seq_ack += packet.LEN
                    data += packet.PAYLOAD
                    flag = 1
                if packet.SEQ <= self.seq_ack:  # 过时的包， 删掉
                    self.receive_buffer.remove(packet)
        return data, self.seq_ack

    # 122822 完结

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
                ack_packet = self.reception(self._recv_from(self.buffer_size)[0])
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
                ack_packet1 = self.reception(self._recv_from(self.buffer_size)[0])
                # judge the packet
                if ack_packet1.test_the_packet(ACK=1):
                    self.set_number_receive(ack_packet1)
                    # receive fin
                    while True:
                        fin_packet2 = self.reception(self._recv_from(self.buffer_size)[0])
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
            re = self._recv_from(self.buffer_size)
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

    def set_send_to(self, send_to):
        self._send_to = send_to

    def set_recv_from(self, recv_from):
        self._recv_from = recv_from

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
        self._send_to(packet.to_bytes(), addr)
        if self.debug:
            print('Send:', packet)

    def reception(self, addr):
        packet = Packet.from_bytes(addr)
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


def checksum(payload):
    sum = 0
    for byte in payload:
        sum += byte
    sum = -(sum % 256)
    return sum & 0xff


class Queue:

    def __init__(self):
        self.items = []

    def push(self, value):
        self.items.append(value)

    def pop(self):
        self.items.pop(0)
