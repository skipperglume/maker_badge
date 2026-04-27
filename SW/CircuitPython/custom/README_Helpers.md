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

