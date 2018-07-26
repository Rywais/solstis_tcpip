import time
import socket
import json
from enum import Enum

#Global variables for use within module
next_data = '' #Extra TCP socket data to carry forward for next read statement

#Exception class for Solstis specific errors
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
  sock.settimeout(100)
  return sock

def send_msg(s,transmission_id=1,op='start_link',params=None,debug=False):
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
  if debug==True:
    print(send_msg)
  s.sendall(send_msg)

def recv_msg(s,timeout=10.):
  global next_data
  i = 0 #Index
  open_brc_count = 1 #Open Brace Count
  close_brc_count = 0 #Closing brace count
  #Initialize data
  data = next_data

  #Check For existing data and if so, parse it
  if len(data) > 0:
    if data[0] != "{":
      raise SolstisError("Stored data from previous TCP/IP is invalid.")
  
    #Check if existing data contains complete message
    for i in range(1,len(data)):
      if data[i] == "{":
        open_brc_count += 1
      elif data[i] == "}":
        close_brc_count += 1
        if close_brc_count == open_brc_count:
          next_data = data[i+1:len(data)]
          data = data[0:i+1]
          return json.loads(data)
  
  #There is NOT a complete message cached so we must continue to read TCP/IP

  #Start timing in case of timeout
  init_time = time.perf_counter()
  #Loop reading TCP/IP until there is some data
  while len(data) == 0:
    data += s.recv(1024).decode('utf8')
    if time.perf_counter() - init_time > timeout:
      raise TimeoutError()

  #Check (if not already done so) that the message starts with a '{'
  if i == 0:
    if data[0] != "{":
      raise SolstisError("Received data from TCP/IP is invalid.")

  #Loop checking for complete message and receiving new data
  while True:
    if len(data) > i+1:
      for i in range(i+1,len(data)):
        if data[i] == "{":
          open_brc_count += 1
        elif data[i] == "}":
          close_brc_count += 1
          if close_brc_count == open_brc_count:
            next_data = data[i+1:len(data)]
            data = data[0:i+1]
            return json.loads(data)
    data += s.recv(1024).decode('utf8')
    if time.perf_counter() - init_time > timeout:
      raise TimeoutError()

def verify_msg(msg,op=None,transmission_id=None):
  msgID = msg["message"]["transmission_id"][0]
  msgOP = msg["message"]["op"]
  if transmission_id is not None:
    if msgID != transmission_id:
      err_msg = "Message with ID"+str(msgID)+" did not match expected ID of: "+\
            str(transmission_id)
      raise SolstisError(err_msg)
  if msgOP == "parse_fail":
    err_msg = "Mesage with ID "+str(msgID)+" failed to parse."
    err_msg += '\n\n'+str(msg)
    raise SolstisError(err_msg)
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

#Same as above but requests a final report as well
def set_wave_m_f_r(sock, wavelength, transmission_id = 1):
  """Sets wavelength given that a wavelength meter is configured

  Parameters:
    sock ~ Socket object to use
    wavelength ~ (float) wavelength to tune to in nanometers
    transmission_id ~ (int) Arbitrary integer
  Returns:
    The wavelength of the most recent measurement made by the wavelength meter
  """
  send_msg(sock,transmission_id,"set_wave_m",{"wavelength": [wavelength],
                                              "report": "finished"})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op="set_wave_m_reply")
  status = val["message"]["parameters"]["status"]
  if status == 1:
    raise SolstisError("No (wavelength) meter found.")
  elif status == 2:
    raise SolstisError("Wavelength Out of Range.")
  #Final Report
  val = recv_msg(sock)
  verify_msg(val,op="set_wave_m_f_r")
  #TODO: Check other variables
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
    statu
  else:
    status = True
  return val["message"]["parameters"]["wavelength"][0], status

#TODO: Move to own file?
class TeraScan(Enum):
  SCAN_TYPE_MEDIUM = 1
  SCAN_TYPE_FINE = 2
  SCAN_TYPE_LINE = 3

  SCAN_RATE_MEDIUM_100_GHZ = 4
  SCAN_RATE_MEDIUM_50_GHZ = 5
  SCAN_RATE_MEDIUM_20_GHZ = 6
  SCAN_RATE_MEDIUM_15_GHZ = 7
  SCAN_RATE_MEDIUM_10_GHZ = 8
  SCAN_RATE_MEDIUM_5_GHZ = 9
  SCAN_RATE_MEDIUM_2_GHZ = 10
  SCAN_RATE_MEDIUM_1_GHZ = 11
  SCAN_RATE_FINE_LINE_20_GHZ = 12
  SCAN_RATE_FINE_LINE_10_GHZ = 13
  SCAN_RATE_FINE_LINE_5_GHZ = 14
  SCAN_RATE_FINE_LINE_2_GHZ = 15
  SCAN_RATE_FINE_LINE_1_GHZ = 16
  SCAN_RATE_FINE_LINE_500_MHZ = 17
  SCAN_RATE_FINE_LINE_200_MHZ = 18
  SCAN_RATE_FINE_LINE_100_MHZ = 19
  SCAN_RATE_FINE_LINE_50_MHZ = 20
  SCAN_RATE_FINE_LINE_20_MHZ = 21
  SCAN_RATE_FINE_LINE_10_MHZ = 22
  SCAN_RATE_FINE_LINE_5_MHZ = 23
  SCAN_RATE_FINE_LINE_2_MHZ = 24
  SCAN_RATE_FINE_LINE_1_MHZ = 25
  SCAN_RATE_LINE_500_KHZ = 26
  SCAN_RATE_LINE_200_KHZ = 27
  SCAN_RATE_LINE_100_KHZ = 28
  SCAN_RATE_LINE_50_KHZ = 29

#TODO: Ensure that the Units parameters is filled in
def scan_stitch_initialize(sock,
                           scan_type,
                           start,
                           stop,
                           scan_rate,
                           transmission_id=1):
  """Initializes TeraScan operations

  Parameters:
    sock ~ Socket to use for communications
    transmission_id ~ (int) Arbitrary integer for communications 
    scan_type ~ (TeraScan Enum) Type of scan to perform
    start ~ (float) Starting wavelength for scan
    stop ~ (float) Ending wavelength for scan
    scan_rate ~ (TeraScan Enum) Scan rate for scan1
  Returns:
    Nothing on success
  Raises:
    SolstisError on failure to initialize
    ValueError on illegal argument input
  """

  #Create the message based on Input:
  #Scan Type:
  if scan_type == TeraScan.SCAN_TYPE_MEDIUM:
    scan_type = "medium"
  elif scan_type == TeraScan.SCAN_TYPE_FINE:
    scan_type = "fine"
  elif scan_type == TeraScan.SCAN_TYPE_LINE:
    scan_type = "line"
  else:
    raise ValueError('scan_type is not a valid TeraScan Enum')

  #Scan Rate and units:
  if scan_rate == TeraScan.SCAN_RATE_MEDIUM_100_GHZ:
    scan_rate = [100]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_MEDIUM_50_GHZ:
    scan_rate = [50]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_MEDIUM_20_GHZ:
    scan_rate = [20]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_MEDIUM_15_GHZ:
    scan_rate = [15]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_MEDIUM_10_GHZ:
    scan_rate = [10]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_MEDIUM_5_GHZ:
    scan_rate = [5]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_MEDIUM_2_GHZ:
    scan_rate = [2]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_MEDIUM_1_GHZ:
    scan_rate = [1]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_20_GHZ:
    scan_rate = [20]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_10_GHZ:
    scan_rate = [10]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_5_GHZ:
    scan_rate = [5]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_2_GHZ:
    scan_rate = [2]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_1_GHZ:
    scan_rate = [1]; units = "GHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_500_MHZ:
    scan_rate = [500]; units = "MHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_200_MHZ:
    scan_rate = [200]; units = "MHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_100_MHZ:
    scan_rate = [100]; units = "MHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_50_MHZ:
    scan_rate = [50]; units = "MHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_20_MHZ:
    scan_rate = [20]; units = "MHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_10_MHZ:
    scan_rate = [10]; units = "MHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_5_MHZ:
    scan_rate = [5]; units = "MHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_2_MHZ:
    scan_rate = [2]; units = "MHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_FINE_LINE_1_MHZ:
    scan_rate = [1]; units = "MHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_LINE_500_KHZ:
    scan_rate = [500]; units = "kHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_LINE_200_KHZ:
    scan_rate = [200]; units = "kHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_LINE_100_KHZ:
    scan_rate = [100]; units = "kHz/s"
  elif scan_rate == TeraScan.SCAN_RATE_LINE_50_KHZ:
    scan_rate = [50]; units = "kHz/s"
  else:
    raise ValueError("Input Scan rate is not valid TeraScan Enum.")

  send_msg(sock,transmission_id,"scan_stitch_initialise",
                      {"scan": scan_type,
                      "start": [start],
                      "stop": [stop],
                      "rate": scan_rate,
                      "units": units})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,
             op="scan_stitch_initialise_reply")
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("TeraScan start wavelength out of range.")
  elif status == 2:
    raise SolstisError("TeraScan stop wavelength out of range.")
  elif status == 3:
    raise SolstisError("TeraScan requested scan range is out of range.")
  else:
    raise SolstisError("TeraScan is not available.")

def scan_stitch_op(sock, scan_type, operation, transmission_id=1):
  """Controls the TeraScan Operation

  Parameters:
    sock ~ Socket to use for communications
    transmission_id ~ (int) Arbitrary integer for use in communications
    scan_type ~ (TeraScan Enum) Type of scan to carry out 
    operation ~ (str) Either "start" or "stop"
  Returns:
    Nothing
  Raises:
    SolstisError on failure to execute command
    ValueError if scan type is invalid
  """

  #Translate Scan type:
  if scan_type == TeraScan.SCAN_TYPE_MEDIUM:
    scan_type = "medium"
  elif scan_type == TeraScan.SCAN_TYPE_FINE:
    scan_type = "fine"
  elif scan_type == TeraScan.SCAN_TYPE_LINE:
    scan_type = "line"
  else:
    raise ValueError("scan_type is not a valid TeraScan Enum")

  send_msg(sock,transmission_id,"scan_stitch_op",{
                                "scan": scan_type,
                                "operation": operation})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op="scan_stitch_op_reply")
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("TeraScan Failed; Unknown Reason.")
  else:
    raise SolstisError("TeraScan not Available.")

def scan_stitch_status(sock,scan_type,transmission_id=1):
  """Checks the status of the TeraScan operations on Solstis

  Parameters:
    sock ~ Socket to use for communications
    transmission_id ~ (int) Arbitrary integer for communications
    scan_type ~ (TeraScan Enum) Type of TeraScan
  Returns:
    Dictionary containing the following key/value pairs:
      "in_progress" ~ (Boolean) True if a scan is in progress [Note: Other
                                values will be omitted if this is False.]
      "wavelength" ~ (float) Current wavelength in scan
      "start" ~ (float) Starting wavelength from scan
      "stop" ~ (float) Ending wavelength in scan
      "tuning" ~ (Boolean) True if TeraScan is currently tuning and False if
                           it's currently scanning
  Raises:
    SolstisError if TeraScan is not available
    ValueError if scan_type is not a valid TeraScan Enum

  """
  #Scan Type:
  if scan_type == TeraScan.SCAN_TYPE_MEDIUM:
    scan_type = "medium"
  elif scan_type == TeraScan.SCAN_TYPE_FINE:
    scan_type = "fine"
  elif scan_type == TeraScan.SCAN_TYPE_LINE:
    scan_type = "line"
  else:
    raise ValueError('scan_type is not a valid TeraScan Enum')
  send_msg(sock,transmission_id,"scan_stitch_status",{"scan":scan_type})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,
             op="scan_stitch_status_reply")
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    in_progress = False
    return {"in_progress":in_progress}
  elif status == 1:
    in_progress = True
  else:
    raise SolstisError("TeraScan is not available")

  #At this point we know in_progress=True so we fill out other entries
  wavelength = val["message"]["parameters"]["current"][0]
  start = val["message"]["parameters"]["start"][0]
  stop = val["message"]["parameters"]["stop"][0]
  current_op = val["message"]["parameters"]["operation"][0]
  if current_op == 0:
    tuning = True
  else:
    tuning = False

  return_dict = {"in_progress": in_progress, "wavelength": wavelength,
                 "start": start, "stop": stop, "tuning": tuning}
  return return_dict

def terascan_output(sock,
                    transmission_id=1,
                    operation=True,
                    delay=1,
                    update_step=1,
                    pause=False):
  """Configures Terascan automatic TCP/IP transmission during transmission

  Parameters:
    sock ~ Socket object to use
    transmission_id ~ (int) Arbitrary int to use for communications
    operation ~ (Boolean) True turns the feature on and False disables it
    delay ~ (int 1-1000) Scan delay after start transmission in 1/100s
    update_step ~ (int 0-50) Causes automatic output messges to be generated
                             the specified number of internal tuning DAC steps
                             have been made. i.e. higher number = less output
                             Note: setting to zero will disable mid scan
                             segment output.
    pause ~ (Boolean) True to enable the feature where the TeraScan will stop
                      after every message transmission of status "start" or
                      "repeat" and will continue upon transmission of a
                      terascan_continue command
    Returns:
      Nothing on successful call
    Raises:
      SolstisError if the command cannot be carried out
  """
  
  #Create message:
  if operation == True:
    operation = "start"
  else: 
    operation = "stop"

  if pause == True:
    pause = "on"
  else:
    pause  = "off"


  send_msg(sock,transmission_id,"terascan_output",{
                                  "operation": operation,
                                  "delay": [delay],
                                  "update": [update_step],
                                  "pause": pause})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op="terascan_output_reply")
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("Automatic Output Configuration failed")
  elif status == 2:
    raise SolstisError("Automatic Output failed; Delay period out of range")
  elif status == 3:
    raise SolstisError("Automatic Output failed; Update step out of range")
  else:
    raise SolstisError("TeraScan not available.")

def recv_auto_output(sock):
  """Receives an automatic message from the Solstis during a TeraScan
  
  Parameters:
    sock ~ Socket to use for communications
  Returns:
    A dictionary object containing the following key/value pairs:
      "wavelength" ~ The current wavelength reading in nm (between 650-1100)
      "status" ~ String being one of "start", "repeat", "recover", "scan", or
                 "end". See Solstis_3_TCP_JSON_protocol_V21.pdf for details
                 Note: If pausing is configured, then a contiue message must be
                 sent after reveiving any "start" or "repeat" values
  Raises:
    SolstisError on bad transmission
    TimeoutError when the socket times out
  """

  try:
    val = recv_msg(sock)
  except socket.timeout:
    raise TimeoutError
  verify_msg(val,op="automatic_output")
  status = val["message"]["parameters"]["status"]
  wavelength = val["message"]["parameters"]["wavelength"][0]

  return {"wavelength": wavelength, "status": status}

def terascan_continue(sock,transmission_id=1):
  """Instructs a paused terascan using automatic output to continue

  Parameters: 
    sock ~ Socket object to use for communications
    transmision_id ~ (int) arbitrary integer used for communications
  Returns:
    Nothing on valid execution
  Raises:
    SolstisError on operation failure
  """
  send_msg(sock,transmission_id,"terascan_continue")
  val = recv_msg(sock)
  verify_msg(val,op="terascan_continue_reply",transmission_id=transmission_id)
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("terascan_continue failed; TeraScan was not paused.")
  else:
    raise SolstisError("TeraScan is not available.")

def get_status(sock, transmission_id=1):
  """Retrieves the system status information available to the user

  Parameters:
    sock ~ Socket object to use
    transmission_id ~ (int) arbitrary integer to use for communications
  Returns:
    A dictionary containing the following key/value pairs:
      "status" ~ 0 on a succesful call, and 1 otherwise 
      "wavelength" ~ The current wavelength in nm
      "temperature" ~ Current temperature in degrees Celcius
      "temperature_status" ~ "on" or "off"
      "etalon_lock" ~ "on","off","debug","error","search" or "low". See Manual.
      "etalon_voltage" ~ Reading in Volts
      "cavity_lock" ~ "on","off","debug","error","search" or "low"
      "resonator_voltage" ~ Reading in Volts
      "ecd_lock" ~ "not_fitted","on","off","debug","error","search" or "low"
      "ecd_voltage" ~ Reading in Volts
      "output_monitor" ~ Reading in Volts
      "etalon_pd_dc" ~ Reading in Volts
      "dither" ~ "on" or "off"
  Raises:
    SolstisError on operation failure
  """

  send_msg(sock,transmission_id,"get_status")
  val = recv_msg(sock)
  verify_msg(val,op="get_status_reply",transmission_id=transmission_id)
  status = val["message"]["parameters"]["status"][0]
  if status == 1:
    raise SolstisError("get_status failed: reason unknown")
  params = val["message"]["parameters"]
  return_val = {"status": 0}
  return_val["wavelength"] = params["wavelength"][0]
  return_val["temperature"] = params["temperature"][0]
  return_val["temperature_status"] = params["temperature_status"]
  return_val["etalon_lock"] = params["etalon_lock"]
  return_val["etalon_voltage"] = params["etalon_voltage"][0]
  return_val["cavity_lock"] = params["cavity_lock"]
  return_val["resonator_voltage"] = params["resonator_voltage"][0]
  return_val["ecd_lock"] = params["ecd_lock"]
  if params["ecd_voltage"] == "not_fitted":
    return_val["ecd_voltage"] = -float('inf')
  else:
    return_val["ecd_voltage"] = params["ecd_voltage"][0]
  return_val["output_monitor"] = params["output_monitor"][0]
  return_val["etalon_pd_dc"] = params["etalon_pd_dc"][0]
  return_val["dither"] = params["dither"]

  return return_val

def tune_etalon(sock, setting, transmission_id=1):
  """Tunes the etalon to user-defined value

  Parameters:
    sock ~ Socket object to use for communications
    setting ~ (float) Percentage (0-100) of etalon range to go to
    transmission_id ~ (int) Arbitrary integer for communications
  Returns:
    Nothing on success
  Raises:
    SolstisError on failure to execute
  """

  send_msg(sock,transmission_id,"tune_etalon",{"setting": [setting]})
  val = recv_msg(sock)
  verify_msg(val,op="tune_etalon_reply",transmission_id=transmission_id)
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("Etalon Tuning value is out of range.")
  else:
    raise SolstisError("tune_etalon Failed; Reason Unknown")

def tune_resonator(sock, setting, transmission_id=1):
  """Tunes the resonator to user-defined value

  Parameters:
    sock ~ Socket object to use for communications
    setting ~ (float) Percentage (0-100) of resonator range to go to
    transmission_id ~ (int) Arbitrary integer for communications
  Returns:
    Nothing on success
  Raises:
    SolstisError on failure to execute
  """

  send_msg(sock,transmission_id,"tune_resonator",{"setting": [setting]})
  val = recv_msg(sock)
  verify_msg(val,op="tune_resonator_reply",transmission_id=transmission_id)
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("Resonator Tuning value is out of range.")
  else:
    raise SolstisError("tune_resonator Failed; Reason Unknown")

def fine_tune_resonator(sock, setting, transmission_id=1):
  """Fine-Tunes the resonator to user-defined value

  Parameters:
    sock ~ Socket object to use for communications
    setting ~ (float) Percentage (0-100) of resonator fine-tuning range to go to
    transmission_id ~ (int) Arbitrary integer for communications
  Returns:
    Nothing on success
  Raises:
    SolstisError on failure to execute
  """

  send_msg(sock,transmission_id,"fine_tune_resonator",{"setting": [setting]})
  val = recv_msg(sock)
  verify_msg(val,op="fine_tune_resonator_reply",transmission_id=transmission_id)
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("Resonator Fine-Tuning value is out of range.")
  else:
    raise SolstisError("fine_tune_resonator Failed; Reason Unknown")

def etalon_lock(sock,lock,transmission_id=1):
  """Either locks or unlocks the etalon

  Parameters:
    sock ~ Socket object to use for communications
    lock ~ (Boolean) True to lock the etalon, False to unlock it 
    transmission_id ~ (int) arbitrary integer for use in communications
  Returns:
    Nothing on success
  Raises:
    SolstisError on failure
  """

  if lock == True:
    lock = "on"
  else:
    lock = "off"

  send_msg(sock,transmission_id,"etalon_lock",{"operation": lock})
  val = recv_msg(sock)
  verify_msg(val,op="etalon_lock_reply",transmission_id=transmission_id)
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  else:
    raise SolstisError("etalon_lock Failed; Reason Unknown")

def fast_scan_start(sock,
                    scan_type="etalon_continuous",
                    width=0.01,
                    time=0.01,
                    transmission_id=1):
  """Starts a Fast scan centered at the current set wavelength

  Parameters:
    sock ~ Socket object to use for communications
    scan_type ~ One of: "etalon_continuous", "etalon_single",
                        "cavity_continuous", "cavity_single",
                        "resonator_continuous", "resonator_single",
                        "ecd_continuous", "fringe_test", "resonator_ramp",
                        "ecd_ramp", "cavity_triangular", "resonator_triangular"
                        See Manual for details
    width ~ (float) Width of scan about center frequency in GHz
    time ~ (float) Duration of scan in seconds. Will ramp at max speed if time
           segment is too small.
    transmission_id ~ (int) Arbitrary integer for use in communications
  Returns:
    Nothing on a succesful execution
  Raises:
    SolstisError on failed execution
  """

  send_msg(sock,transmission_id,"fast_scan_start",
                                {"scan": scan_type,
                                 "width": width,
                                 "time": time} )
  val = recv_msg(sock)
  verify_msg(val,op="fast_scan_start_reply",transmission_id=transmission_id)
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("Fast Scan Failed: Scan width too large for position")
  elif status == 2:
    raise SolstisError("Fast Scan Failed: No reference cavity fitted")
  elif status == 3:
    raise SolstisError("Fast Scan Failed: no ERC fitted")
  elif status == 4:
    raise SolstisError("Fast Scan Failed: Invalid Scan Type requested")
  else:
    raise SolstisError("Fast Scan Failed: Time > 10000 seconds")

def fast_scan_poll(sock, scan_type="etalon_continuous", transmission_id=1):
  """Polls a currently running fast scan.

  Parameters:
    sock ~ Sock object to use for communications
    scan_type ~ One of: "etalon_continuous", "etalon_single",
                        "cavity_continuous", "cavity_single",
                        "resonator_continuous", "resonator_single",
                        "ecd_continuous", "fringe_test", "resonator_ramp",
                        "ecd_ramp", "cavity_triangular", "resonator_triangular"
                        See Manual for details
    transmission_id ~ (int) Arbitrary integer to use for communications
  Returns:
    Tuple containing (in increasing index order):
      -floating point value representing the current tuner value
      -Boolean stating whether tuning is done/inactive (True = Not tuning)
  Raises:
    SolstisError on execution failure
  """

  send_msg(sock,transmission_id,"fast_scan_poll",{"scan": scan_type})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op="fast_scan_poll_reply")
  status = val["message"]["parameters"]["status"][0]
  tuner_value = val["message"]["parameters"]["tuner_value"][0]
  if status == 1:
    status = False
  else:
    status = True
  return (tuner_value,status)

def fast_scan_stop(sock,scan_type="etalon_continuous",transmission_id=1):
  """Stops a fast-scan in progress

  Parameters:
    sock ~ Sock object to use for communications
    scan_type ~ One of: "etalon_continuous", "etalon_single",
                        "cavity_continuous", "cavity_single",
                        "resonator_continuous", "resonator_single",
                        "ecd_continuous", "fringe_test", "resonator_ramp",
                        "ecd_ramp", "cavity_triangular", "resonator_triangular"
                        See Manual for details
    transmission_id ~ (int) Arbitrary integer to use for communications
  Returns:
    Nothing on successful execution
  Raises:
    SolstisError on failed execution
  """

  send_msg(sock,transmission_id,"fast_scan_stop",{"scan": scan_type})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op="fast_scan_stop_reply")
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("fast_scan_stop Failed; Cause unknown")
  elif status == 2:
    raise SolstisError("fast_scan_stop Failed; Reference Cavity not fitted.")
  elif status == 3:
    raise SolstisError("fast_scan_stop Failed; ECD not fitted.")
  else:
    raise solstisError("fast_scan_stop Failed; Invalid Scan Type.")

def fast_scan_stop_nr(sock,scan_type="etalon_continuous",transmission_id=1):
  """Stops a fast-scan in progress without returning to the original position

  Parameters:
    sock ~ Sock object to use for communications
    scan_type ~ One of: "etalon_continuous", "etalon_single",
                        "cavity_continuous", "cavity_single",
                        "resonator_continuous", "resonator_single",
                        "ecd_continuous", "fringe_test", "resonator_ramp",
                        "ecd_ramp", "cavity_triangular", "resonator_triangular"
                        See Manual for details
    transmission_id ~ (int) Arbitrary integer to use for communications
  Returns:
    Nothing on successful execution
  Raises:
    SolstisError on failed execution
  """

  send_msg(sock,transmission_id,"fast_scan_stop_nr",{"scan": scan_type})
  val = recv_msg(sock)
  verify_msg(val,transmission_id=transmission_id,op="fast_scan_stop_nr_reply")
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("fast_scan_stop_nr Failed; Cause unknown")
  elif status == 2:
    raise SolstisError("fast_scan_stop_nr Failed; Reference Cavity not fitted.")
  elif status == 3:
    raise SolstisError("fast_scan_stop_nr Failed; ECD not fitted.")
  else:
    raise solstisError("fast_scan_stop_nr Failed; Invalid Scan Type.")

def set_wave_tolerance_m(sock,tolerance=1.0,transmission_id=1):
  """Sets the tolerance for the sending of the set_wave_m final report

  Parameters:
    sock ~ Socket object to use for communications
    tolerance ~ (float) New tolerance value
    transmission_id ~ (int) Arbitrary integer for use in communications
  Returns:
    Nothing on successful execution
  Raises:
    SolstisError on failed execution
  """
  send_msg(sock,transmission_id,"set_wave_tolerance_m",{"tolerance": tolerance})
  val = recv_msg(sock)
  verify_msg(val,
             transmission_id=transmission_id,
             op="set_wave_tolerance_m_reply")
  status = val["message"]["parameters"]["status"][0]
  if status == 0:
    return
  elif status == 1:
    raise SolstisError("Could not set tolerance; No wavemeter connected")
  else:
    raise SolstisError("Could not set tolerance; Tolerance Value Out of Range")
