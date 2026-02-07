import argparse
import re
import signal
import sys
import threading

from jr3.plotter import Plotter

MAX_SCALE = 16384 # 2^14
FULL_SCALES = [v / MAX_SCALE for v in [115, 111, 185, 5.6, 5.2, 6.1]] # TEO's right arm
OP_FORCES = 0x600
OP_MOMENTS = 0x680

parser = argparse.ArgumentParser()
parser.add_argument('--id', type=int, required=True, help='node ID')
args = parser.parse_args()

plotter = Plotter()

should_stop = False

def handler(signum, frame):
    global should_stop
    should_stop = True

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

def hex_to_signed_int(data):
    hex = int(data[1] + data[0], 16)
    return hex - 2**16 if hex > 2**15 - 1 else hex

def do_read():
    for line in sys.stdin:
        if should_stop:
            break

        if (m := re.match(r'^(\w+)\s+(\w+)\s+\[(\d)\]((?:\s+\w{2}){0,8})$', line.strip())) is not None:
            if not int(m.group(3), 10) == 8: # dlc
                continue

            op = int(m.group(2), 16) - args.id
            data = m.group(4).strip().split(' ')

            if op == OP_FORCES:
                forces = [hex_to_signed_int(data[i:i+2]) * FULL_SCALES[j] for j, i in enumerate(range(0, 6, 2))]
                plotter.update_forces(forces)
            elif op == OP_MOMENTS:
                moments = [hex_to_signed_int(data[i:i+2]) * FULL_SCALES[j] for j, i in enumerate(range(0, 6, 2), start=3)]
                plotter.update_moments(moments)
            else:
                continue

thread = threading.Thread(target=do_read)
thread.start()

while not should_stop:
    plotter.plot()
