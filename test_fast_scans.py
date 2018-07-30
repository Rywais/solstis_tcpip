#!/usr/bin/python3
# This code should test the operation of Solstis fast scans

import time
from solstis_functions import *
import numpy as np
import matplotlib.pyplot as plt

#User Parameters
START_WAVELEN = 775.5
END_WAVELEN = 780.5
GHZ_SPACING = 200
SCAN_SPACING = 200
SCAN_TIME = 0.01

#Create Function to convert between nm and GHz
def nm_to_ghz(wavelen):
  return (299792458/(wavelen))

def ghz_to_nm(freq):
  return (299792458/(freq))

#Initialize Socket
sock = init_socket()

#Start Link
start_link(sock)

#Set the tolerance for the Solstis to increase execution speed
set_wave_tolerance_m(sock,tolerance=0.01)

#Create the list of center points about which to scan
freqs = np.arange(nm_to_ghz(START_WAVELEN),nm_to_ghz(END_WAVELEN),GHZ_SPACING)

#Create plotting variables
wavelens = [[0,0]]*len(freqs)
times = [[0,0]]*len(freqs)

init_time = time.perf_counter()

for i in range(len(freqs)):
  set_wave_m_f_r(sock,ghz_to_nm(freqs[i]))
  fast_scan_start(sock,scan_type="etalon_continuous",width=SCAN_SPACING,
                  time=SCAN_TIME)
  #Wait to confirm fast scan has started
  while True:
    val = fast_scan_poll(sock,scan_type="etalon_continuous")
    if val[1] == False:
      break

  wavelens[i][0] = ghz_to_nm(freqs[i]-SCAN_SPACING/2)
  times[i][0] = time.perf_counter() - init_time

  #Wait for scan to end
  while True:
    val = fast_scan_poll(sock,scan_type="etalon_continuous")
    if val[1] == False:
      break

  wavelens[i][1] = ghz_to_nm(freqs[i]-SCAN_SPACING/2)
  times[i][1] = time.perf_counter() - init_time

plt.figure()
for i in range(len(freqs)):
  plot( (times[i][0],times[i][1]),(wavelens[i][0],wavelens[i][1]) )

plt.show()
