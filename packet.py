class Packet:
    def __init__(self):
        self.SYN = False
        self.ACK = False
        self.FIN = False
        self.seq = 0
        self.ack = 0
        self.LEN = 0
        self.CHECKSUM = 0
        self.payload = b''

    def to_bytes(self):
        data = b''
        flag = 0
        if self.SYN:
            flag += 0x8000
        if self.ACK:
            flag += 0x4000
        if self.FIN:
            flag += 0x2000
        data += int.to_bytes(flag, 2, byteorder='big')
        data += int.to_bytes(self.CHECKSUM, 2, byteorder='big')
        data += int.to_bytes(self.seq, 4, byteorder='big')
        data += int.to_bytes(self.ack, 4, byteorder='big')
        data += int.to_bytes(self.LEN, 4, byteorder='big')
        data += self.payload

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
        if flag & 0x8000 != 0:
            packet.SYN = True
        if flag & 0x4000 != 0:
            packet.ACK = True
        if flag & 0x2000 != 0:
            packet.FIN = True
        packet.CHECKSUM = int.from_bytes(byte[2:4], byteorder='big')
        packet.seq = int.from_bytes(byte[4:8], byteorder='big')
        packet.ack = int.from_bytes(byte[8:12], byteorder='big')
        packet.LEN = int.from_bytes(byte[12:16], byteorder='big')
        packet.payload = byte[16:]

        completed = packet.LEN % 4
        if completed == 0:
            pass
        elif completed == 3:
            packet.payload = packet.payload[:-1]
        elif completed == 2:
            packet.payload = packet.payload[:-2]
        elif completed == 1:
            packet.payload = packet.payload[:-3]

        assert packet.LEN == len(packet.payload)
        assert Packet.checksum(packet.to_bytes()) == 0

        return packet

    @staticmethod
    def create(seq=0, ack=0, data=b'', SYN=False, ACK=False, FIN=False):
        packet = Packet()
        packet.ACK = ACK
        packet.FIN = FIN
        packet.SYN = SYN

        packet.seq = seq
        packet.ack = ack
        packet.LEN = len(data)

        packet.payload = data
        packet.CHECKSUM = 0
        checksum = Packet.checksum(packet.to_bytes())
        packet.CHECKSUM = checksum

        return packet

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
        res = ""

        if self.SYN:
            res += "\033[94mSYN\033[0m "
        if self.ACK:
            res += "\033[93mACK\033[0m "
        if self.FIN:
            res += "\033[91mFIN\033[0m "

        res += "["
        res += "seq={}, ".format(self.seq)
        res += "ack={}, ".format(self.ack)

        if self.LEN != 0:
            res += "Len={}, ".format(self.LEN)
            res += "] "
            res += str(self.payload)
        else:
            res += "] "

        return res


if __name__ == "__main__":
    # test Packet
    packet = Packet.create(1, 2, b'\xFF', False, True, False)
    print(packet.CHECKSUM)

    byte = packet.to_bytes()
    print(Packet.checksum(byte))

    packet2 = Packet.from_bytes(byte)
    print(packet2.CHECKSUM)

    bit_error = bytearray(byte)
    bit_error[16] = 0xEE
    try:
        packet3 = Packet.from_bytes(bytes(bit_error))
    except:
        print("find bit error")
    else:
        raise Exception("not find bit error")
