from rdt import RDTSocket
import time
from difflib import Differ

client = RDTSocket()
client.connect(('127.0.0.1', 9999))

data_count = 0
echo = b''
count = 3

with open('alice.txt', 'r') as f:
    data = f.read()
    encoded = data.encode()
    assert len(data)==len(encoded)

start = time.perf_counter()
for i in range(count): # send 'alice.txt' for count times
    data_count+=len(data)
    client.send(encoded)

'''
blocking send works but takes more time 
'''

while True:
    reply = client.recv(2048)
    echo += reply
    print(reply)
    if len(echo)==len(encoded)*count:
        break
client.close()

'''
make sure the following is reachable
'''

print(f'transmitted {data_count}bytes in {time.perf_counter()-start}s')
diff = Differ().compare(data.splitlines(keepends=True), echo.decode().splitlines(keepends=True))
for line in diff:
    assert line.startswith('  ') # check if data is correctly echoed
