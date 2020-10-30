#!/bin/bash

# set home dir and mark the start of a new logging run
cd /home/pi/Documents/SRP_RI/
date >> /home/pi/Documents/SRP_RI/run.log

# start gpio stuff and check pin 22 breakwire state
sudo pigpiod
if [ "$1" == "-f" ]; then
    breakwire=1
elif [ "$1" == "-r" ]; then
    breakwire=0
else
    echo "no flag given, checking breakwire"
    pigs modes 22 r
    pigs pud 22 u
    breakwire=$(pigs r 22)
    pigs pud 22 o
fi

# start different scripts based on breakwire state
if [ $breakwire -eq 1 ]; then  # if the breakwire pin is floating high
    echo "starting flight script"
    /usr/bin/python3 /home/pi/Documents/SRP_RI/flight/fly.py 2>>/home/pi/Documents/SRP_RI/run.log
elif [ $breakwire -eq 0 ]; then  # if the breakwire pin is pulled to ground
    echo "starting remote control script"
    /usr/bin/python3 /home/pi/Documents/SRP_RI/remote_control/index.py 2>>/home/pi/Documents/SRP_RI/run.log #2>/dev/null
fi
exitcode=$?  # record the exit code of the script

# clean up and shutdown pi in case the script exited with 13
sudo killall pigpiod
if [ $exitcode -eq 13 ]; then
    echo "power off in 15s"
    sleep 15
    echo "power off now"
    sudo poweroff
fi
