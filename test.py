import threading
from datetime import datetime

from packet import Packet

from rdt import RDTSocket, cut_the_message, Queue

self = RDTSocket()
message_list = []


def send(self, bytes: bytes):
    """
    Send data to the socket.
    The socket must be connected to a remote socket, i.e. self._send_to must not be none.
    """
    # assert self._send_to, "Connection not established yet. Use sendto instead."

    message_list = cut_the_message(self.buffer_size, bytes)
    self.set_window_size(len(message_list))
    pointer = 0
    window_list = Queue()
    ack_list = []

    # open receive thread
    recv = threading.Thread(target=self.recv_many, args=(ack_list))
    recv.start()
    recv.join()
    while True:
        # length is now in window waiting to be acked
        length: int = len(window_list.items)
        send_number = self.window_size - length
        # push
        for i in range(send_number):
            if pointer < len(message_list):
                packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack, data=message_list[pointer])
                self.set_number_send(packet)
                # (packet,send_time,condition:0 is not ack and 1 is ack)
                window_list.push((packet, 0, 0))
                pointer += 1
            else:
                send_number = i
                break
        # send new packet
        for j in range(length, send_number + len):
            self._send_to(window_list.items[j + length], self.address)
            window_list.items[j][1] = datetime.now().timestamp()
            if self.debug:
                print('Send:', window_list.items[j + length][0])

        # to check the retransmisson and ack, find the max ack
        duplicated_ack = 0
        max_ack = 0
        for packet in ack_list:
            if max_ack < packet.SEQ_ACK:
                max_ack = packet.SEQ_ACK
            elif max_ack == packet.SEQ_ACK:
                duplicated_ack += 1

        # check if old packet is timeout or retransmit
        for k in range(length):
            if window_list.items[k][0].SEQ < max_ack:
                window_list.items[k][2] = 1
            elif window_list.items[k][0].SEQ == max_ack:
                if duplicated_ack >= 3:
                    self._send_to(window_list.items[k][0], self.address)
                    window_list.items[k][1] = datetime.now().timestamp()
                    if self.debug:
                        print('Fast Retransmit:', window_list.items[k][0])
            elif datetime.now().timestamp() - window_list.items[k][1] >= 1:
                self._send_to(window_list.items[k][0], self.address)
                window_list.items[k][1] = datetime.now().timestamp()
                if self.debug:
                    print('Timout Retransmit:', window_list.items[k][0])

        while window_list.items[0][2] == 1:
            window_list.pop()
        if pointer == len(message_list) and len(window_list.items) == 0:
            break

    def recv_many(self, list):
        while True:
            list.append(Packet.from_bytes(self._recv_from(self.buffer_size)[0]))


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
        data = b''  # 存储payload
        recv_list=[]
        #      1.开一个进程收包
        recv = threading.Thread(target=self.recv_many,args=recv_list)
        recv.start()
        recv.join()
        #    while:
          # 预先创建一个发包
        while 1:
            # 2. 从list里拿一个收到的包
            if len(recv_list) == 0:
                continue
            packet_bytes, addr = recv_list[0]
            del recv_list[0]
            packet = Packet.from_bytes(packet_bytes)
            if packet.test_the_packet(FIN=1,ACK=1):
                self.set_number_receive(packet)
                return None
            elif packet.test_the_packet(ACK=1):
                #           7. 如果来的seq = 我的ack： 返回ack = seq+len, data
                if packet.SEQ == self.seq_ack:
                    self.set_number_receive(packet)
                    data += packet.PAYLOAD
                    # 检查 buffer ， 看是否可以连上
                    self.check_receive_buffer(data)
                    # 返回包
                    packet_send = Packet(SEQ_ACK=self.seq_ack, SEQ=self.seq)
                    self.transmission(packet_send, self.address)
                #           8. 如果来的seq > 我的ack：
                #           如果可以就将包存在buffer里，返回我本来的ack
                elif packet.SEQ > self.seq_ack:
                    if len(self.receive_buffer) < self.receive_buffer_size:
                        self.receive_buffer.append(packet)
                    packet_send = Packet(ACK=1, SEQ_ACK=self.seq_ack, SEQ=self.seq)
                    self.transmission(packet_send, self.address)


    def check_receive_buffer(self, data):
        flag = 1
        while flag:
            flag = 0
            for packet in self.receive_buffer:
                if self.seq_ack == packet.SEQ:  # 找到了一个可以接上的包，一系列操作，继续循环
                    self.set_number_receive(packet)
                    data += packet.PAYLOAD
                    flag = 1
                if packet.SEQ <= self.seq_ack:  # 过时的包， 删掉
                    self.receive_buffer.remove(packet)
