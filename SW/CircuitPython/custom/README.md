
### Path via usb to maker Badge CircuitPy
    
    /media/$USER/CIRCUITPY

### Terminal command to get path

    lsblk

Or:

    sudo dmesg | grep tty

### Find a serial port:

    ls /dev/tty*

You should for something like: `/dev/ttyACM0`, with recent time of creation.

### Simple command to create a serial reader: 

    grep --quiet --max-count=1 -F "foo" /dev/ttyUSB0

### Command to move a new script:

    scp code.py /media/$USER/CIRCUITPY/code.py
    scp qr.bmp /media/$USER/CIRCUITPY/


### Output of os.uname() : 
    
    sysname='ESP32S2', 
    nodename='ESP32S2', 
    release='8.2.6', 
    version='8.2.6 on 2023-09-12', 
    machine='Maker badge by Czech maker with ESP32S2'

### Output of os.listdir('/'):

    ['.fseventsd', '.metadata_never_index', '.Trashes', 'settings.toml', 'lib', 'boot_out.txt', 'System Volume Information', 'code.py', 'logo.bmp', 'qr.bmp']
    scp code.py /media/lofu/CIRCUITPY/code.py
    scp qr.bmp /media/lofu/CIRCUITPY/


### Important remarks:

 1. For the board `rev.D` a pin `board.D16` is a power controlling pin to display. Without setting it to `LOW`/`False` e-paper display won't refresh.
