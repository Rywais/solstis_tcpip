#!/usr/bin/python3
# This code logs the Photodiode output data from the Solstis periodically

#User parameters
PERIOD = 1 #Seconds
SAVE_EVERY_N_SAMPLES = 10
DATAFILE = 'PD_output'

from solstis_functions import *
import time
import numpy as np
import matplotlib.pyplot as plt

#Initialize socket
sock = init_socket()

#Start Link
start_link(sock,ip_address='192.168.1.100')

#Initialize variables
i = 0
data = np.array([])
data_t = np.array([])

#Start Loop
try:
  init_time = time.perf_counter()
  while True:
    val = get_status(sock)
    data = np.append(data,val["output_monitor"])
    data_t = np.append(data_t,time.perf_counter()-init_time)
    print(val["output_monitor"], ", Press ctrl+C to terminate the program.")
    i += 1
    if i % SAVE_EVERY_N_SAMPLES == 0:
      np.savetxt(DATAFILE+'.npy',data)
      np.savetxt(DATAFILE+"_t.npy",data_t)
    time.sleep(PERIOD)
except KeyboardInterrupt:
  np.savetxt(DATAFILE,data)
  np.savetxt(DATAFILE+"_t",data_t)
  
