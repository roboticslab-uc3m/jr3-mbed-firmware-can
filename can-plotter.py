import argparse
import collections
import matplotlib.pyplot as plt
import numpy as np
import re
import signal
import sys
import threading
import time

STEPS = 100
TIME_INTERVAL = 0.01 # [s]
MAX_SCALE = 16384 # 2^14
FULL_SCALES = [v / MAX_SCALE for v in [115, 111, 185, 5.6, 5.2, 6.1]] # TEO's right arm
OP_FORCES = 0x600
OP_MOMENTS = 0x680

parser = argparse.ArgumentParser()
parser.add_argument('--id', type=int, required=True, help='node ID')
args = parser.parse_args()

t = np.arange(0, STEPS)
values = [collections.deque(np.zeros(t.shape)) for i in range(6)]
last_value = [0 for i in range(6)]
limits = [(0, 0) for i in range(2)]

should_stop = False

def handler(signum, frame):
    global should_stop
    should_stop = True

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

fig, axes = plt.subplots(1, 2)

axes[0].set_title('forces')
axes[0].set_animated(True)

axes[1].set_title('moments')
axes[1].set_animated(True)

(ln_fx,) = axes[0].plot(values[0], label='x', color='red')
(ln_fy,) = axes[0].plot(values[1], label='y', color='green')
(ln_fz,) = axes[0].plot(values[2], label='z', color='blue')
(ln_mx,) = axes[1].plot(values[3], label='x', color='red')
(ln_my,) = axes[1].plot(values[4], label='y', color='green')
(ln_mz,) = axes[1].plot(values[5], label='z', color='blue')

plt.show(block=False)
plt.pause(0.1)

bg = fig.canvas.copy_from_bbox(fig.bbox)

fig.draw_artist(axes[0])
fig.draw_artist(axes[1])

# https://matplotlib.org/stable/users/explain/animations/blitting.html + https://stackoverflow.com/a/15724978
fig.canvas.blit(fig.bbox)

def do_draw():
    global should_stop

    while not should_stop:
        for i in range(len(values)):
            values[i].popleft()
            values[i].append(last_value[i])

        fig.canvas.restore_region(bg)

        ln_fx.set_ydata(values[0])
        ln_fy.set_ydata(values[1])
        ln_fz.set_ydata(values[2])
        ln_mx.set_ydata(values[3])
        ln_my.set_ydata(values[4])
        ln_mz.set_ydata(values[5])

        axes[0].set_ylim(limits[0][0], limits[0][1])
        axes[1].set_ylim(limits[1][0], limits[1][1])

        fig.draw_artist(axes[0])
        fig.draw_artist(axes[1])

        fig.canvas.blit(fig.bbox)
        fig.canvas.flush_events()

        time.sleep(TIME_INTERVAL)

thread = threading.Thread(target=do_draw)
thread.start()

def hex_to_signed_int(data):
    hex = int(data[1] + data[0], 16)
    return hex - 2**16 if hex > 2**15 - 1 else hex

for line in sys.stdin:
    if should_stop:
        break

    if (m := re.match('^(\w+)\s+(\w+)\s+\[(\d)\]((?:\s+\w{2}){0,8})$', line.strip())) is not None:
        if not int(m.group(3), 10) == 8: # dlc
            continue

        op = int(m.group(2), 16) - args.id
        data = m.group(4).strip().split(' ')

        if op == OP_FORCES:
            last_value[0] = hex_to_signed_int(data[0:2]) * FULL_SCALES[0]
            last_value[1] = hex_to_signed_int(data[2:4]) * FULL_SCALES[1]
            last_value[2] = hex_to_signed_int(data[4:6]) * FULL_SCALES[2]
            limits[0] = (min([limits[0][0]] + last_value[0:3]), max([limits[0][1]] + last_value[0:3]))
        elif op == OP_MOMENTS:
            last_value[3] = hex_to_signed_int(data[0:2]) * FULL_SCALES[3]
            last_value[4] = hex_to_signed_int(data[2:4]) * FULL_SCALES[4]
            last_value[5] = hex_to_signed_int(data[4:6]) * FULL_SCALES[5]
            limits[1] = (min([limits[1][0]] + last_value[3:6]), max([limits[1][1]] + last_value[3:6]))
        else:
            continue
