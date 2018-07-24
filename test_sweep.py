from solstis_functions import *
import time
import numpy as np
import matplotlib.pyplot as plt

#User chosen parameters
START_WAVELEN = 775.5 #Scan's starting wavelength
END_WAVELEN = 780.5 #Scan's ending wavelength
NUM_STEPS = 51 #Number of points in scan
DELAY = 0.00 #Delay between scan simultaneous settings/measurements

#Create our socket using default params
sock = init_socket()

#Create arrays and things necessary to carry out a sweep
wavelengths = np.linspace(START_WAVELEN,END_WAVELEN,num=NUM_STEPS)
times = np.zeros(len(wavelengths))
wavelengths_measured = np.zeros(len(wavelengths))
init_time = 0

#Start link
start_link(sock)

#Set wavelength to initial value
set_wave_m(sock,START_WAVELEN)

#Wait to attain this initial value
while True:
  poll = poll_wave_m(sock)
  if poll[1] == True:
    init_time = time.perf_counter()
    wavelengths_measured[0] = poll[0]
    times[0] = time.perf_counter() - init_time
    break

print("Initial value attained")

#Set and measure all remaining states
for i in range(1,len(wavelengths)):
# time.sleep(DELAY)
# times[i] = time.perf_counter() - init_time
  wavelengths_measured[i] = set_wave_m_f_r(sock,wavelengths[i])
  print("Progress: ",float(i)/float(NUM_STEPS))
  time.sleep(DELAY)
  while True:
    poll = poll_wave_m(sock)
    if poll[1] == True:
      wavelengths_measured[i] = poll[0]
      times[i] = time.perf_counter() - init_time
      break

#Plot the data
fig, ax1 = plt.subplots()
ax1.plot(times,wavelengths,'r.')
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Set Wavelength (nm)')
plt.ylim(START_WAVELEN,END_WAVELEN)

ax2 = ax1.twinx()
ax2.plot(times,wavelengths_measured,'b.')
ax2.set_ylabel('Measured Wavelength (nm)')
plt.ylim(START_WAVELEN,END_WAVELEN)

plt.tight_layout()
plt.show()
