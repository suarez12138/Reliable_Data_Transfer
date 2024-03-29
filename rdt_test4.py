import ctypes
import inspect
import math
from datetime import datetime

from USocket import UnreliableSocket
import threading
import time
from packet import Packet
import functools


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
        self.time_out = 3
        self._rate = rate
        # self._send_to = None
        # self._recv_from = None
        self.debug = debug
        self.seq = 0
        self.seq_ack = 0
        self.buffer_size = 2048
        self.address = None
        self.identity = None
        self.window_size = None
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
        conn.set_identity(0)
        syn_list = []
        recv_accept = threading.Thread(target=self.recv_syn, args=(syn_list,))
        recv_accept.start()

        # Use port 6666 to receive first SYN
        target_addr = None  # Record client address
        while True:
            if len(syn_list) == 0:
                continue
            syn_packet = syn_list[0]
            syn_list.pop(0)
            if self.debug:
                print('Receive:' + str(syn_packet[0]) + '\n')
            # Receive SYN
            if syn_packet[0].test_the_packet(SYN=1):
                conn.set_number_receive(syn_packet[0])
                target_addr = syn_packet[1]
                break

        _async_raise(recv_accept.ident, SystemExit)

        # Use conn to transfer syn_ack_packet and it will be allot a new port, then always use conn but not server
        # Server just need to receive the first SYN for each client
        syn_ack_packet = Packet(SYN=1, ACK=1, SEQ_ACK=conn.seq_ack, SEQ=conn.seq)
        begin = time.time()
        conn.transmission(syn_ack_packet, target_addr)

        # Initialize the threading after transmission and a port is given to conn
        while True:
            ack_packet = Packet.from_bytes(conn.recvfrom(self.buffer_size)[0])
            if self.debug:
                print('Receive:' + str(ack_packet) + '\n')
            # Receive ACK
            if ack_packet.test_the_packet(ACK=1):
                conn.set_number_receive(ack_packet)
                if self.debug:
                    print('开启 Port:' + str(target_addr[1]) + ' 的连接' + '\n')
                break
            if time.time() - begin > self.time_out:
                # The second threading need to cut down manually if last ACK not arrive or wrong
                conn.transmission(syn_ack_packet, target_addr)
                begin = time.time()
        conn.set_address(target_addr)
        return conn, conn.address

    def connect(self, address: (str, int)):
        """
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        self.set_identity(1)
        # Use syn_ack_packet[1] to set address
        syn_ack_packet = None
        syn_packet = Packet(SYN=1)
        while_flag = True

        begin = time.time()
        self.transmission(syn_packet, address)
        # Initialize the threading after transmission and a port is given
        syn_ack_list = []
        recv_connect = threading.Thread(target=self.recv_syn, args=(syn_ack_list,))
        recv_connect.start()

        while while_flag:
            while True:
                if len(syn_ack_list) == 0:
                    if time.time() - begin > self.time_out:
                        begin = time.time()
                        self.transmission(syn_packet, address)
                    continue
                syn_ack_packet = syn_ack_list[0]
                syn_ack_list.pop(0)
                if self.debug:
                    print('Receive:' + str(syn_ack_packet[0]) + '\n')
                # Receive SYN ACK
                if syn_ack_packet[0].test_the_packet(SYN=1, ACK=1):
                    self.set_number_receive(syn_ack_packet[0])
                    # send ack
                    ack_packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
                    self.transmission(ack_packet, syn_ack_packet[1])
                    while_flag = False
                    break
                else:
                    # Packet is wrong
                    break
            _async_raise(recv_connect.ident, SystemExit)

        # Set address after three times handshake
        self.set_address(syn_ack_packet[1])

    # Return whole payload(in byte)
    def recv(self, bufsize: int) -> bytes:
        """
        Receive data from the socket.
        The return value is a bytes object representing the data received.
        The maximum amount of data to be received at once is specified by bufsize.

        Note that ONLY data send by the peer should be accepted.
        In other words, if someone else sends data to you from another address,
        it MUST NOT affect the data returned by this function.
        """
        recv_list = []
        recv_list.append(Packet.from_bytes(self.recvfrom(self.buffer_size)[0]))
        #      1.开一个进程收包
        recv = threading.Thread(target=self.recv_many, args=(recv_list,))
        recv.start()
        data = b''  # 存储payload
        # 预先创建一个发包
        while 1:
            # 2. 从list里拿一个收到的包
            if len(recv_list) == 0:
                continue
            packet = recv_list[0]
            recv_list.pop(0)
            if self.debug:
                print('Receive:' + str(packet) + '\n')
            # packet = Packet.from_bytes(packet_bytes)

            if packet.test_the_packet(FIN=1, ACK=1):
                self.set_number_receive(packet)
                _async_raise(recv.ident, SystemExit)
                return data
            elif packet.test_the_packet(ACK=1) or packet.test_the_packet(END=1, ACK=1):
                #           7. 如果来的seq = 我的ack： 返回ack = seq+len, data
                if packet.SEQ == self.seq_ack:
                    self.set_number_receive(packet)
                    data += packet.PAYLOAD
                    if packet.test_the_packet(END=1, ACK=1):
                        self.transmission(Packet(ACK=1, SEQ_ACK=self.seq_ack, SEQ=self.seq), self.address)
                        _async_raise(recv.ident, SystemExit)
                        return data
                    # 检查 buffer ， 看是否可以连上
                    data, end = self.check_receive_buffer(data)
                    if end:
                        self.transmission(Packet(ACK=1, SEQ_ACK=self.seq_ack, SEQ=self.seq), self.address)
                        _async_raise(recv.ident, SystemExit)
                        return data
                # 返回包
                # 如果来的seq > 我的ack：
                # 如果可以就将包存在buffer里，返回我本来的ack
                elif packet.SEQ > self.seq_ack:
                    if len(self.receive_buffer) < self.receive_buffer_size:
                        self.receive_buffer.append(packet)
                    else:
                        pass
                self.transmission(Packet(ACK=1, SEQ_ACK=self.seq_ack, SEQ=self.seq), self.address)

    def check_receive_buffer(self, data):
        # 先排好序，SEQ从小到大
        self.receive_buffer = sorted(self.receive_buffer, key=functools.cmp_to_key(Packet.cmp))
        end = False
        while len(self.receive_buffer) > 0:
            packet = self.receive_buffer[0]
            if packet.SEQ > self.seq_ack:  # 比我大，直接结束
                break
            else:
                if self.seq_ack == packet.SEQ:  # 找到了一个可以接上的包，一系列操作，继续循环
                    self.set_number_receive(packet)
                    data += packet.PAYLOAD
                    if packet.test_the_packet(END=1, ACK=1):
                        end = True
                self.receive_buffer.pop(0)
        return data, end

    def send(self, bytes: bytes):
        """
        Send data to the socket.
        The socket must be connected to a remote socket, i.e. self._send_to must not be none.
        """
        # assert self._send_to, "Connection not established yet. Use sendto instead."
        message_list = cut_the_message(self.buffer_size, bytes)
        self.set_window_size(10)
        pointer = 0
        window_list = []
        # ack_list = []
        max_ack = [-1]
        duplicated_ack = [-1]
        dup_ack_num = [0]
        # state:0--slow start,1--con avoid
        state = [0]
        ssthresh = [10]

        check_ack = threading.Thread(target=self.check_ack,
                                     args=(max_ack, duplicated_ack, dup_ack_num, state, ssthresh))
        check_ack.start()
        # recv.join()
        while True:
            # length is now in window waiting to be acked
            length: int = len(window_list)
            send_number = self.window_size - length
            # push
            for i in range(send_number):
                if pointer < len(message_list):
                    if pointer == len(message_list) - 1:
                        packet = Packet(END=1, ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack, data=message_list[pointer])
                    else:
                        packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack, data=message_list[pointer])
                    self.set_number_send(packet)
                    # (packet,send_time)
                    window_list.append([packet, 0.0])
                    pointer += 1
                else:
                    send_number = i
                    break
            # send new packet
            for j in range(length, send_number + length):
                # print()
                self.transmission(window_list[j][0], self.address)
                window_list[j][1] = time.time()
            if state[0] == 1:
                self.set_window_size(self.window_size + 1)
            # to check the retransmisson and ack, find the max ack
            # for packet in ack_list:
            # check if old packet is timeout or retransmit
            ack_boundary = 0
            for k in range(len(window_list)):
                if window_list[k][0].SEQ < max_ack[0]:
                    continue
                if window_list[k][0].SEQ == max_ack[0]:
                    ack_boundary = k
                    if duplicated_ack[0] == max_ack[0]:
                        self.sendto(window_list[k][0].to_bytes(), self.address)
                        window_list[k][1] = time.time()
                        if self.debug:
                            print('Fast Retransmit:' + str(window_list[k][0]) + '\n')
                        dup_ack_num[0] = 0
                        duplicated_ack[0] = -1
                        # 快恢复，ssthresh砍半，window等于ssthresh，进入拥塞控制（向下取整）
                        # ssthresh[0] = math.floor(ssthresh[0] / 2)
                        # self.set_window_size(ssthresh[0])
                        # state[0] = 1
                        continue

                if time.time() - window_list[k][1] >= self.time_out:
                    self.sendto(window_list[k][0].to_bytes(), self.address)
                    window_list[k][1] = datetime.now().timestamp()
                    if self.debug:
                        print('Timeout Retransmit:' + str(window_list[k][0]) + '\n')
                        # 慢开始，window等于一，
                    # ssthresh[0] = math.floor(self.window_size / 2)
                    # self.set_window_size(1)
                    # state[0] = 0

            if len(window_list) > 0:
                window_list = window_list[ack_boundary:]
                if window_list[-1][0].SEQ < max_ack[0]:
                    window_list = []
                # if ssthresh[0] < len(window_list):
                #     pointer -= len(window_list) - ssthresh[0]
                #     window_list = window_list[:ssthresh[0]]

            if pointer == len(message_list) and len(window_list) == 0:
                # _async_raise(recv.ident, SystemExit)
                _async_raise(check_ack.ident, SystemExit)
                break

    def check_ack(self, max_ack, duplicated_ack, dup_ack_num, state, ssthresh):
        while True:
            packet = Packet.from_bytes(self.recvfrom(self.buffer_size)[0])
            if self.debug:
                print('Receive:' + str(packet) + '\n')
            if packet.test_the_packet(ACK=1):
                if max_ack[0] < packet.SEQ_ACK:
                    max_ack[0] = packet.SEQ_ACK
                    dup_ack_num[0] = 0
                elif max_ack[0] == packet.SEQ_ACK:
                    dup_ack_num[0] += 1
                # # 如果是慢开始，window的size加一
                # if state[0] == 0:
                #     self.set_window_size(self.window_size + 1)
                #     if self.window_size == ssthresh[0]:
                #         state[0] = 1
            if dup_ack_num[0] >= 3:
                duplicated_ack[0] = max_ack[0]

    def recv_many(self, list):
        while True:
            list.append(Packet.from_bytes(self.recvfrom(self.buffer_size)[0]))

    def recv_syn(self, list):  # 加上了地址
        while True:
            data, addr = self.recvfrom(self.buffer_size)
            packet = Packet.from_bytes(data)
            list.append([packet, addr])

    def close(self):
        time_out_close = 0.5
        """
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither futher sends nor receives are allowed.
        """
        ack_list = []
        # open receive thread
        recv = threading.Thread(target=self.recv_many, args=(ack_list,))
        recv.start()

        if self.identity:
            # send fin twice

            fin_packet = Packet(ACK=1, FIN=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            self.transmission(fin_packet, self.address)

            time_start = time.time()
            flag_ack = 0
            flag_fin = 0
            count = 0
            while True:
                if len(ack_list) == 0:
                    if time.time() > time_start + time_out_close:
                        count += 1
                        if count > 20:
                            if self.debug:
                                print('长时间未收到ack，自动关闭 Port:' + str(self.address[1]) + '的连接' + '\n')
                            break
                        time_start = time.time()
                        fin_packet = Packet(ACK=1, FIN=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
                        self.transmission(fin_packet, self.address)
                    continue
                packet = ack_list[0]
                ack_list.pop(0)
                if flag_ack == 0 and packet.test_the_packet(ACK=1):
                    print("receive:" + str(packet) + '\n')
                    self.set_number_receive(packet)
                    flag_ack += 1
                elif flag_fin == 0 and packet.test_the_packet(FIN=1, ACK=1):
                    print("receive:" + str(packet) + '\n')
                    self.set_number_receive(packet)
                    flag_fin += 1
                    # send ack
                if flag_ack and flag_fin:
                    ack_packet2 = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
                    self.transmission(ack_packet2, self.address)
                    break
        else:
            time_start = time.time()
            while 1:
                if time.time() > time_start + 10:
                    time_start = time.time()
                    print('time out')
                    break
                if len(ack_list) > 0:
                    packet = ack_list[0]
                    del ack_list[0]
                    if self.debug:
                        print('Receive:' + str(packet) + '\n')
                    if packet.test_the_packet(FIN=1, ACK=1):
                        break

            count = 0
            # send fin,ack
            fin_ack_packet = Packet(ACK=1, FIN=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            self.transmission(fin_ack_packet, self.address)
            ack_packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
            self.transmission(ack_packet, self.address)
            while 1:
                if len(ack_list) == 0:
                    if time.time() > time_start + time_out_close:
                        count += 1
                        if count >= 10:
                            if self.debug:
                                print('长时间未收到ack，自动关闭 Port:' + str(self.address[1]) + '的连接' + '\n')
                            break
                        ack_packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
                        self.transmission(ack_packet, self.address)
                        # send fin,ack
                        fin_ack_packet = Packet(ACK=1, FIN=1, SEQ=self.seq, SEQ_ACK=self.seq_ack)
                        self.transmission(fin_ack_packet, self.address)
                        time_start = time.time()
                    continue
                packet = ack_list[0]
                ack_list.pop(0)
                if self.debug:
                    print('Receive:' + str(packet) + '\n')
                if packet.test_the_packet(FIN=1, ACK=1):
                    count -= 1
                elif packet.test_the_packet(ACK=1):
                    self.set_number_receive(packet)
                    if self.debug:
                        print('关闭 Port:' + str(self.address[1]) + '的连接' + '\n')
                    break
                else:
                    continue
        _async_raise(recv.ident, SystemExit)
        super().close()

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
            print('Send:' + str(packet) + '\n')

    def reception(self, data):
        packet = Packet.from_bytes(data)
        if self.debug:
            print('Receive:' + str(packet) + '\n')
        return packet

    def set_window_size(self, param):
        self.window_size = param


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


def _async_raise(tid, exctype):
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


"""
You can define additional functions and classes to do thing such as packing/unpacking packets, or threading.

"""

"""
Reliable Data Transfer Segment

Segment Format:

|0 1 2 3 4 5 6 7 8|0 1 2 3 4 5 6 7 8|0 1 2 3 4 5 6 7 8|0 1 2 3 4 5 6 7 8| 
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           (NO USE)        |E|S|F|A|              CHECKSUM             |
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
 - E-END                      EndOf

Ranges:
 - Payload Length           0 - 2^32  (append zeros to the end if length < 1440)
 - Sequence Number          0 - 2^32
 - Acknowledgement Number   0 - 2^32
 - CHECKSUM                 0 - 2^16

Size of sender's window     16
"""
