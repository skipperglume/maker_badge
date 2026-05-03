import time
import board
import digitalio
import os
import wifi
import socketpool
import analogio
import touchio
import displayio
import terminalio
import adafruit_ssd1680
from adafruit_display_text import label


TRANSIENT_SOCKET_ERRNOS = (11, 110, 116)

enable_display = digitalio.DigitalInOut(board.D16)
enable_display.direction = digitalio.Direction.OUTPUT
enable_display.value = False

WIFI_SSID = "skipperglume"
WIFI_PASSWORD = "shashasha"



BATTERY_DIVIDER_COEFF = 2.0
BATTERY_MIN_VOLTAGE = 3.2
BATTERY_MAX_VOLTAGE = 4.2

BUTTON_PINS = [board.D5, board.D4, board.D3, board.D2, board.D1]
BUTTON_NAMES = ["BTN1", "BTN2", "BTN3", "BTN4", "BTN5"]
TOUCH_THRESHOLD_SCALE = 1.35
TOUCH_THRESHOLD_MIN_DELTA = 250

# D14 enables the battery divider transistor: LOW enables, HIGH disables.
battery_en = digitalio.DigitalInOut(board.D14)
battery_en.direction = digitalio.Direction.OUTPUT
battery_en.value = True
battery_adc = analogio.AnalogIn(board.D6)
buttons = [touchio.TouchIn(pin) for pin in BUTTON_PINS]

# Raise thresholds so accidental/light touches do not trigger as easily.
for button in buttons:
  baseline = getattr(button, "raw_value", 0)
  current_threshold = getattr(button, "threshold", baseline)
  scaled_threshold = int(current_threshold * TOUCH_THRESHOLD_SCALE)
  min_from_baseline = int(baseline + TOUCH_THRESHOLD_MIN_DELTA)
  button.threshold = max(scaled_threshold, min_from_baseline)

# ePaper display constants
DISPLAY_BLACK = 0x000000
DISPLAY_WHITE = 0xFFFFFF
DISPLAY_WIDTH = 250
DISPLAY_HEIGHT = 122

# Initialize ePaper display hardware (same wiring as custom/code.py)
_board_spi = board.SPI()
_epd_cs = board.D41
_epd_dc = board.D40
_epd_reset = board.D39
_epd_busy = board.D42

displayio.release_displays()
_display_bus = displayio.FourWire(
    _board_spi, command=_epd_dc, chip_select=_epd_cs, reset=_epd_reset, baudrate=1000000
)
time.sleep(0.5)
display = adafruit_ssd1680.SSD1680(
    _display_bus,
    width=DISPLAY_WIDTH,
    height=DISPLAY_HEIGHT,
    rotation=270,
    busy_pin=_epd_busy,
    seconds_per_frame=5,
)

# Shared display group and white background tile
_display_data = displayio.Group()
_display_bg_bitmap = displayio.Bitmap(DISPLAY_WIDTH, DISPLAY_HEIGHT, 1)
_display_palette = displayio.Palette(1)
_display_palette[0] = DISPLAY_WHITE
_background = displayio.TileGrid(_display_bg_bitmap, pixel_shader=_display_palette)


def _display_add_text(text, scale, color, x, y):
    """Append a scaled text label to the shared display group."""
    group = displayio.Group(scale=scale, x=x, y=y)
    text_label = label.Label(terminalio.FONT, text=text, color=color)
    group.append(text_label)
    _display_data.append(group)


def _display_clear():
    """Clear all display group entries and restore the white background."""
    while len(_display_data) > 0:
        _display_data.pop()
    _display_data.append(_background)


def read_battery_state():
    """Return measured battery voltage and estimated percentage."""
    battery_en.value = False
    raw = battery_adc.value
    battery_en.value = True

    adc_voltage = raw * (3.3 / 65535)
    battery_voltage = adc_voltage * BATTERY_DIVIDER_COEFF

    normalized = (battery_voltage - BATTERY_MIN_VOLTAGE) / (
        BATTERY_MAX_VOLTAGE - BATTERY_MIN_VOLTAGE
    )
    if normalized < 0:
        normalized = 0
    if normalized > 1:
        normalized = 1

    return {
        "raw": raw,
        "adc_voltage": adc_voltage,
        "battery_voltage": battery_voltage,
        "battery_percent": int(normalized * 100),
    }


def read_buttons_state():
    """Return current pressed state and raw integer value for each touch button."""
    states = []
    for button in buttons:
        states.append(
            {
                "pressed": bool(button.value),
                "raw": int(getattr(button, "raw_value", 0)),
            }
        )
    return states


def build_button_rows(button_states):
    """Return HTML rows for touch button state and raw values."""
    html = ""
    for index, state in enumerate(button_states):
        pressed = state["pressed"]
        raw = state["raw"]
        state_label = "PRESSED" if pressed else "RELEASED"
        square_class = "square-on" if pressed else "square-off"
        html += (
            '<div class="btn-row"><span>{}</span><span class="btn-state"><span class="square {}"></span>{} ({})</span></div>\n'.format(
                BUTTON_NAMES[index], square_class, state_label, raw
            )
        )
    return html





def build_html(state, button_states):
    """Render a compact HTML page with battery telemetry and button state."""
    button_rows_html = build_button_rows(button_states)
    page = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <meta http-equiv=\"refresh\" content=\"5\" />
  <title>Maker Badge Battery</title>
  <style>
    :root {{
      --bg: #f5f7ef;
      --panel: #ffffff;
      --ink: #1e2c2d;
      --muted: #53666a;
      --good: #1c8b5f;
    }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 20% 10%, #e4edd8, var(--bg));
      font-family: "Verdana", "Trebuchet MS", sans-serif;
      color: var(--ink);
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 16px;
    }}
    .card {{
      width: min(420px, 100%);
      background: var(--panel);
      border: 2px solid #d8dfcc;
      border-radius: 14px;
      padding: 18px;
      box-shadow: 0 10px 24px rgba(30, 44, 45, 0.10);
    }}
    h1 {{
      margin: 0 0 10px 0;
      font-size: 1.2rem;
      letter-spacing: 0.02em;
    }}
    .big {{
      font-size: 2.4rem;
      line-height: 1;
      font-weight: 700;
      color: var(--good);
      margin: 2px 0 12px 0;
    }}
    .row {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 6px 0;
      border-top: 1px dashed #d8dfcc;
      font-size: 0.95rem;
    }}
    .section-title {{
      margin: 14px 0 4px 0;
      font-size: 0.95rem;
      color: var(--muted);
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }}
    .btn-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 6px 0;
      border-top: 1px dashed #d8dfcc;
      font-size: 0.95rem;
    }}
    .btn-state {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      letter-spacing: 0.01em;
    }}
    .square {{
      width: 12px;
      height: 12px;
      border-radius: 3px;
      border: 1px solid rgba(0, 0, 0, 0.2);
      display: inline-block;
    }}
    .square-on {{
      background: #1c8b5f;
    }}
    .square-off {{
      background: #c83f3f;
    }}
    .muted {{
      color: var(--muted);
      font-size: 0.85rem;
      margin-top: 12px;
    }}
  </style>
</head>
<body>
  <main class=\"card\">
    <h1>Maker Badge Battery</h1>
    <div class=\"big\">{percent}%</div>
    <div class=\"row\"><span>Battery voltage</span><strong>{voltage:.3f} V</strong></div>
    <div class=\"row\"><span>ADC voltage</span><strong>{adc:.3f} V</strong></div>
    <div class=\"row\"><span>Raw ADC</span><strong>{raw}</strong></div>
    <p class=\"section-title\">Touch Buttons</p>
    {button_rows}
    <p class=\"muted\">Auto-refresh every 5 s.</p>
  </main>
</body>
</html>
""".format(
        percent=state["battery_percent"],
        voltage=state["battery_voltage"],
        adc=state["adc_voltage"],
        raw=state["raw"],
        button_rows=button_rows_html,
    )
    return page

def send_http_response(client, body):
    payload = body.encode("utf-8")
    headers = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n"
        "Content-Length: {}\r\n"
        "\r\n"
    ).format(len(payload)).encode("utf-8")

    packet = headers + payload
    sent = 0
    retries = 0
    while sent < len(packet):
        try:
            sent_now = client.send(packet[sent:])
        except OSError as exc:
            err = exc.args[0] if exc.args else None
            if err in TRANSIENT_SOCKET_ERRNOS and retries < 20:
                retries += 1
                time.sleep(0.01)
                continue
            raise

        if sent_now is None:
            sent_now = 0
        if sent_now <= 0:
            if retries < 20:
                retries += 1
                time.sleep(0.01)
                continue
            raise RuntimeError("Socket send stalled before full response was transmitted")

        sent += sent_now
        retries = 0


def read_http_request(client):
    """Read and discard one HTTP request in a CircuitPython-safe way."""
    # Some CircuitPython socket implementations do not provide recv(),
    # but they do provide recv_into().
    buf = bytearray(1024)
    try:
        if hasattr(client, "recv_into"):
            return client.recv_into(buf)
        if hasattr(client, "recv"):
            data = client.recv(1024)
            return len(data) if data else 0
    except OSError as exc:
        # EAGAIN / timeout can happen on non-blocking socket reads.
        # Treat this as an empty request and continue serving a response.
        err = exc.args[0] if exc.args else None
        if err in TRANSIENT_SOCKET_ERRNOS:
            return 0
        raise
    return 0

def connect_wifi():
    if WIFI_SSID == "YOUR_WIFI_SSID" or WIFI_PASSWORD == "YOUR_WIFI_PASSWORD":
        raise RuntimeError(
            "Set CIRCUITPY_WIFI_SSID/CIRCUITPY_WIFI_PASSWORD in settings.toml "
            "or edit WIFI_SSID/WIFI_PASSWORD in code_wifi.py"
        )

    print("Connecting to Wi-Fi...")
    wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
    print("Connected.")
    print("IP:", wifi.radio.ipv4_address)

    result = {'result': 'Connected', 'IP': str(wifi.radio.ipv4_address)}


def show_client_on_display(address):
    """Display connected client IP and port on the Maker Badge ePaper screen."""
    try:
        client_ip = str(address[0]) if isinstance(address, tuple) and len(address) > 0 else str(address)
        client_port = str(address[1]) if isinstance(address, tuple) and len(address) > 1 else "-"

        enable_display.value = False  # Power on (transistor active low)

        # Wait for display to be ready if it is still refreshing
        while display.time_to_refresh > 0:
            time.sleep(0.1)

        home_ip = str(wifi.radio.ipv4_address)

        _display_clear()
        _display_add_text(home_ip, 2, DISPLAY_BLACK, 10, 10)
        _display_add_text(client_ip, 2, DISPLAY_BLACK, 10, 40)
        _display_add_text("port " + client_port, 2, DISPLAY_BLACK, 10, 70)

        display.show(_display_data)
        display.refresh()
    except Exception as exc:
        print("Display update error:", exc)


def run_server():
    method_name = 'run_server'

    connect_wifi()

    pool = socketpool.SocketPool(wifi.radio)
    server = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    server.bind(("0.0.0.0", 80))
    server.listen(1)

    print("HTTP server running on http://{}/".format(wifi.radio.ipv4_address))

    while True:
        # 
        client, address = server.accept() # Wait for a client to connect


        print(f"Client connected: {address}")
        show_client_on_display(address)

        try:
            print(f"Client: [{address}]" )
            if hasattr(client, "settimeout"):
                client.settimeout(3)
                _ = read_http_request(client)

            state = read_battery_state()
            button_states = read_buttons_state()
            page = build_html(state, button_states)
            send_http_response(client, page)
        except Exception as exc:
            print("Request error:", exc)
        finally:
            try:
                client.close()
            except Exception:
                pass

        time.sleep(0.01)


run_server()