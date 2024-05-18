# https://www.zive.cz/clanky/cesky-maker-badge-zapomente-na-papirove-visacky-ted-si-je-muzete-naprogramovat-pro-kazdou-akci/sc-3-a-223710/default.aspx
# https://www.zive.cz/clanky/programovani-elektroniky-cinsky-radar-na-lidi-za-tri-stovky-hlk-ld2450/sc-3-a-224831/default.aspx?recombee_recomm_id=bb31d49b0cdbb0e6e00abecf60eaf14e
import time
import terminalio
import board
import neopixel
import touchio
import displayio
import adafruit_ssd1680
import analogio
from adafruit_display_text import label
import gc
import digitalio
# TODO: test this library
# import os

# Activating the eink's power supply and configuring its SPI bus
# The transistor turns on the power supply by setting the GPIO16 pin to a low state 
enable_display = digitalio.DigitalInOut(board.D16)
enable_display.direction = digitalio.Direction.OUTPUT
enable_display.value = False



# Function to write test to console\terminal
# Better write off with RAM usage
def printm(text):
    print(f"RAM {gc.mem_free()} B:\t{text}")

# Function for append text to the display data
def _addText(text, scale, color, x_cord, y_cord):
    group = displayio.Group(scale = scale, x = x_cord, y = y_cord)
    text_label = label.Label(terminalio.FONT, text = text, color = color)
    group.append(text_label)
    display_data.append(group)

def get_batery_State():
    coeff = 2 # Coefficient for voltage divider
    battery_en.value = False # The transistor turns on the voltage divider circuit by setting the battery_en pin to a low state
    raw = battery_adc.value # Get the value  /A/D
    battery_en.value = True # We disconnect the circuit by setting the high state
    # Data from the A/D CircuitPython returns in the range 0-65535 regardless of the actual resolution of the A/D on the chip
    # We recalculate the raw value back to the voltage with the assumption that the value 65535 corresponds to a voltage of 3.3V
    voltage = raw * (3.3 / 65536)
    return {'voltage':voltage * coeff, 'raw_normalized':voltage, 'raw':raw}

def displayMakerDescription(name, surname, company):
    '''
    Method for printing the namecard to the ePaper display
    '''
    while len(display_data) > 0:
        display_data.pop()

    # Append tilegrid with the background to the display data
    display_data.append(background)

    # Append text to the display data
    _addText(name, 3, display_black, 70, 20)
    _addText(surname, 3, display_black, 50, 60)
    _addText(company, 2, display_black, 20, 100)
    display.show(display_data)
    display.refresh()
    time.sleep(1)

def displayVoltage():
    '''
    Method for printing the Voltage: Raw and Voltage
    '''
    while len(display_data) > 0:
        display_data.pop()

    # Append tilegrid with the background to the display data
    display_data.append(background)

    readOff = get_batery_State()

    # Append text to the display data
    _addText('Battery status:', 2, display_black, 20, 20)
    _addText(f'Voltage: {readOff['voltage']} V', 2, display_black, 20, 60)
    _addText(f'Raw: {readOff['raw']}', 2, display_black, 20, 100)
    display.show(display_data)
    display.refresh()
    time.sleep(1)

def displayEmpty():
    '''
    Method for displaying the empty screen
    '''
    while len(display_data) > 0:
        display_data.pop()

    # Append tilegrid with the background to the display data
    display_data.append(background)

    display.show(display_data)
    display.refresh()
    time.sleep(1)

def displayFigure():
    '''
    Method for a figure on the display. Will try to make some random figure.
    '''
    while len(display_data) > 0:
        display_data.pop()

    # Append tilegrid with the background to the display data
    display_data.append(background)

    figure_map = displayio.Bitmap(display_width, display_height, 1)
    
    figure_palette = displayio.Palette(1) # 
    figure_palette[0] = display_white

    
    figure_map[0, 0] = 1
    figure_map[5, 5] = 1
    for k in range(5):
        for i in range(10):
            for j in range(10):
                figure_map[10*2*k+i, 5*2*k+j] = 1
    figure_map[10, 10] = 1
    figure_map[20, 20] = 1

    figure = displayio.TileGrid(figure_map, pixel_shader = figure_palette)
    display_data.append(figure)

    display.show(display_data)
    display.refresh()
    time.sleep(1)

def displayQR():
    '''
    Method for displaying QR code on the display
    '''
    while len(display_data) > 0:
        display_data.pop()

    # Append tilegrid with the background to the display data
    display_data.append(background)

    
    display_data.append(qr_tile)

    display.show(display_data)
    display.refresh()
    time.sleep(1)

def printBatteryState(func):
    '''
    Method for printing the namecard to the ePaper display
    '''
    data = func()
    _addText(f'Voltage: {data['voltage']}', 3, display_black, 70, 20)
    _addText(f'Raw: {data['raw']}', 3, display_black, 50, 60)
    display.show(display_data)
    display.refresh()
    time.sleep(1)
    data.clear()



# Define board pinout
board_spi = board.SPI()  # Uses SCK and MOSI
# Define ePaper display pins
board_epd_cs = board.D41 # Chip select pin for display controller (active low)
board_epd_dc = board.D40 # Data/Command pin for display controller. 0 for command, 1 for data
board_epd_reset = board.D39 # Reset pin for display controller
board_epd_busy = board.D42 # Busy signal from display controller

# Define pin for battery reading
# D6
battery_en = digitalio.DigitalInOut(board.D14)
battery_en.direction = digitalio.Direction.OUTPUT
battery_adc = analogio.AnalogIn(board.D6)
get_batery_State() 

# Define touch buttons
touch_threshold = 20000 # Adjust this value to be higher or lower depending on your touch sensitivity
touch_1 = touchio.TouchIn(board.D5)
touch_1.threshold = touch_threshold
touch_2 = touchio.TouchIn(board.D4)
touch_2.threshold = touch_threshold
touch_3 = touchio.TouchIn(board.D3)
touch_3.threshold = touch_threshold
touch_4 = touchio.TouchIn(board.D2)
touch_4.threshold = touch_threshold
touch_5 = touchio.TouchIn(board.D1)
touch_5.threshold = touch_threshold

# Define LED
led_pin = board.D18
# Neo Pixel LED initialization with 4 LEDs and 10% brightness level
led_matrix = neopixel.NeoPixel(led_pin, 4, brightness = 0.1, auto_write = False)

# Define LED colors value
led_off = (0, 0, 0)
led_red = (255, 0, 0)
led_green = (0, 255, 0)
led_blue = (0, 0, 255)
led_purple = (255, 0, 255)

# Define ePaper display colors value
display_black = 0x000000
display_white = 0xFFFFFF

# Define ePaper display resolution
display_width = 250
display_height = 122

# Prepare ePaper display
displayio.release_displays()
display_bus = displayio.FourWire(
    board_spi, command = board_epd_dc, chip_select = board_epd_cs, reset = board_epd_reset, baudrate = 1000000
)
time.sleep(0.5)
# Initialize the display
display = adafruit_ssd1680.SSD1680(
    display_bus, # The display bus 
    width = display_width, # The width and height values can be adjusted to match the physical display
    height = display_height, # The width and height values can be adjusted to match the physical display
    rotation = 270, # The rotation can be adjusted to match the physical orientation of the display
    busy_pin = board_epd_busy, #
    seconds_per_frame=10,
    # time_to_refresh=1,
)

display_data = displayio.Group()
display_background = displayio.Bitmap(display_width, display_height, 1)
display_color_palette = displayio.Palette(1) # 
display_color_palette[0] = display_white

background = displayio.TileGrid(display_background, pixel_shader = display_color_palette)

qr_bmp = displayio.OnDiskBitmap("/qr.bmp")
qr_tile = displayio.TileGrid(qr_bmp, pixel_shader=qr_bmp.pixel_shader)



def startingDisplay(select: int):
    if select == 0:
        # Render namecard to display
        displayMakerDescription('Denys', 'Timoshyn', 'Charles University')
    elif select == 1:
        # Render empty display
        displayVoltage()
    elif select == 2:
        # Render figure on display
        displayFigure()
    elif select == 3:
        # Render QR code on display
        displayQR()
    else: 
        # Render empty display
        displayEmpty()

startingDisplay(3)

    


# Display a BMP graphic from the root directory of the CIRCUITPY drive
# with open("/logo.bmp", "rb") as f:
#     pic = displayio.OnDiskBitmap(f)
#     # Create a Tilegrid with the bitmap and put in the displayio group
#     t = displayio.TileGrid(pic, pixel_shader=pic.pixel_shader)
#     display_data.append(t)
#     enable_display.value = False
#     display.show(display_data)
#     display.refresh()

enable_display.value = False
# MAIN LOOP
while True:
    # color = [0,0,0]
    printm('')
    printm(f'{get_batery_State()}')
    printm(f'Size of display_data: {len(display_data)}')
    if touch_1.value:
        # Turn off the LED
        led_matrix.fill(led_off)
        led_matrix.show()
        if display.time_to_refresh == 0.0:
            displayMakerDescription('Denys', 'Timoshyn', 'Charles University')
            time.sleep(1)
            printm(f'Size of display_data: {len(display_data)}')
    if touch_2.value:
        # Set LED to red
        led_matrix.fill(led_red)
        led_matrix.show()
        
        if display.time_to_refresh == 0.0:
            displayVoltage()
            time.sleep(1)
            printm(f'Size of display_data: {len(display_data)}')
        
        time.sleep(1)
    if touch_3.value:
        # Set LED to green
        led_matrix.fill(led_green)
        led_matrix.show()

        if display.time_to_refresh == 0.0:
            
            displayQR()
            time.sleep(1)
            printm(f'Size of display_data: {len(display_data)}')
        
    if touch_4.value:
        # Set LED to blue
        led_matrix.fill(led_blue)
        led_matrix.show()
        
        if display.time_to_refresh == 0.0:
            
            displayFigure()
            time.sleep(1)
            printm(f'Size of display_data: {len(display_data)}')
        
    if touch_5.value:
        # Turn off the LED
        led_matrix.fill(led_purple)
        led_matrix.show()
        # printBatteryState(get_batery_State)
        # display_data.append(displayio.TileGrid(display_background, pixel_shader = display_color_palette))
        # printMakerDescription('Denys', 'Timoshyn', '')
    
    printm(f'{display.time_to_refresh}')
    if display.busy:
        printm('Display is busy')
    else:
        printm('Display is not busy')
    while display.busy:
        time.sleep(0.5)
        pass
    time.sleep(0.5)