from rdt import RDTSocket

SERVER_ADDR = '127.0.0.1'
SERVER_PORT = 6666
MESSAGE = b'0xFF'
BUFFER_SIZE = 2048

client = RDTSocket()
client.connect((SERVER_ADDR, SERVER_PORT))
client.send(MESSAGE)
data = client.recv(BUFFER_SIZE)
client.close()
