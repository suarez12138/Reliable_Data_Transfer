import threading
from datetime import datetime

from packet import Packet
from rdt import RDTSocket


self=RDTSocket()
message_list=[]
#
# send_state=threading.Thread()
# recv_state=threading.Thread()
# send_state.start()
# recv_state.start()
# send_state.join()
# recv_state.join()
#
#
# def send_many(self, i, message_list):
#     while True:
#         now = datetime.now().timestamp()
#         for packet,send_time in message_list:
#             if self.seq >= packet.seq + packet.LEN:
#                 continue
#             if now - send_time >= 1.0:
#                 print(self.state, "retransmit ", end='')
#                 self.send_packet(packet)
#             else:
#                 conn.sending.append((packet, send_time))
#                 continue
#         # now = datetime.now().timestamp()
#         # packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack, data=message_list[i])
#         # self.set_number_send(packet)
#         # self._send_to(packet.to_bytes(), self.address)
#         # if self.debug:
#         #     print('Send:', packet)
#         # ack_packet = Packet.from_bytes(self._recv_from(self.buffer_size)[0])
#         # if self.debug:
#         #     print('Receive:', ack_packet)
#         # if ack_packet.test_the_packet(ACK=1):
#         #     self.set_number_receive(ack_packet)
#         #     break
#         # else:
#         #     continue
#
#         # for packet, send_time in sending:
#         #     if conn.seq >= packet.seq + packet.LEN:
#         #         continue
#         #     if now - send_time >= 1.0:
#         #         print(conn.state, "retransmit ", end='')
#         #         conn.send_packet(packet)
#         #     else:
#         #         conn.sending.append((packet, send_time))
#
#
#         for i in range(len(message_list)):
#             while True:
#                 packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack, data=message_list[i])
#                 self.set_number_send(packet)
#                 self._send_to(packet.to_bytes(), self.address)
#                 if self.debug:
#                     print('Send:', packet)
#                 ack_packet = Packet.from_bytes(self._recv_from(self.buffer_size)[0])
#                 if self.debug:
#                     print('Receive:', ack_packet)
#                 if ack_packet.test_the_packet(ACK=1):
#                     self.set_number_receive(ack_packet)
#                     break
#                 else:
#                     continue
a=[0]*8
del a[1]
print(a)


send = threading.Thread(target=self.recv_many, args=(window_list, j, datetime.now().timestamp()))
                window_list.items[j][3]=send
                send.start()


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
    while True:
        #open receive thread
        recv = threading.Thread(target=self.recv_many, args=(window_list))
        length = len(window_list.items)
        send_number = self.window_size - length
        # push
        for i in range(send_number):
            if pointer < len(message_list):
                packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack, data=message_list[pointer])
                self.set_number_send(packet)
                # (packet,send_time,condition:0 is not ack 1 is ack)
                window_list.push((packet, 0, 0))
                pointer += 1
            else:
                send_number = i
                break
        #send new packet
        for j in range(length, send_number + len):
            self._send_to(window_list.items[j + length], self.address)
            window_list.items[j][1] = datetime.now().timestamp()
            if self.debug:
                print('Send:', window_list.items[j + length][0])

        #check if old packet is timeout
        for k in range(length):
            if datetime.now().timestamp() - window_list.items[1] >= 1:
                self._send_to(window_list.items[k][0], self.address)
                window_list.items[k][1] = datetime.now().timestamp()
                if self.debug:
                    print('Retransmmit:', window_list.items[k][0])

        while window_list.items[0][2] == 1:
            window_list.pop()
        if pointer == len(message_list) and len(window_list.items):
            break
    def recv_many(self, window_list):
        while True:
            ack_packet = Packet.from_bytes(self._recv_from(self.buffer_size)[0])
            if self.debug:
                print('Receive:', ack_packet)
            if ack_packet.test_the_packet(ACK=1):
                self.set_number_receive(ack_packet)
                ####延迟确认 need to be modified
            else:
                pass



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
    ack_list=[]
    while True:
        #open receive thread
        recv = threading.Thread(target=self.recv_many, args=(ack_list))
        length = len(window_list.items)
        send_number = self.window_size - length
        # push
        for i in range(send_number):
            if pointer < len(message_list):
                packet = Packet(ACK=1, SEQ=self.seq, SEQ_ACK=self.seq_ack, data=message_list[pointer])
                self.set_number_send(packet)
                # (packet,send_time,condition:0 is not ack 1 is ack)
                window_list.push((packet, 0, 0))
                pointer += 1
            else:
                send_number = i
                break
        #send new packet
        for j in range(length, send_number + len):
            self._send_to(window_list.items[j + length], self.address)
            window_list.items[j][1] = datetime.now().timestamp()
            if self.debug:
                print('Send:', window_list.items[j + length][0])

        #check the retransmisson
        for i in ack_list:
            pass
        #need to be modified

        #check if old packet is timeout
        for k in range(length):
            if datetime.now().timestamp() - window_list.items[1] >= 1:
                self._send_to(window_list.items[k][0], self.address)
                window_list.items[k][1] = datetime.now().timestamp()
                if self.debug:
                    print('Retransmmit:', window_list.items[k][0])

        while window_list.items[0][2] == 1:
            window_list.pop()
        if pointer == len(message_list) and len(window_list.items):
            break
    def recv_many(self, ack_list):
        while True:
            ack_packet = Packet.from_bytes(self._recv_from(self.buffer_size)[0])
            if self.debug:
                print('Receive:', ack_packet)
            if ack_packet.test_the_packet(ACK=1):
                self.set_number_receive(ack_packet)
                ack_list.append(ack_packet)

                
            else:
                pass