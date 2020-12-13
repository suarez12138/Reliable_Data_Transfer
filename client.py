from rdt import RDTSocket

SERVER_ADDR = '127.0.0.1'
SERVER_PORT = 12345
MESSAGE = 'abcdefg'
BUFFER_SIZE = 2048

client = RDTSocket()
client.connect((SERVER_ADDR, SERVER_PORT))
client.send(MESSAGE)
data = client.recv(BUFFER_SIZE)
assert data == MESSAGE
client.close()
