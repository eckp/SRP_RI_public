import os
from flask import Flask, render_template, request, jsonify, send_file
import time
import types
import zipfile

try:
    from gpiozero.pins.pigpio import PiGPIOFactory
    import gpiozero
    dry_run = False
except ImportError:
    dry_run = True

# helper method, to be bodged onto the AngularServo class for now
def move(self, angle=None, speed=0):
    '''Moves the servo to angle [deg] at speed [deg/s].'''
    if self.angle is None or angle is None or speed == 0:
        self.angle = angle
        return
    begin, end = int(self.angle), angle
    for a in range(begin, end+1, 2*(begin<end)-1):
        self.angle = a
        time.sleep(1/speed)

if not dry_run:
    gpiozero.AngularServo.move = move
    servo = gpiozero.AngularServo(4, min_angle=0, max_angle=90, initial_angle=None, pin_factory=PiGPIOFactory())
    switch = gpiozero.Button(27)
    breakwire = gpiozero.Button(22)
    switch.when_pressed = lambda: set_position(90)
    switch.when_released = lambda: set_position(0)
    breakwire.when_released = lambda: stop(True)
    LED = gpiozero.RGBLED(24, 23, 18)
position = None
shutdown = False  # whether to shut down after exit. Var will be set by function call
shutdown_hook = None  # hacky global to store the server shutdown function in at the soonest request
project_dir = '/home/pi/Documents/SRP_RI/'

def stop(_shutdown=False):
    global shutdown
    shutdown = _shutdown
    #print('shutting down?', shutdown)
    #request.environ.get('werkzeug.server.shutdown')()  # stop Flask server, does not work outside request
    shutdown_hook()


def set_position(angle):
    global position
    position = angle
    if dry_run:
        print(position)
    else:
        if isinstance(position, int) or position is None:
            servo.move(angle=position, speed=45)
        else:
            print(position+' ignored as it is not int or NoneType')


app = Flask(__name__)
if dry_run:
    app.config['DEBUG'] = True

@app.context_processor
def get_logdate_dropdown():
    all_data_files = os.listdir(project_dir+'data/')
    dates = list(set([f[:17] for f in all_data_files]))
    sorted_dates = dates.sort(key=lambda x: int(x[6:8]+x[3:5]+x[0:2]+x[9:11]+x[12:14]+x[15:17]))  # manually parsing the date :(
    dropdown_options = '\n'.join(['<option value="{}">{}</option>'.format(d, d) for d in dates[::-1]])
    return dict(dropdown = dropdown_options)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/_set_position', methods=['POST'])
def _set_position():
    _position = request.form.get('position', type=int)
    set_position(_position)
    return jsonify(position=position)

@app.route('/_get_position', methods=['GET'])
def _get_position():
    global shutdown_hook
    if shutdown_hook is None:  # save the shutdown hook from this request for later
        shutdown_hook = request.environ.get('werkzeug.server.shutdown')
    return jsonify(position=position)

@app.route('/_stop', methods=['POST'])
def _stop():
    stop(bool(request.form.get('shutdown', type=int)))
    return '', 204

@app.route('/_get_file/<path:logdate>', methods=['GET', 'POST'])
def _get_file(logdate):
#    logdate = request.form.get('logdate')
    temppath = project_dir+'temp/'+logdate+'.zip'
    zipf = zipfile.ZipFile(temppath, 'w', zipfile.ZIP_DEFLATED)
    for file in [f for f in os.listdir('data/') if f.startswith(logdate)]:
        zipf.write('data/'+file, arcname=file)
    zipf.close()
    return send_file(temppath, mimetype='zip', as_attachment=True)

# Run the app on the local development server
if __name__ == "__main__":
    if not dry_run:
        LED.color = (0,1,0)
    else:
        print('ready')
    app.run(host='0.0.0.0')
    #print('app is done, going to send exit code', shutdown*13)
    exit(shutdown*13)  # 13 is the exit code that tells the shell script to shut down

