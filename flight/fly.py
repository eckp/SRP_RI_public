#!/usr/bin/python3

'''SRP_RI main flight software

Logs data and actuates deployment of the SRP Reimagined rocket
'''

########################################
# imports
import os
# set working directory to the location of this script for the sensor module imports to work
workdir = '/'.join(os.path.realpath(__file__).split('/')[:-1])+'/'  # only meant for unix-type file systems
os.chdir(workdir)
import sys
import shutil
import time
import math
import csv
import logging
import threading
import subprocess
import altimu10v5
import dummy
from config import Config
# use different pin_factory for the servo to prevent jittering
# requires 'sudo pigpio' to be run before this script
from gpiozero.pins.pigpio import PiGPIOFactory
import gpiozero

import pyprofile
pf = pyprofile.Profiler()

########################################
# definitions

# state variables
state = 'IDLE'
last_state = 'OFF'
p = [0, 0]  # last two pressure values
h = [0, 0]  # last two altitude values
v = [0, 0]  # last two velocity values
# reference variables
p0 = None
flight_start = None
apogee = 0

conf = Config('config.json')

########################################
# state machine functions

@pf.profile
def update_statemachine():
    '''Execute the actions in the flight loop depending on the current state.
    Change the state depending on conditions given in state diagram.
    Also execute any actions when transitioning between states.
    '''
    global state, last_state, flight_start  # making a State class could make this neater
    t = time.time()  # eliminates the many calls to time.time() whenever it is used

    if state == 'IDLE':
        if last_state != state:
            hatch.value = conf.hatch_closed
            status_LED.color = conf.green
            last_state = state
        # to prevent the statemachine from then immediately going to ARMED,
        # TODO: solve this in a nicer way if possible, maybe by warning if arm_switch is on in IDLE
        if breakwire.value and not arm_switch.value:
            # put stuff to be executed on changing from IDLE to PREPARED here
            buzzer.progress()
            state = 'PREPARED'

    elif state == 'PREPARED':
        if last_state != state:
            status_LED.color = conf.blue
            last_state = state
        if not breakwire.value:
            buzzer.setback()
            state = 'IDLE'
        elif arm_switch.value:
            buzzer.progress()
            state = 'ARMED'

    elif state == 'ARMED':
        if last_state != state:
            last_state = state
            if not imu.enabled:
                status_LED.default_blink(on_color=conf.blue)
                imu.enable()
                imu.calibrate()
                global p0, p
                p0s = []
                for i in range(50):
                    p0s.append(imu.lps25h.get_barometer_raw()/40.96)
                p0 = sum(p0s)/len(p0s)
                p = [p0]*2
                logger.debug('Sensor calibration finished, starting threads now')
                for sensor in sensors:
                    sensor.start_thread()
            status_LED.color = conf.red
        if not arm_switch.value:
            buzzer.setback()
            state = 'PREPARED'
        elif not breakwire.value:
            buzzer.progress()
            state = 'LAUNCHED'

    elif state == 'LAUNCHED':
        if last_state != state:
            status_LED.default_blink(on_color=conf.red, off_color=conf.green)
            last_state = state
            flight_start = t
        if ((t > flight_start+conf.deploy_window[0])\
            and (h[1]<conf.deploy_altitude and v[1]<conf.deploy_velocity))\
           or (t > flight_start+conf.deploy_window[1]):
            hatch.value = conf.hatch_open
            buzzer.progress()
            state = 'DEPLOYED'

    elif state == 'DEPLOYED':
        if last_state != state:
            status_LED.default_blink(on_color=conf.red, off_color=conf.blue)
            last_state = state
        if ((t > flight_start+conf.landing_window[0])\
            and (conf.landing_altitude_range[0]<h[1]<conf.landing_altitude_range[1]\
                 and conf.landing_velocity_range[0]<v[1]<conf.landing_velocity_range[1]))\
           or (t > flight_start+conf.landing_window[1]):
            buzzer.progress()
            state = 'LANDED'

    elif state == 'LANDED':
        if last_state != state:
            status_LED.default_blink(on_color=conf.green, off_color=conf.blue)
            # landing routine:
            time.sleep(5)
            stop.set()
            for sensor in sensors:
                try:
                    sensor.save()
                except (AttributeError, ValueError) as e:
                    logger.warning('Saving the last data failed, because the csv file was not opened',
                                   exc_info=False)
            for sensor in sensors:
                try:
                    sensor.thread.join()
                except AttributeError as e:
                    logger.warning('Joining the sensor threads failed, because they were not created/started',
                                   exc_info=False)
            last_state = state
            status_LED.color = conf.white
        if not arm_switch.value:
            buzzer.progress()
            state = 'OFF'
            logger.info('{} to {}'.format(last_state, state))  # needs to be repeated here, because the function will return before reaching the end
            return 'stop'
        else:
            buzzer.beep_out(int(apogee))

    else:
        logger.warning('State variable is {}, matching no existing state. Going to do TBD now'.format(state))
        # what to do when state is messed up?
    if last_state != state:
        status_LED.off()
        logger.info('{} to {}'.format(last_state, state))


########################################
# sensor/IO functions/classes

class BeepingTonalBuzzer(gpiozero.TonalBuzzer):
    def beep(self, on_time=1, off_time=1, n=None, tone=None, background=True):
        '''Patch a beeping functionality similar to the normal Buzzer into TonalBuzzer.'''
        value = (math.log2(gpiozero.tones.Tone(tone).frequency/self.mid_tone.frequency)/self.octaves if tone else 0)
        def square_wave(on, off, timestep, num=None):
            t = 0
            while (num is None) or (t//(on+off) < num):
                yield (value if t%(on+off)<=on else None)
                t += timestep
            yield None
            return
        self.source = square_wave(on_time, off_time, self.source_delay, n)
        if (not background) and n:
            time.sleep((on_time+off_time)*n)  # block for the time that it takes square_wave to finish the n beeps

    def progress(self):
        '''Beep the pattern for making progress in the statemachine.'''
        self.beep(conf.beep_period/2, conf.beep_period/2, n=2, background=False)

    def setback(self):
        '''Beep the pattern for a setback in the statemachine.'''
        self.beep(3*conf.beep_period/2, conf.beep_period/2, n=1, background=False)

    def beep_out(self, num, dot=0.3, dash=0.6, pause=5):
        '''Beep a given number in binary morse. 0 is 1 'dot' seconds, 1 is dash 'dash' time, separated by 1 'dot' silence. The pause between repeats is 'pause' seconds silence.'''
        pattern = [dot*int(b) + dash*(1-int(b)) for b in str(bin(num))[2:]]
        for b in pattern:
            self.beep(b, dot, n=1, background=False)
        time.sleep(pause)

# TODO: ideas for extension of the TonalBuzzer class to allow for playing:
# - active drive (using self.pwm_device.frequency to play tone)
#   - melody(pattern, n, background, tempo, active)
#     - where pattern is a list of tuples with the tone and its duration (in beats)
#    [- a third tuple element could specify the volume for self.pwm_device.value, but this does not work smoothly]
#     - the active flag specifies whether to actively drive the buzzer by PWM frequencies, 
#       or to treat it like a passive buzzer (and only change the duty cycle to change the volume)
#   - beep(on_time, off_time, n, background, tone, volume, active)
#     - same as above. If active is False, the tone parameter will be disregarded, if active is True, volume will be disregarded
#   - play(tone)
#     - already inherited from the TonalBuzzer class
# also setting the source_delay parameter to the smallest beat duration might be nice

    def stop(self):
        self.source = None
        self.value = None


class Sensor:
    '''Provide functions for sensor readout and saving data.'''
    def __init__(self, name, default_interval, func, save_interval=1):
        self.name = name
        # read-related
        self.default_interval = default_interval
        self.func = func
        self.data = []
        # save-related
        self.save_interval = save_interval  # number of seconds to wait  between writing the newest data to a file
        self.filename = datafilename + '_' + self.name + '.csv'
        self.writer = None
        self.last_idx = 0  # index of where the last saving operation left off

    @property
    def interval(self):
        '''Set the reading interval according to the current state,
        as the idea is to run the entire rocket slower when idling.
        '''
        return self.default_interval*conf.state_interval_factors[state]
        
    @pf.profile
    def read(self):
        '''Read and process data from the sensor.
        Return the time it took to run, for the calling loop to sleep for the rest of the interval.
        '''
        start = time.time()
        values = self.func()
        if isinstance(values, list):
            # using the start time, to prevent calling time.time() unneccesarily,
            # and to log the same timestamp in both cases
            self.data.append([start, *values])
        else:
            self.data.append([start, values])
        # barometer only: update state variables
        if self.name == 'baro':
            self.update_state_variables()
        return time.time()-start

    @pf.profile
    def save(self):
        '''Save the latest data, and return the time it took to run.'''
        start = time.time()
        self.writer.writerows(self.data[self.last_idx:])
        self.last_idx = len(self.data)
        self.file.flush()
        return time.time()-start
        
    def read_thread(self):
        '''Run the data reading function repeatedly in the background,
        and run the data saving function at set intervals.
        '''
        next_save = time.time() + self.save_interval
        with open(self.filename, 'a') as self.file:
            self.writer = csv.writer(self.file)
            while not stop.is_set():
                sleep_duration = self.interval - self.read()
                if time.time() > next_save:
                    sleep_duration -= self.save()
                    next_save += self.save_interval
                time.sleep(max(0, sleep_duration))

    def start_thread(self):
        '''Set up the thread and start it.'''
        self.thread = threading.Thread(target=self.read_thread)
        self.thread.start()

    @pf.profile
    def update_state_variables(self):
        '''Update the global state variables, which are used for deployment decisions.'''
        global p, h, v
        p = [p[1], conf.p_smoothing*(self.data[-1][1]/40.96) + (1-conf.p_smoothing)*p[0]]
        h = [h[1], conf.T0/conf.a*((p[1]/p0)**(-conf.R*conf.a/conf.g0)-1)]
        v = [v[1], conf.v_smoothing*(h[1]-h[0])/self.interval + (1-conf.v_smoothing)*v[0]]
        if h[1] >= apogee:
            global apogee
            apogee = h[1]


@pf.profile
def wait_for_toggle(obj, timeout=None):
    '''Call the wait_for_press/release method on obj with the timeout in seconds.
    Return True when the button was toggled in time, and False if the function times out.
    If the timeout was set to None (indefinite), return the time waited.
    '''
    start = time.time()
    initial = obj.value
    obj.wait_for_release(timeout=timeout)
    residual_timeout = start+timeout-time.time() or None
    obj.wait_for_press(timeout=residual_timeout)
    if not initial:
        residual_timeout = start+timeout-time.time() or None
        obj.wait_for_release(timeout=residual_timeout)
    end = time.time()
    if timeout == None:
        return end - start
    return end <= (start + timeout)

def default_blink(self, on_color=conf.white, off_color=(0,0,0)):
    '''Shortcut function for blinking with standard parameters.'''
    self.blink(conf.blink_period/2, conf.blink_period/2,
               on_color=on_color, off_color=off_color,
               n=None, background=True)
# assign the shortcut function to the RGBLED class
gpiozero.RGBLED.default_blink = default_blink

# TODO: either clean this function up a bit or maybe integrate it with the Sensor class
@pf.profile
def sensors_present():
    '''Check if all sensors are adressable'''
    i2cout = subprocess.check_output(['/usr/sbin/i2cdetect', '-y', '1'], universal_newlines=True)
    addresses = [hex(altimu10v5.lis3mdl.LIS3MDL.ADDR)[2:],
                hex(altimu10v5.lps25h.LPS25H.ADDR)[2:],
                hex(altimu10v5.lsm6ds33.LSM6DS33.ADDR)[2:]]
    return all(map(lambda x: x in i2cout, addresses))


@pf.profile
def selftest():
    '''Actuate all the outputs and lists the states of all the inputs,
    to check whether stuff is working.
    '''
    logger.debug('Testing status LED (blinking red-green-blue)')
    for color in (conf.red, conf.green, conf.blue):
        status_LED.blink(conf.blink_period/2, conf.blink_period/2, on_color=color, n=1, background=False)
    time.sleep(1)

    logger.debug('Testing buzzer (beeping 3 times short, 2 times long and beeping 1234 in binary)')
    buzzer.beep(conf.beep_period/2, conf.beep_period/2, n=3, background=False)
    buzzer.beep(3*conf.beep_period/2, conf.beep_period/2, n=2, background=False)
    time.sleep(1)
    buzzer.beep_out(1234)
    time.sleep(1)

    logger.debug('Testing hatch (opening and closing)')
    hatch.value = conf.hatch_open
    time.sleep(1)
    hatch.value = conf.hatch_closed
    time.sleep(1)

    print('Please toggle arm switch')
    logger.debug('Arm switch {}'.format(('timed out', 'working')[wait_for_toggle(arm_switch, timeout=8)]))
    print('Please insert breakwire and take it out again')
    logger.debug('Breakwire detection {}'.format(('timed out', 'working')[wait_for_toggle(breakwire, timeout=8)]))
    
    logger.debug('AltIMU10v5 sensors {}'.format(('not present', 'present')[sensors_present()]))
    

########################################
# initialisation

datafilename = workdir+'../data/'+time.strftime('%d-%m-%y_%H-%M-%S')
shutil.copyfile('config.json', datafilename+'_config.json')

# configure logging to console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
# additional handler for logging exceptions
except_handler = logging.StreamHandler(sys.stderr)
except_handler.setLevel(logging.ERROR)

# configure logging to file
file_handler = logging.FileHandler(filename=datafilename+'.log', mode='a')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(fmt='%(created)s %(levelname)-8s %(name)s:%(funcName)s: %(message)s')
file_handler.setFormatter(file_formatter)

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# add the handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(except_handler)
logger.addHandler(file_handler)

# log initial message
logger.info('Start of the log of {}'.format(conf.name))


# in case the pin number is None (null in json), a dummy object is assigned
hatch      = (gpiozero.Servo(conf.hatch_pin, conf.hatch_closed, pin_factory=PiGPIOFactory()) if conf.hatch_pin else dummy.Output('hatch'))
buzzer     = (BeepingTonalBuzzer(conf.buzzer_pin, octaves=4) if conf.buzzer_pin else dummy.Output('buzzer'))
status_LED = (gpiozero.RGBLED(*conf.status_LED_pins, pwm=True) if all(conf.status_LED_pins) else dummy.Output('status_LED'))
arm_switch = (gpiozero.Button(conf.arm_switch_pin) if conf.arm_switch_pin else dummy.Input('arm_switch'))
breakwire  = (gpiozero.Button(conf.breakwire_pin) if conf.breakwire_pin else dummy.Input('breakwire'))
gpiobjects = [hatch, buzzer, status_LED, arm_switch]

imu = altimu10v5.IMU()
# automatic dummy assignment if the sensors are not present, to allow for easier testing
if sensors_present():
    baro = Sensor('baro', conf.sensor_intervals['baro'], imu.lps25h.get_barometer_raw)
    acc  = Sensor('acc',  conf.sensor_intervals['acc'],  imu.lsm6ds33.get_accelerometer_raw)
    gyro = Sensor('gyro', conf.sensor_intervals['gyro'], imu.lsm6ds33.get_gyroscope_raw)
    mag  = Sensor('mag',  conf.sensor_intervals['mag'],  imu.lis3mdl.get_magnetometer_raw)
else:
    logger.debug('AltIMU10v5 sensors not present, the logged data will be generated by a dummy function')
    baro = Sensor('baro', conf.sensor_intervals['baro'], dummy.Sensor('baro').get)
    acc  = Sensor('acc',  conf.sensor_intervals['acc'],  dummy.Sensor('acc').get)
    gyro = Sensor('gyro', conf.sensor_intervals['gyro'], dummy.Sensor('gyro').get)
    mag  = Sensor('mag',  conf.sensor_intervals['mag'],  dummy.Sensor('mag').get)
sensors = [baro, acc, gyro, mag]

stop = threading.Event()


########################################
# main

if __name__ == '__main__':
    try:
        buzzer.progress()
        start = time.time()
        while update_statemachine() != 'stop':
            if conf.testing:
                logger.debug('{}m and {}m/s'.format(h[1], v[1]))
            time.sleep(max(0, (conf.statemachine_interval*conf.state_interval_factors[state]+start-time.time())))
            start = time.time()
    except:
        logger.exception('main loop broke', exc_info=True)
    finally:
        for obj in gpiobjects:
            obj.close()
        pf.save(datafilename+'_events.csv')
        if conf.testing:
            a = pyprofile.Analyser(pf.events)
            print(a.summary())
            if conf.plot:
                a.plot()
            sys.exit(0)
        else:
            sys.exit(13)  # exit code for shutdown by shell script
