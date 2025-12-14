# JR3 Mbed firmware (CAN interface)

An Arm Mbed OS 6 application that performs data acquisition from a JR3 force-torque sensor and streams it through a CAN channel.

Incidentally, support was added for sending simple PWM commands to a Lacquey fetch gripper through a secondary optional CAN channel.

Refer to [roboticslab-uc3m/jr3-mbed-firmware](https://github.com/roboticslab-uc3m/jr3-mbed-firmware/) for the underlying board-sensor communication. This repository focuses on the CAN interface layer with an external master node. Refer to [roboticslab-uc3m/jr3-mbed-firmware-usb](https://github.com/roboticslab-uc3m/jr3-mbed-firmware-usb/) for the USB interface variant.

## Installation

Since the Mbed Online Compiler has been discontinued and the Keil web compiler will be shut down on July 2026, the preferred method is to use the [Mbed CE (Community Edition)](https://mbed-ce.dev/) CMake-based build system. Once built, plug in the Mbed to a USB port of your PC and drag-and-drop the downloaded .bin file into it.

## CAN protocol

| command                          | op code | direction | payload<br>(bytes) | details                                                                                              |
|----------------------------------|:-------:|:---------:|:------------------:|------------------------------------------------------------------------------------------------------|
| sync                             |  0x080  |     in    |          0         |                                                                                                      |
| acknowledge                      |  0x100  |    out    |        1-7         | LSB byte: 0x00 - sensor ready; 0x01 - not initialized<br>6 MSB bytes (optional): see command details |
| **start sync**                   |  0x180  |     in    |          2         | low-pass filter cutoff frequency in 0.01*Hz (integer)<br>(e.g. 1025 = 10.25 Hz)                      |
| **start async**                  |  0x200  |     in    |          6         | 2 LSB bytes: cutoff frequency (as above)<br>4 MSB bytes: period in us (integer)                      |
| **stop**                         |  0x280  |     in    |          0         |                                                                                                      |
| **zero offsets**                 |  0x300  |     in    |          0         |                                                                                                      |
| **set filter**                   |  0x380  |     in    |          2         | cutoff frequency (as above)                                                                          |
| **get state**                    |  0x400  |     in    |          0         |                                                                                                      |
| **get full scales**<br>(forces)  |  0x480  |     in    |          0         | acknowledge message carries force full scales<br>in the 6 MSB bytes (Fx, Fy, Fz)                     |
| **get full scales**<br>(moments) |  0x500  |     in    |          0         | acknowledge message carries moment full scales<br>in the 6 MSB bytes (Mx, My, Mz)                    |
| **reset**                        |  0x580  |     in    |          0         |                                                                                                      |
| force data                       |  0x600  |    out    |          8         | (3x) 2 LSB bytes: Fx, Fy, Fz (integer, signed)<br>2 MSB bytes: frame counter                         |
| moment data                      |  0x680  |    out    |          8         | (3x) 2 LSB bytes: Mx, My, Mz (integer, signed)<br>2 MSB bytes: frame counter                         |
| bootup                           |  0x700  |    out    |          0         |                                                                                                      |
| gripper PWM                      |  0x780  |     in    |          4         | PWM command between -100.0 and 100.0 (float)                                                         |

Bolded incoming commands imply that the Mbed will respond with an acknowledge message.

## Usage

On bootup, the calibration matrix and full scales are queried from the sensor and stored for later use. If successful, the bootup message is sent. This may take a few seconds from initial power up. A failure means that there is no connection to the sensor. Re-initialization may be requested during normal operation through the "reset" command. If the initialization succeeds, the JR3 controller is in "ready" state, otherwise it remains in "not initialized" state. All acknowledge messages carry this state information in their payload. The "get state" command is a no-op that can be used to ping the controller.

The JR3 sensor operates in two modes: synchronous and asynchronous. Both entail that a background thread will be performing data acquisition, decoupling, offset removal and filtering at full sensor bandwidth (8 KHz per channel).

- Synchronous ("start sync" command): per the CiA 402 standard (a.k.a. CANopen), a SYNC message is broadcast over the CAN network by a producer node so that consumers act upon (e.g. send sensor data, accept motion commands). As soon as the incoming SYNC message is processed, the Mbed will send the latest force and moment data in return.
- Asynchronous ("start async" command): an additional thread is spawned to query latest forces and moments at the specified fixed rate (tested at 1 ms).

The sensor is **not** calibrated by default. Use the "zero offsets" command to capture the current offset and substract it from subsequent filtered results. This command can be issued at any time.

It is highly recommended to enable raw data filtering by specifying the desired cutoff frequency to either start command. This firmware implements a simple first-order low-pass IIR filter, also known as an exponential moving average (see [Wikipedia article](https://w.wiki/7Er6)). Its cutoff frequency can be modified through the "set filter" command.

Outgoing force and moment data requires post-processing on the receiver's side. These signed integer values should be multiplied by the corresponding full scale and divided by a factor of 16384 (=2^14) for forces and 16384\*10 for moments. The resulting values will be expressed in Newtons and Newton*meters, respectively. Use the "get full scales" command to query the sensor full scales.

## Configuration

See [mbed-app.json5](mbed_app.json5) for a list of configurable parameters and their description. The project should be recompiled after any changes are made to this file.

## Additional tools

Most Linux kernels should support [SocketCAN](https://www.kernel.org/doc/html/next/networking/can.html). In order to create a network interface for a CAN channel with a baudrate of 1 Mbps, run the following command:

```
sudo ip link set can0 up txqueuelen 1000 type can bitrate 1000000
```

To send a CAN message, install the [can-utils](https://github.com/linux-can/can-utils) package (`apt install can-utils`) and run:

```
cansend can0 201#C80010270000
```

This will start an ASYNC publisher on ID 1 with a period of 10 ms (10000 us = 0x2710) and a cutoff frequency of 2 Hz (200 Hz*0.01 = 0x00C8). Use the `candump can0` command on a new terminal to inspect live traffic on the CAN bus, including any response from the Mbed.

A helper Python script is provided for visual inspection of filtered data, [can-plotter.py](can-plotter.py). Example usage:

```
candump can0 | python3 can-plotter.py --id 1
```

## Dependencies

This project depends on the following libraries developed and kindly shared by other MBED users. Their code has been embedded into this repository for convenience.

- <https://os.mbed.com/users/simon/code/Motor/>

## See also

- <https://github.com/roboticslab-uc3m/jr3-mbed-firmware/>
- <https://github.com/roboticslab-uc3m/jr3-mbed-firmware-usb/>
- <https://github.com/roboticslab-uc3m/yarp-devices/issues/263>
- <https://github.com/roboticslab-uc3m/jr3pci-linux/>
