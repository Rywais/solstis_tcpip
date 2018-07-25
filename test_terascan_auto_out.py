#!/usr/bin/python3
# This code is purposed to test a TeraScan WITH Live Feedback and optional
# pausing

from solstis_functions import *
import time
import numpy as np
import matplotlib.pyplot as plt

#User Parameters:
PAUSE = False
PAUSE_DELAY = 0.0
START = 777.5
STOP = 779.5
FILE_SUFFIX = "scan_15"

#Initialize socket
sock = init_socket()

#Start Link
start_link(sock)

#Initialize TeraScan
scan_stitch_initialize(sock,TeraScan.SCAN_TYPE_FINE,START,STOP,
                            TeraScan.SCAN_RATE_FINE_LINE_5_GHZ)

#Configure the Automantic Output
terascan_output(sock,
                transmission_id=1,
                operation=True,
                delay=1,
                update_step=1,
                pause=PAUSE)

#Variables for later graphing
times = np.array([])
wavelength = np.array([])
init_time = time.perf_counter()

#Start the scan
scan_stitch_op(sock, TeraScan.SCAN_TYPE_FINE, "start")

while True:
  try:
    val = recv_auto_output(sock)
  except:
    break
  print("status: ",val["status"])
  wavelength = np.append(wavelength,val["wavelength"])
  times = np.append(times,time.perf_counter()-init_time)
  if val["status"] == "end" and val["wavelength"] >= STOP:
    break
  if PAUSE==True and (val["status"] == "start" or val["status"] == "repeat"):
    time.sleep(PAUSE_DELAY)
    terascan_continue(sock,transmission_id=1)

fig, ax = plt.subplots()
ax.plot(times,wavelength,'bo')
ax.set_title("Wavelengths Over Time of TeraScan")
plt.show()

np.savetxt("times_"+FILE_SUFFIX+".txt",times)
np.savetxt("wavelength_"+FILE_SUFFIX+".txt",wavelength)
