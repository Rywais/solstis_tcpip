#!/usr/bin/python3
# This code is purposed to test a TeraScan WITHOUT the live feedback and no
# pausing

from solstis_functions import *
import time
import numpy as np
import matplotlib.pyplot as plt

#Initialize socket
sock = init_socket()

#Start Link
start_link(sock)

#Initialize TeraScan
scan_stitch_initialize(sock,TeraScan.SCAN_TYPE_MEDIUM,775.5,780.5,
                            TeraScan.SCAN_RATE_MEDIUM_100_GHZ)
#Start the scan
scan_stitch_op(sock, TeraScan.SCAN_TYPE_MEDIUM, "start")

#Variables for later graphing
times = np.array([])
wavelength = np.array([])
init_time = time.perf_counter()

while True:
  val = scan_stitch_status(sock,TeraScan.SCAN_TYPE_MEDIUM)
  if val["in_progress"] == False:
    break
  
  wavelength = np.append(wavelength,val["wavelength"])
  times = np.append(times,time.perf_counter()-init_time)

fig, ax = plt.subplots()
ax.plot(times,wavelength,'bo')
ax.set_title("Wavelengths Over Time of TeraScan")
plt.show()
