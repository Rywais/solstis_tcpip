import socket
import json

SOCKET_ADDR = '192.168.1.222'
SOCKET_PORT = 39933
IP_ADDRESS = '192.168.1.107'

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

sock.connect((SOCKET_ADDR,SOCKET_PORT))

#Create JSON Command:
parameters = {"ip_address": IP_ADDRESS}
message = {"transmission_id": [999],
           "op": "start_link",
           "parameters": parameters}
command = {"message": message}

try:
  send_msg = json.dumps(command).encode('utf8')
  sock.sendall(send_msg)

  amount_received = 0
  amount_expected = 32#TODO: Refer to previous TODO
  data = b''

  while amount_received < amount_expected:
    temp = sock.recv(16)
    amount_received = amount_received + len(temp)
    data = data + temp
  print('Your received data follows:')
  print(data)

finally:
  print('Closing Socket')
  sock.close()

