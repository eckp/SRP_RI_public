Note: this public repo is a redacted copy of my private working version, so sadly no commit history is available.
**For the original flight software and flight data of SRP Separation Anxiety, our first attempt, see https://github.com/eckp/SRP_SA**

# SRP_RI

This repo hosts the progams used for the SRP:RI project. 
In the `flight` folder, the flight software can be found (`fly.py` being the main script), 
whereas the groundstation scripts (e.g. `post.py` for post-processing and analysis of the data) are collected in `ground`.
The data/log files are written to and read from the top level `data` folder, but the folder itself is not tracked.

## Flight software

The flight software is started by the `run.sh` script when you boot up with the breakwire leads disconnected. Alternatively you can call `run.sh -f` to override the gpio check.

### Pin allocations

Allocation | Designation | Left | Right | Designation | Allocation
---------- | ----------- | ---- | ----- | ----------- | ----------
AltIMU Vin | 3V3         | 1    | 2     | 5V          | RGB LED anode
AltIMU SDA | BCM 2       | 3    | 4     | 5V          | Power regulator input
AltIMU SCL | BCM 3       | 5    | 6     | Ground      | Power regulator ground
Hatch servo| BCM 4       | 7    | 8     | BCM 14      | 
Buzzer GND | Ground      | 9    | 10    | BCM 15      | 
Buzzer     | BCM 17      | 11   | 12    | BCM 18      | Blue LED
Arm switch | BCM 27      | 13   | 14    | Ground      | AltIMU GND
Breakwire  | BCM 22      | 15   | 16    | BCM 23      | Green LED
&nbsp;     | 3V3         | 17   | 18    | BCM 24      | Red LED
&nbsp;     | BCM 10      | 19   | 20    | Ground      | RGB LED GND
&nbsp;     | BCM 9       | 21   | 22    | BCM 25      | 
&nbsp;     | BCM 11      | 23   | 24    | BCM 8       | 
Arm switch GND| Ground      | 25   | 26    | BCM 7       | 
&nbsp;     | BCM 0       | 27   | 28    | BCM 1       | 
&nbsp;     | BCM 5       | 29   | 30    | Ground      | Breakwire GND
&nbsp;     | BCM 6       | 31   | 32    | BCM 12      | 
&nbsp;     | BCM 13      | 33   | 34    | Ground      | 
&nbsp;     | BCM 19      | 35   | 36    | BCM 16      | 
&nbsp;     | BCM 26      | 37   | 38    | BCM 20      | 
&nbsp;     | Ground      | 39   | 40    | BCM 21      | 


### Dependencies
not really significant (yet?)
- gpiozero (1.5.0)
- altered [altimu10v5](https://github.com/SvetoslavKuzmanov/altimu10v5)
  - alternative could be [this](https://github.com/tkurbad/mipSIE/tree/master/python/AltIMU-10v5) module. It has a readout for the temperature data of the various sensors
- matplotlib (3.0.3)
  - numpy (1.18.1)


### Data files format

CSV file contains the acquired data in the following format:
```
[data point number, ]timestamp, datapointX[, datapointY, datapointZ]
#comment
```
The data point number was included for some time but has been removed for consistency with other log files. The timestamp being the first float in the row should make it obvious which format was used.

### Sensors
#### Configuration
The sensors can be set to different scales and speeds, by setting registers to the following values:
The default values (at least, those that came with the module) are listed as the first entry for each register, and the other values are other configurations allowing for better precision, readout rate or range.

Sensor     | Register name | Register address | Value      | Setting
---------- | ------------- | ---------------- | ---------- | -------
LPS25H     | CTRL_REG1     | 0x20             | 0b10110000 | active; 12.5Hz; no interrupt; continuous update; disable autozero; 4-wire interface
&nbsp;     | &nbsp;        | &nbsp;           | 0b11000000 | active; 25Hz; idem
LIS3MDL    | CTRL_REG1     | 0x20             | 0b01110000 | temperature disabled; 10Hz; self-test disabled
&nbsp;     | &nbsp;        | &nbsp;           | 0b11100010 | temperature enabled; 155Hz (Ultra-high-performance XY axis for best precision); self-test disabled
&nbsp;     | CTRL_REG2     | 0x21             | 0b00000000 | +-4 gauss; normal mode
&nbsp;     | &nbsp;        | &nbsp;           | 0b0..00000 | replace .. by 01 for +-8 gauss, 10 for +-12 gauss or 11 for +-16 gauss
&nbsp;     | CTRL_REG3     | 0x22             | 0b00000000 | low-power disabled; 4-wire interface; continuous-conversion mode (because Fast-ODR is used in CTRL_REG1)
&nbsp;     | &nbsp;        | &nbsp;           | 0b00000011 | power-down mode
&nbsp;     | CTRL_REG4     | 0x23             | 0b00001100 | Ultra-high-performance mode for Z axis; Little Endian data
LSM6DS33   | CTRL1_XL      | 0x10             | 0b01011000 | 208Hz accelerometer; +-4g; antialiasing filter bandwidth 400Hz
&nbsp;     | &nbsp;        | &nbsp;           | 0b....,,00 | replace .... by 0000 for power-down, 0001 for 13Hz, 0010 for 26Hz, 0011 for 52Hz, 0100 for 104Hz, 0101 for 208Hz, 0110 for 416Hz, 0111 for 833Hz, 1000 for 1660Hz, 1001 for 3330Hz, 1010 for 6660Hz; replace ,, by 00 for +-2g, 10 for +-4g, 11 for +-8g, 01 for +-16g
&nbsp;     | CTRL2_G       | 0x11             | 0b01011000 | 208Hz gyroscope; 1000 dps; extra low scale disabled
&nbsp;     | &nbsp;        | &nbsp;           | 0b....,,00 | same as accelerometer ODR; replace ,, by 00 for 245 dps, 01 for 500 dps, 10 for 1000 dps, 11 for 2000 dps; second-to-last bit set to 1 enables 125 dps mode, so very small scale, giving extra resolution
&nbsp;     | CTRL6_C       | 0x15             | 0b00000000 | enable high-performance mode for accelerometer
&nbsp;     | CTRL7_G       | 0x16             | 0b00000000 | enable high-performance mode for gyroscope
&nbsp;     | FIFO_CTRL5    | 0x0A             | 0b00000000 | disable FIFO, should already be disabled by default...

#### Conversion
The raw data from each sensor can be converted from least-significant-bits (LSB) to the appropriate units, using the following formulas:
##### LPS25H
```
p [Pa] = PRESS_OUT/40.96
T [C] = 42.5 + TEMP_OUT/480
```
##### LIS3MDL
```
B [gauss] = OUT/6842 if range was +-4 gauss, OUT/3421 if range was +-8 gauss, OUT/2281 if range was +-12 gauss, OUT/1711 if range was +-16 gauss
T [C] = TBD_OFFSET (25?) + OUT/8
```

##### LSM6DS33
```
a [g] = OUT*61E-6 if range was +-2 g, OUT*122E-6 if range was +-4 g, OUT*244E-6 if range was +-8 g, OUT*488E-6 if range was +-16 g
r [dps] = OUT*4375E-6 if range was +-125 dps, OUT*8750E-6 if range was +-245 dps, OUT*17500E-6 if range was +-500 dps, OUT*35E-3 if range was +-1000 dps, OUT*70E-3 if range was +-2000 dps
T [C] = 25 + OUT/16
```

## Ground software
TBD

## Remote control
This web-interface, launched when the breakwire is inserted (or with `run.sh -r` to override the gpio check), allows control over the parachute hatch servo.
It is meant to facilitate easy testing without having to run through the entire state machine or having to log on for manual control.

To access the web page, boot up the pi with the breakwire leads shorted and make sure it either finds a known wifi network, or log into its own hotspot, called SRPi using the code `[redacted]`. 
Then navigate to either http://10.0.0.5:5000 (in case of the Pi being the hotspot) or find the Pi's IP address and navigate to port 5000. There you'll find the web page to control the servo.
