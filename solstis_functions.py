import time
import socket
import json

class SolstisError(Exception):
  """Exception raised when the Solstis response indicates an error

  Attributes:
    message ~ explanation of the error
  """
  def __init__(self,message):
    self.message = message

def init_socket(address='192.168.1.222',port=39933):
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.connect((address,port))
  sock.settimeout(1)
  return sock

def send_msg(s,transmission_id,op,params=None):
  """
  Function to carry out the most basic communication send function
  s ~ Socket
  transmission_id ~ Arbitrary(?) integer
  op ~ String containing operating command
  params ~ dict containing Solstis Key/Value pairs as necessary
  """
  if params is not None:
    message = {"transmission_id": [transmission_id],
               "op": op,
               "parameters": params}
  else:
    message = {"transmission_id": [transmission_id],
               "op": op}
  command = {"message": message}
  send_msg = json.dumps(command).encode('utf8')
  s.sendall(send_msg)

#TODO: Make this safe in case of multiple messages queued
def recv_msg(s,timeout=10.):
  data = ''
  while True:
    data += s.recv(1024).decode('utf8')
    if data.count('{') == data.count('}'):
      break
  return json.loads(data)

def verify_msg(msg,op=None,transmission_id=None):
  msgID = msg["message"]["transmission_id"][0]
  msgOP = msg["message"]["op"]
  if transmission_id is not None:
    if msgID != transmission_id:
      msg = "Message with ID"+str(msgID)+" did not match expected ID of: "+\
            str(transmission_id)
  if msg["message"]["op"] == "parse_fail":
    msg = "Mesage with ID "+str(msgID)+" failed to parse."
    raise SolstisError(msg)
  if op is not None:
    if msgOP != op:
      msg = "Message with ID"+str(msgID)+"with operation command of '"+msgOP+\
            "' did not match expected operation command of: "+op
      raise SolstisError(msg)

def start_link(sock,transmission_id=1,ip_address='192.168.1.107'):
  send_msg(sock,transmission_id,'start_link',{'ip_address': ip_address})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op='start_link_reply')
  if val["message"]["parameters"]["status"] == "ok":
    return
  elif val["message"]["parameters"]["status"] == "failed":
    raise SolstisError("Link could not be formed")
  else:
    raise SolstisError("Unknown error: Could not determine link status")

def set_wave_m(sock, wavelength, transmission_id = 1):
  """Sets wavelength given that a wavelength meter is configured

  Parameters:
    sock ~ Socket object to use
    wavelength ~ (float) wavelength to tune to in nanometers
    transmission_id ~ (int) Arbitrary integer
  Returns:
    The wavelength of the most recent measurement made by the wavelength meter
  """
  send_msg(sock,transmission_id,"set_wave_m",{"wavelength": [wavelength]})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op="set_wave_m_reply")
  status = val["message"]["parameters"]["status"]
  if status == 1:
    raise SolstisError("No (wavelength) meter found.")
  elif status == 2:
    raise SolstisError("Wavelength Out of Range.")
  return val["message"]["parameters"]["wavelength"][0]

def poll_wave_m(sock,transmission_id=1):
  """Gets the latest Wavemeter reading and current wavelength tuning status

  Parameters:
    sock ~ socket object to use
    transmission_id ~ (int) Arbitrary integer to use for communications
  Returns:
    Tuple containing (in increasing index order):
      -floating point value for current wavelength
      -Boolean stating whether tuning is done/inactive (True = Not tuning)
  """

  send_msg(sock,transmission_id,"poll_wave_m")
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op="poll_wave_m_reply")
  status = val["message"]["parameters"]["status"][0]
  if status == 1:
    raise SolstisError("No (wavelength) meter found.")
  elif status == 0 or status == 3:
    status = True #Not tuning
  else:
    status = False #Still Tuning
  return val["message"]["parameters"]["current_wavelength"][0], status

def move_wave_t(sock, wavelength, transmission_id=1):
  """Sets the wavelength based on wavelength table

  Parameters:
    sock ~ socket object to use
    wavelength ~ (float) wavelength set point
    transmission_id ~ (int) Arbitrary integer for communications
  Returns:
    Nothing
  """

  send_msg(sock,transmission_id,"move_wave_t", {"wavelength": [wavelength]})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op="move_wave_t_reply")
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("move_wave_t: Failed, is your wavemeter configured?")
  else:
    raise SolstisError("Wavelength out of range.")

def poll_move_wave_t(sock,transmission_id=1):
  """Gets the currently set wavelength according to wavelength table

  Parameters:
    sock ~ socket object to use
    transmission_id ~ (int) Arbitrary integer for communications
  Returns:
    Tuple containing the following (in increasing index order):
      -Current wavelength
      -Boolean with value True if Tuning is not taking place, False o/w
  """
  send_msg(sock,transmission_id,"poll_move_wave_t")
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op="poll_move_wave_t_reply")
  status = val["message"]["parameters"]["status"][0]
  if status == 2:
    raise SolstisError("poll_move_wave_t: Failed,is your wavemeter configured?")
  elif status == 1:
    status = False
  else:
    status = True
  return val["message"]["parameters"]["wavelength"][0], status
