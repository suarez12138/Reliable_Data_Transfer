from rdt import RDTSocket

SERVER_ADDR = '127.0.0.1'
SERVER_PORT = 12345

server = RDTSocket()
server.bind((SERVER_ADDR, SERVER_PORT))

while True:
    conn, client = server.accept()
    while True:
        data = conn.recvfrom(2048)
        if not data:
            break
        conn.send(data)
    conn.close()

