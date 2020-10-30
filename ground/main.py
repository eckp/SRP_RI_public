import math
import json
import os
import numpy as np
import scipy as sp
import sys
from matplotlib import pyplot as plt

plt.style.use("ggplot")


def load_data(name):
    f = open(name).readlines()
    datapoints = []
    for line in f:
        if not line[0] == "#":
            line = line.split(",")
            for i in range(0, len(line)):
                line[i] = float(line[i])
            datapoints.append(np.asarray(line))
    datapoints = np.asarray(datapoints)
    datapoints = np.transpose(datapoints)
    return datapoints


def read_log(log):
    states = {"START": [], "IDLE": [], "PREPARED": [], "ARMED": [], "LAUNCHED": [], "DEPLOYED": []}
    loglines = open(log).readlines()
    for line in range(0, len(loglines)):
        if loglines[line][-1:] == "\n":
            loglines[line] = loglines[line][:-1]
        words = loglines[line].split(" ")
        if line == 0:
            states["START"].append([float(words[0]), np.NAN])
            states["IDLE"].append([float(words[0]), np.NAN])
        elif words[1] == "INFO":
            states[words[-3]][-1][1] = float(words[0])
            if not words[-1] in states.keys():
                states[words[-1]] = []
            states[words[-1]].append([float(words[0]), np.NAN])
    return states


def plot_states(states, ax, text_y):
    for state in list(states.keys()):
        for change in states[state]:
            ax.vlines(change[0] - states["START"][0][0], -sys.maxsize, sys.maxsize)
            ax.text(change[0] - states["START"][0][0], text_y, state)


def calculate_acc_g(acc_data):
    acc_raw = [np.asarray(acc_data[a]) * 488e-6 for a in range(1, len(acc_data))]  # conversion from LSB to g's  # why the range(1, len)?
    return acc_raw

def calculate_gyro_dps(gyro_data):
    gyro_raw = [np.asarray(gyro_data[g])* 17500e-6 for g in range(1, len(gyro_data))]  # conversion from LSB to dps
    return gyro_raw


def calculate_mag_gaus(mag_data):
    mag_raw = [np.asarray(mag_data[m]) / 6842 for m in range(1, len(mag_data))]  # conversion from LSB to gauss
    return mag_raw


def calculate_heading(mag_list, states):
    """Calculates the heading for the ascent only, as only then the data is interesting/processable"""
    # setup and array creation
    sine_wave_time = 7  # number of seconds after launch that are usable for heading zeroing
    mag = np.asarray(mag_list[1:])
    times = np.asarray(mag_list[0])
    start = False
    for t in range(0, len(times)):
        if times[t] > states["LAUNCHED"][0][0] and not start:
            before_launch = np.asarray([m[:t] for m in mag])
            start = t
        elif times[t] > states["LAUNCHED"][0][0] + sine_wave_time:
            timeframe_for_calibration = np.asarray([m[start:t] for m in mag])
            cali = t
            break
    timeframe_of_interest = np.asarray([m[cali:] for m in mag])
    times_toi = times[cali:]
    # calculation of offsets and zero values
    offsets = np.array([(max(axis) + min(axis)) / 2 for axis in timeframe_for_calibration])
    before_launch_zeroed = np.asarray([before_launch[i] - offsets[i] for i in range(0, len(offsets))])
    timeframe_of_interest_zeroed = np.asarray([timeframe_of_interest[i] - offsets[i] for i in range(0, len(offsets))])
    heading_zero = np.mean(np.arctan2(before_launch_zeroed[0], before_launch_zeroed[1]))
    # calculation of relative heading and angular rates
    headings = np.array(np.arctan2(timeframe_of_interest_zeroed[0], timeframe_of_interest_zeroed[1]) - heading_zero)
    # correct for modulo 360 by atan2 by adding/subtracting (based on the sign of the jump) 2pi whenever there's a jump bigger than pi in the values
    for i in range(1, len(headings)):
        diff = headings[i - 1] - headings[i]
        if abs(diff) > np.pi:
            headings[i:] += np.pi * 2 * diff / abs(diff)
    angular_rate = np.array([0] + [(h - headings[i]) / (t - times_toi[j]) for (i, h), (j, t) in
                                   zip(enumerate(headings[1:]), enumerate(times_toi[1:]))])
    return [times_toi, headings * 180 / np.pi, angular_rate * 180 / np.pi, heading_zero * 180 / np.pi]


def calculate_alt_vv(baro_data, conf, states):
    pressure_raw = np.asarray(baro_data[1]) / 40.96
    pressure_smoothed = [pressure_raw[0]]
    for i in range(0, len(pressure_raw)):
        if baro_data[0][i] >= states["LAUNCHED"][0][0]:
            p0 = np.average(pressure_raw[:i])
    for i, p in enumerate(pressure_raw[1:]):
        pressure_smoothed.append(conf["p_smoothing"] * p + (1 - conf["p_smoothing"]) * pressure_smoothed[i])
    altitude = [conf["T0"] / conf["a"] * ((p / p0) ** (-(conf["R"] * conf["a"]) / conf["g0"]) - 1)
                for p in pressure_smoothed]
    #print(altitude)
    vertical_velocity = [0] + [(alt - altitude[i]) / conf["sensor_intervals"]['baro'] for i, alt in
                               enumerate(altitude[1:])]  # conversion from h to vv
    vertical_velocity_smoothed = [vertical_velocity[0]]
    for i, vv in enumerate(vertical_velocity[1:]):
        vertical_velocity_smoothed.append(conf["v_smoothing"] * vv + (1 - conf["v_smoothing"])
                                          * vertical_velocity_smoothed[i])
    return np.round(np.asarray(pressure_raw), 3), np.round(np.asarray(pressure_smoothed), 3), \
           np.round(np.asarray(altitude), 3), np.round(np.asarray(vertical_velocity), 3), \
           np.round(np.asarray(vertical_velocity_smoothed), 3)


if __name__ == '__main__':
    print("Current directory is:", os.getcwd())
    rel_path = input("Enter relative path from current dir:")
    if not rel_path:
        rel_path = ""
    elif rel_path[0] != "/" or rel_path[0] != "\\":
        if "\\" in os.getcwd():
            rel_path = "\\" + rel_path.replace('/', '\\')
        elif "/" in os.getcwd():
            rel_path = "/" + rel_path.replace('\\', '/')
    while True:
        choices = []
        for date in os.listdir(os.getcwd()+rel_path):
            if date[-4:] == ".log":
                choices.append(date[:-4])
        choices = sorted(choices)
        for c in range(0, len(choices)):
            print(str(c) + ".", choices[c])
        datafilename = input('Which files? Give index or full name: ')
        if not datafilename:
            datafilename = choices[-1]
        if datafilename in ('q', 'quit', 'stop', 'x', 'exit'):
            quit()
        if datafilename not in choices:
            try:
                datafilename = choices[int(datafilename)]
                break
            except IndexError as error:
                print("Not a valid index")
            except TypeError as error:
                print("Not a valid index")
    with open(os.getcwd() + rel_path + datafilename + '_config.json') as config_file:
        conf = json.load(config_file)
    states = read_log(os.getcwd() + rel_path + datafilename + '.log')

    n_plots = len(conf["sensor_intervals"].keys())
    n_rows = int(math.sqrt(n_plots))
    n_cols = math.ceil(n_plots / n_rows)
    fig, axs = plt.subplots(n_rows, n_cols, sharex=True)
    fig.suptitle('Raw sensor readings', fontsize=20)
    sensors = {}
    for i, name in enumerate(conf["sensor_intervals"].keys()):
        sensors[name] = load_data(os.getcwd() + rel_path + datafilename + "_" + name + '.csv')
        ax = axs[i // n_cols, i % n_cols]
        ax.set_title(name)
        lim = [sys.maxsize, -sys.maxsize]
        for s in range(1, len(sensors[name])):
            ax.scatter(sensors[name][0] - states["START"][0][0], sensors[name][s])
            lim = [min(lim[0], min(sensors[name][s])), max(lim[1], max(sensors[name][s]))]
        lim_delta = (lim[1] - lim[0]) * 0.1
        lim = [lim[0] - lim_delta, lim[1] + lim_delta]
        plot_states(states, ax, lim[0] + lim_delta * 0.5)
        ax.set_ylim(lim)
    plt.show()

    p, ps, h, vv, vvs = calculate_alt_vv(sensors['baro'], conf, states)
    baroplots = {'pressure': [p, ps], 'altitude': [h],
                 'vertical velocity': [vv, vvs]}
    n_plots = len(baroplots)
    n_rows = int(math.sqrt(n_plots))
    n_cols = math.ceil(n_plots / n_rows)
    fig, axs = plt.subplots(n_rows, n_cols, sharex=True)
    fig.suptitle('Barometer based measurements', fontsize=20)
    for i, name in enumerate(baroplots):
        if n_rows == 1:
            ax = axs[i]
        else:
            ax = axs[i // n_cols, i % n_cols]
        ax.set_title(name)
        lim = [sys.maxsize, -sys.maxsize]
        for s in range(0, len(baroplots[name])):
            ax.plot(sensors['baro'][0] - states["START"][0][0], baroplots[name][s])
            lim = [min(lim[0], min(baroplots[name][s])), max(lim[1], max(baroplots[name][s]))]
        lim_delta = (lim[1] - lim[0]) * 0.1
        lim = [lim[0] - lim_delta, lim[1] + lim_delta]
        plot_states(states, ax, lim[0] + lim_delta * 0.5)
        ax.set_ylim(lim)
    plt.show()

    fig, axs = plt.subplots(2, 2, sharex=True)
    fig.suptitle('Usable calibrated sensor readings', fontsize=20)

    lim = [sys.maxsize, -sys.maxsize]
    #print(calculate_acc_g(sensors['acc']))
    for d in calculate_acc_g(sensors['acc']):
        #print(d)
        axs[0, 0].plot(sensors['acc'][0] - states["START"][0][0], d)
        lim = [min(lim[0], min(d)), max(lim[1], max(d))]
    lim_delta = (lim[1] - lim[0]) * 0.1
    lim = [lim[0] - lim_delta, lim[1] + lim_delta]
    axs[0, 0].set_title('Accelerometer')
    axs[0, 0].set_ylabel('Acceleration [g]')
    axs[0, 0].set_xlabel('Time [s]')
    axs[0, 0].set_xlim(-2, states["DEPLOYED"][0][0] - states["START"][0][0] + 35)
    plot_states(states, axs[0, 0], lim[0] + lim_delta * 0.5)
    axs[0, 0].set_ylim(lim)

    lim = [sys.maxsize, -sys.maxsize]
    for d in calculate_gyro_dps(sensors['gyro']):  #range(1,len(sensors['gyro'])):
        axs[0, 1].plot(sensors['gyro'][0] - states["START"][0][0], d)
        lim = [min(lim[0], min(d)), max(lim[1], max(d))]
    lim_delta = (lim[1] - lim[0]) * 0.1
    lim = [lim[0] - lim_delta, lim[1] + lim_delta]
    axs[0, 1].set_title('Gyro')
    axs[0, 1].set_ylabel('Angular rate [dps]')
    axs[0, 1].set_xlabel('Time [s]')
    axs[0, 1].set_xlim(-2, states["DEPLOYED"][0][0] - states["START"][0][0] + 35)
    plot_states(states, axs[0, 1], lim[0] + lim_delta * 0.5)
    axs[0, 1].set_ylim(lim)

    lim = [sys.maxsize, -sys.maxsize]
    for d in calculate_mag_gaus(sensors['mag']):
        axs[1, 0].plot(sensors['mag'][0] - states["START"][0][0], d)
        lim = [min(lim[0], min(d)), max(lim[1], max(d))]
    lim_delta = (lim[1] - lim[0]) * 0.1
    lim = [lim[0] - lim_delta, lim[1] + lim_delta]
    axs[1, 0].set_title('Magnetometer')
    axs[1, 0].set_ylabel('Magnetic field strength [gauss]')
    axs[1, 0].set_xlabel('Time [s]')
    axs[1, 0].set_xlim(-2, states["DEPLOYED"][0][0] - states["START"][0][0] + 35)
    plot_states(states, axs[1, 0], lim[0] + lim_delta * 0.5)
    axs[1, 0].set_ylim(lim)

    angular_rate = calculate_heading(sensors['mag'], states)
    lim = [sys.maxsize, -sys.maxsize]
    for d in range(1, len(angular_rate)-1):
        axs[1, 1].plot(angular_rate[0] - states["START"][0][0], angular_rate[d])
        lim = [min(lim[0], min(angular_rate[d])), max(lim[1], max(angular_rate[d]))]
    lim_delta = (lim[1] - lim[0]) * 0.1
    lim = [lim[0] - lim_delta, lim[1] + lim_delta]
    axs[1, 1].set_title('Magnetometer-derived')
    axs[1, 1].set_ylabel('Angular rate [dps]')
    axs[1, 1].set_xlabel('Time [s]')
    #plot_states(states, axs[1, 1], lim[0] + lim_delta * 0.5)
    axs[1, 1].set_ylim(lim)
    plt.show()



