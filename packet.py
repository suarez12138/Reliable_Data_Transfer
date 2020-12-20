class Packet:
    def __init__(self, SYN=False, FIN=False, ACK=False, SEQ=0, SEQ_ACK=0, data=b''):
        self.SYN = SYN
        self.ACK = ACK
        self.FIN = FIN
        self.SEQ = SEQ
        self.SEQ_ACK = SEQ_ACK
        self.LEN = len(data)
        self.PAYLOAD = data
        self.CHECKSUM = 0
        self.CHECKSUM = self.checksum(self.to_bytes())

    def to_bytes(self):
        data = b''
        flag = 0
        if self.SYN:
            flag += 0x0004
        if self.FIN:
            flag += 0x0002
        if self.ACK:
            flag += 0x0001
        data += int.to_bytes(flag, 2, byteorder='big')
        data += int.to_bytes(self.CHECKSUM, 2, byteorder='big')
        data += int.to_bytes(self.SEQ, 4, byteorder='big')
        data += int.to_bytes(self.SEQ_ACK, 4, byteorder='big')
        data += int.to_bytes(self.LEN, 4, byteorder='big')
        data += self.PAYLOAD

        completed = self.LEN % 4
        if completed == 0:
            pass
        elif completed == 3:
            data += b'\x00'
        elif completed == 2:
            data += b'\x00\x00'
        elif completed == 1:
            data += b'\x00\x00\x00'

        return data

    @staticmethod
    def from_bytes(byte: bytes):
        packet = Packet()
        flag = int.from_bytes(byte[0:2], byteorder='big')
        if flag & 0x8004 != 0:
            packet.SYN = True
        if flag & 0x0002 != 0:
            packet.FIN = True
        if flag & 0x0001 != 0:
            packet.ACK = True
        packet.CHECKSUM = int.from_bytes(byte[2:4], byteorder='big')
        packet.SEQ = int.from_bytes(byte[4:8], byteorder='big')
        packet.SEQ_ACK = int.from_bytes(byte[8:12], byteorder='big')
        packet.LEN = int.from_bytes(byte[12:16], byteorder='big')
        packet.PAYLOAD = byte[16:]

        completed = packet.LEN % 4
        if completed == 0:
            pass
        elif completed == 3:
            packet.PAYLOAD = packet.PAYLOAD[:-1]
        elif completed == 2:
            packet.PAYLOAD = packet.PAYLOAD[:-2]
        elif completed == 1:
            packet.PAYLOAD = packet.PAYLOAD[:-3]

        ###########################################################################3需要修改
        # assert packet.LEN == len(packet.PAYLOAD)
        # assert Packet.checksum(packet.to_bytes()) == 0
        return packet

    def test_the_packet(self, SYN=0, FIN=0, ACK=0):

        if not self.SYN == SYN:
            return False
        if not self.FIN == FIN:
            return False
        if not self.ACK == ACK:
            return False
        if not self.LEN == len(self.PAYLOAD):
            return False
        if not self.checksum(self.to_bytes()) == 0:
            return False
        return True

    @staticmethod
    def checksum(data: bytes):
        length = len(data)
        sum = 0
        for i in range(0, int(length / 2)):
            b = int.from_bytes(data[0: 2], byteorder='big')
            # print(hex(data[0]), hex(data[1]))
            data = data[2:]
            sum = (sum + b) % 65536
        return (65536 - sum) % 65536

    def __str__(self) -> str:
        output = ""
        output += "[ "

        if self.SYN:
            output += "\033[1;91mSYN\033[0m "
        if self.FIN:
            output += "\033[1;95mFIN\033[0m "
        if self.ACK:
            output += "\033[1;94mACK\033[0m "
        output += "] "

        output += "SEQ={}, ".format(self.SEQ)
        output += "SEQ_ACK={}, ".format(self.SEQ_ACK)
        output += "LEN={} ".format(self.LEN)
        if self.LEN != 0:
            output += "\n "
            output += str(self.PAYLOAD)

        return output

    def cmp(self, other):  # 自定义比较函数
        if self.SEQ < other.SEQ:
            return -1
        elif self.SEQ == other.SEQ:
            return 0
        else:
            return 1
# if __name__ == "__main__":
#     # test Packet
#     packet = Packet.create(1, 2, b'\xFF', False, True, False)
#     print(packet.CHECKSUM)
#
#     byte = packet.to_bytes()
#     print(Packet.checksum(byte))
#
#     packet2 = Packet.from_bytes(byte)
#     print(packet2.CHECKSUM)
#
#     bit_error = bytearray(byte)
#     bit_error[16] = 0xEE
#     try:
#         packet3 = Packet.from_bytes(bytes(bit_error))
#     except:
#         print("find bit error")
#     else:
#         raise Exception("not find bit error")
