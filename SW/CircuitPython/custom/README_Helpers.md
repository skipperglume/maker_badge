```bash
sudo apt install -y picocom
```


sudo usermod -aG dialout $USER

sudo chmod a+rw /dev/ttyACM0



newgrp dialout


```bash
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

dmesg | tail -n 50

Connect to listen to port:
```bash
picocom -b 115200 /dev/ttyACM0
```

## Helper scripts

Run from the repository root:

1) Auto-detect serial port and open `picocom`:

```bash
./SW/CircuitPython/custom/scripts/connect_badge_serial.sh
```

Optional flags:

```bash
./SW/CircuitPython/custom/scripts/connect_badge_serial.sh --list
./SW/CircuitPython/custom/scripts/connect_badge_serial.sh --baud 115200
./SW/CircuitPython/custom/scripts/connect_badge_serial.sh --port /dev/ttyACM0
```

2) Copy code files/folders to mounted `CIRCUITPY` drive:

```bash
./SW/CircuitPython/custom/scripts/copy_to_badge.sh code.py
```

Examples:

```bash
./SW/CircuitPython/custom/scripts/copy_to_badge.sh code.py code_wifi.py
./SW/CircuitPython/custom/scripts/copy_to_badge.sh --target lib my_module/
./SW/CircuitPython/custom/scripts/copy_to_badge.sh --mount /media/$USER/CIRCUITPY code.py
```

