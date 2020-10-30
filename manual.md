# SRP_RI user manual

In this document you can find information on the preparation, launch procedure and data recovery. Additionaly, it describes the expected behaviour of the rocket, so you can test it if necessary.

## Preparation

Preparing the electronics for flight only requires the insertion of the 9V battery, and then screwing the top section shut. <!--- If you want, you can check the functionality by turning on the rocket and testing the statemachine, which is described in [this section](#tbd) -->

Before flying the rocket, the parachute must be packed in the parachute compartment in the following manner: TBD TBD...
To close the hatch, carefully push the servo arm to a straight down position, and slide the hatch on from the right (the servo arm doesn't have to be perfectly aligned, as it will move itself shut when the electronics are started up). To be sure it won't open accidentally before the launch, tie a rubber band or similar around the rocket. This will also keep the hatch closed in case the servo moves when the rocket starts up.

## Launch procedure

- Verify that you have the rocket fully prepared, with the battery inserted and the parachute packed in the closed compartment.
- Check that the breakwire is **disconnected**
- Once the rocket is in the tower, switch it on by flipping the bottom switch down, and wait for it to beep short twice, indicating that it has successfully booted up and has started the flight software. The rocket is now in IDLE mode (with the status LED being solid green).
- Fasten the breakwire to the launch tower and insert it into the connector that is dangling on the outside of the rocket (the wires are black and white). Once you have done so, the rocket progresses from IDLE to PREPARED, as you can hear from the double short beep. The status LED should now be solid blue.
  - If this does not happen, check that the arm switch is in the off position.
- Once you are ready to arm the rocket, do so by flipping the top switch down. The status LED should start blinking blue (and beep short twice), indicating that the sensors are being calibrated. This calibration takes about 30 seconds, after which the LED turns solid red. Now the rocket is waiting for the breakwire to get pulled out at launch, so you can run away in a safe but distinctive manner.

Note: all actions required to progress through the state machine, also act in reverse: if you need to disarm the rocket, do so by flipping the arm switch (top one) up. You can go back from PREPARED into IDLE similarly, namely by pulling out the breakwire. These "setbacks" in the statemachine are audibly accompanied by a long beep.

## Recovering the data after landing

Once you get the rocket back from the field, check whether the arm and power switch are still on. The white light should be on, indicating that the rocket has finished saving the data. If so, then the rocket should be using its beeper to output the apogee altitude (in meters) according to the following binary encoding<!--,
borrowed from the [PerfectFlite Stratologger](http://www.perfectflite.com/Downloads/StratoLoggerCF%20manual.pdf):-->

### Apogee readout

<!--Digits, as defined in the table below, are separated from the other digits in the number by a long beep,
and the whole number is repeated after a long pause.

Digit | Pattern
----- | -----------
0     | beep-beep-beep-beep-beep-beep-beep-beep-beep-beep
1     | beep
2     | beep-beep
3     | beep-beep-beep
4     | beep-beep-beep-beep
5     | beep-beep-beep-beep-beep
6     | beep-beep-beep-beep-beep-beep
7     | beep-beep-beep-beep-beep-beep-beep
8     | beep-beep-beep-beep-beep-beep-beep-beep
9     | beep-beep-beep-beep-beep-beep-beep-beep-beep
-->

The integer number is beeped out in binary, where a long beep (ca 0.8 seconds) stand for a 1 and a short beep (ca 0.4 seconds) stands for 0. In the table you can see some example numbers:

Pattern     | Calculation                                                                   | Number
----------- | ----------------------------------------------------------------------------- | ------
--.         | `1*4 + 1*2 + 0*1`                                                             | 6
-.--..-.-.  | `1*512 + 0*256 + 1*128 + 1*64 + 0*32 + 0*16 + 1*8 + 0*4 + 1*2 + 0*1`          | 714
-..--.-..-. | `1*1024 + 0*512 + 0*256 + 1*128 + 1*64 + 0*32 + 1*16 + 0*8 + 0*4 + 1*2 + 0*1` | 1234

After you have taken note of this number, disarm the rocket by flipping up the arm switch. This will cause the rocket to power itself down in a controlled fashion. After about 30 seconds, you can switch off the power as well, and proceed with extracting the battery and cleaning up/documenting the mess/success.

If the arm switch is already off while the power switch is still on, the rocket has powered off itself when it was disarmed after landing. You can safely flip up (switch off) the power switch, and proceed like described in the paragraph above.

If both the arm and power switch are already off, it is possible that the rocket has experienced a sudden poweroff.
There's nothing you can do about it now, other than proceeding like described above, and maybe making an image of the SD card first before powering on the Raspberry Pi again.

### Extracting the data

Once you have secured the SD card, you can use any Raspberry Pi to boot from that SD card. There are various ways of extracting the data, depending on how much is left of the rocket. If the entire electronics are intact, you can simply insert the SD card and follow the easy way. If troubles arise and the easy way doesn't work, you can still download the data manually via the hard way.

#### Connection

To download the data we need some kind of connection. The raspberry pi os on the SD card is set up to search for a hotspot of the name `[redacted]`, with the code `[redacted]`. (This usually is my laptop, but if you need to do it yourself, you can set up a hotspot with these parameters). If it does not find this network, it will set up an open hotspot of its own, called `SRPi`.

#### The easy way

If you boot up the raspi with [GPIO pin 22](https://pinout.xyz/pinout/pin15_gpio22) pulled to ground, which is what the breakwire does if you connect the two ends, it starts the remote control script (if you are using the spare RPi, I have made the black jumper that can jump pin BCM22 (board15) diagonally to ground at board14). When you are connected to the raspi's hotspot, browse to http://10.0.0.5:5000. If it is connected to your hotspot, look up its IP and browse to it at port 5000. There you will find the remote control web interface, at the bottom of which you'll find a selector input to select which log you want to download, and a button to do so. This will download a zipfile with all the data and logs from that timestamp for you.

#### The hard way

As soon as the Raspberry Pi connects to your hotspot, you can extract all data from it by running this command from the shell:
`scp pi@[IP_ADDRESS]:~/Documents/SRP_RI/data ./`
(replace `[IP_ADDRESS]` by the IP address of the Raspberry Pi, which you can find on the settings page for the hotspot).
The pw you need to enter is team_reimagined, belonging to the user pi on the Raspberry Pi.
This will transfer the entire `data` folder to your current working directory, from where you can save it, upload it or post-process it.
