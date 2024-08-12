
### Path via usb to maker Badge CircuitPy
    
    /media/lofu/CIRCUITPY

### Terminal command to get path

    lsblk

Or:

    sudo dmesg | grep tty

### Find a serial port:

    ls /dev/tty*

You should for something like: `/dev/ttyACM0`, with recent time of creation.

### Simple command to creat a serial reader: 

    grep --quiet --max-count=1 -F "foo" /dev/ttyUSB0

### Command to move a new script:

    scp code.py /media/lofu/CIRCUITPY/code.py
    scp qr.bmp /media/lofu/CIRCUITPY/


### Important remark:

For the board `rev.D` a pin `board.D16` is a powerconstroling pin to display. Without setting it to `LOW`/`False` e-paper display won't refresh.
