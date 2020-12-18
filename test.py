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
                if duplicated_ack>=3:
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
        if pointer == len(message_list) and len(window_list.items)==0:
            break

    def recv_many(self, ack_list):
        while True:
            ack_list.append(Packet.from_bytes(self._recv_from(self.buffer_size)[0]))

