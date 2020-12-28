import time

from rdt import RDTSocket

SERVER_ADDR = '127.0.0.1'
SERVER_PORT = 6666

server = RDTSocket()
server.bind((SERVER_ADDR, SERVER_PORT))

while True:
    begin = time.time()
    conn, client = server.accept()
    # time.sleep(10)
    while True:

        data = conn.recv(2048)
        # break
        if data:
            break
        # conn.send(data)

    conn.close()
    print(data)
    print(time.time() - begin)
