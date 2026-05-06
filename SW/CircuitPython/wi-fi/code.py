import time
import board
import digitalio
import os
import wifi
import socketpool
import analogio
import touchio
import neopixel
import displayio
import terminalio
import adafruit_ssd1680
from adafruit_display_text import label
import gc


TRANSIENT_SOCKET_ERRNOS = (11, 110, 116)

enable_display = digitalio.DigitalInOut(board.D16)
enable_display.direction = digitalio.Direction.OUTPUT
enable_display.value = False

WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID", "")
WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD", "")
SERVER_PORT = 8080
CLIENT_READ_TIMEOUT_S = 0.2
DISPLAY_CLIENT_UPDATE_MIN_INTERVAL_S = 1.0
HTTP_HEADER_CHUNK_SIZE = 128
HTTP_BODY_CHUNK_SIZE = 128
HTTP_SEND_MAX_RETRIES = 800
HTTP_SEND_RETRY_DELAY_S = 0.005



BATTERY_DIVIDER_COEFF = 2.0
BATTERY_MIN_VOLTAGE = 3.2
BATTERY_MAX_VOLTAGE = 4.2

BUTTON_PINS = [board.D5, board.D4, board.D3, board.D2, board.D1]
BUTTON_NAMES = ["BTN1", "BTN2", "BTN3", "BTN4", "BTN5"]
TOUCH_THRESHOLD_SCALE = 1.35
TOUCH_THRESHOLD_MIN_DELTA = 250

_last_client_display_ts = 0.0
_last_client_display_key = ""

# D14 enables the battery divider transistor: LOW enables, HIGH disables.
battery_en = digitalio.DigitalInOut(board.D14)
battery_en.direction = digitalio.Direction.OUTPUT
battery_en.value = True
battery_adc = analogio.AnalogIn(board.D6)
buttons = [touchio.TouchIn(pin) for pin in BUTTON_PINS]

LED_PIN = board.D18
LED_COUNT = 4
LED_BRIGHTNESS = 0.1
led_matrix = neopixel.NeoPixel(
    LED_PIN, LED_COUNT, brightness=LED_BRIGHTNESS, auto_write=False
)

# Raise thresholds so accidental/light touches do not trigger as easily.
for button in buttons:
    # baseline = getattr(button, "raw_value", 0)
    # current_threshold = getattr(button, "threshold", baseline)
    baseline = 11000
    current_threshold = baseline
    scaled_threshold = int(current_threshold * TOUCH_THRESHOLD_SCALE)
    min_from_baseline = int(baseline + TOUCH_THRESHOLD_MIN_DELTA)
    baseline
    print(baseline)
    print(current_threshold)
    print(baseline)
    print(min_from_baseline)
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


def buttons_to_color(button_states):
    """Map the active button combination to a unique RGB color.

    Each of the 32 possible combinations gets a distinct hue on the
    color wheel (full saturation, full brightness). No buttons pressed
    returns black (0, 0, 0).
    """
    mask = 0
    for index, state in enumerate(button_states):
        if state["pressed"]:
            mask |= 1 << index

    if mask == 0:
        return (0, 0, 0)

    # Map 1-31 evenly across the full hue wheel (0.0 - 1.0)
    hue = (mask - 1) / 31.0

    # HSV -> RGB  (S=1, V=1)
    h6 = hue * 6.0
    i = int(h6) % 6
    f = h6 - int(h6)
    t = int(f * 255)
    q = int((1.0 - f) * 255)
    if i == 0: return (255, t, 0)
    if i == 1: return (q, 255, 0)
    if i == 2: return (0, 255, t)
    if i == 3: return (0, q, 255)
    if i == 4: return (t, 0, 255)
    
    return (255, 0, q)


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


def update_led_matrix(button_states):
    """Show the current button-combination color on all badge LEDs."""
    mix_color = buttons_to_color(button_states)
    led_matrix.fill(mix_color)
    led_matrix.show()





def build_html(state, button_states):
    """Render a lightweight HTML page with battery telemetry and button state."""
    button_rows_html = build_button_rows(button_states)
    r, g, b = buttons_to_color(button_states)
    mix_color_hex = "#{:02X}{:02X}{:02X}".format(r, g, b)
    mix_label = mix_color_hex if (r or g or b) else "none"
    page = """<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta http-equiv=\"refresh\" content=\"5\"><title>Maker Badge</title><style>body{{font-family:Verdana,sans-serif;margin:0;padding:12px;background:#f5f7ef;color:#1e2c2d}}.card{{max-width:420px;margin:auto;background:#fff;border:1px solid #d8dfcc;border-radius:10px;padding:12px}}.big{{font-size:2rem;font-weight:700;color:#1c8b5f;margin:8px 0}}.row,.btn-row{{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-top:1px dashed #d8dfcc}}.square{{width:10px;height:10px;border-radius:2px;display:inline-block;margin-right:6px}}.square-on{{background:#1c8b5f}}.square-off{{background:#c83f3f}}.sw{{width:14px;height:14px;border:1px solid #888;border-radius:3px;display:inline-block;vertical-align:middle;margin-right:6px}}.btn{{display:block;width:100%;margin-top:8px;padding:8px 10px;border:0;border-radius:8px;background:#1e2c2d;color:#fff;font-weight:700}}</style></head><body><main class=\"card\"><h2>Maker Badge Battery</h2><div class=\"big\">{percent}%</div><div class=\"row\"><span>Battery</span><strong>{voltage:.3f} V</strong></div><div class=\"row\"><span>ADC</span><strong>{adc:.3f} V</strong></div><div class=\"row\"><span>Raw</span><strong>{raw}</strong></div><div class=\"row\"><span>Mix</span><strong><span class=\"sw\" style=\"background:{mix_color}\"></span>{mix_label}</strong></div>{button_rows}<button class=\"btn\" type=\"button\" onclick=\"location.reload()\">Refresh</button></main></body></html>""".format(
        percent=state["battery_percent"],
        voltage=state["battery_voltage"],
        adc=state["adc_voltage"],
        raw=state["raw"],
        button_rows=button_rows_html,
        mix_color=mix_color_hex,
        mix_label=mix_label,
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

    def _send_with_retry(data, chunk_size, max_retries):
        sent = 0
        retries = 0
        while sent < len(data):
            end = sent + chunk_size
            view = memoryview(data)[sent:end]
            try:
                sent_now = client.send(view)
            except OSError as exc:
                err = exc.args[0] if exc.args else None
                if err in TRANSIENT_SOCKET_ERRNOS and retries < max_retries:
                    retries += 1
                    time.sleep(HTTP_SEND_RETRY_DELAY_S)
                    continue
                return False

            if sent_now is None:
                sent_now = 0

            if sent_now <= 0:
                if retries < max_retries:
                    retries += 1
                    time.sleep(HTTP_SEND_RETRY_DELAY_S)
                    continue
                return False

            sent += sent_now
            retries = 0
            # Give Wi-Fi stack a brief chance to drain buffers on tiny devices.
            time.sleep(0.001)
        return True

    if not _send_with_retry(headers, HTTP_HEADER_CHUNK_SIZE, HTTP_SEND_MAX_RETRIES):
        return False
    if not _send_with_retry(payload, HTTP_BODY_CHUNK_SIZE, HTTP_SEND_MAX_RETRIES):
        return False
    return True


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
    if not WIFI_SSID or not WIFI_PASSWORD:
        raise RuntimeError(
            "Set CIRCUITPY_WIFI_SSID and CIRCUITPY_WIFI_PASSWORD in /CIRCUITPY/settings.toml"
        )

    print("Connecting to Wi-Fi...")
    wifi.radio.connect(WIFI_SSID, WIFI_PASSWORD)
    print("Connected.")
    print("IP:", wifi.radio.ipv4_address)

    result = {'result': 'Connected', 'IP': str(wifi.radio.ipv4_address)}


def show_connecting_on_display(ssid):
    """Display the network name the badge is trying to connect to."""
    try:
        enable_display.value = False  # Power on (transistor active low)

        while display.time_to_refresh > 0:
            time.sleep(0.1)

        ip_text = str(wifi.radio.ipv4_address) if wifi.radio.ipv4_address else "0.0.0.0"
        url_text = "{}:{}".format(ip_text, SERVER_PORT)

        _display_clear()
        _display_add_text("Connecting to:", 2, DISPLAY_BLACK, 10, 10)
        _display_add_text(ssid, 2, DISPLAY_BLACK, 10, 35)
        _display_add_text(url_text, 2, DISPLAY_BLACK, 10, 70)

        display.show(_display_data)
        display.refresh()
    except Exception as exc:
        print("Display update error:", exc)


def show_client_on_display(address):
    """Display connected client IP and port on the Maker Badge ePaper screen."""
    global _last_client_display_ts, _last_client_display_key
    try:
        client_ip = str(address[0]) if isinstance(address, tuple) and len(address) > 0 else str(address)
        client_port = str(address[1]) if isinstance(address, tuple) and len(address) > 1 else "-"
        display_key = client_ip + ":" + client_port

        now = time.monotonic()
        if display_key == _last_client_display_key and (now - _last_client_display_ts) < DISPLAY_CLIENT_UPDATE_MIN_INTERVAL_S:
            return

        if display.time_to_refresh > 0:
            # Do not block request handling while ePaper is refreshing.
            return

        enable_display.value = False  # Power on (transistor active low)

        home_ip = str(wifi.radio.ipv4_address)

        _display_clear()
        _display_add_text(home_ip, 2, DISPLAY_BLACK, 10, 10)
        _display_add_text(client_ip, 2, DISPLAY_BLACK, 10, 40)
        _display_add_text("port " + client_port, 2, DISPLAY_BLACK, 10, 70)

        display.show(_display_data)
        display.refresh()
        _last_client_display_ts = now
        _last_client_display_key = display_key
    except Exception as exc:
        print("Display update error:", exc)


def run_server():

    method_name = 'run_server'

    show_connecting_on_display(WIFI_SSID)
    time.sleep(0.02)
    connect_wifi()



    pool = socketpool.SocketPool(wifi.radio)
    server = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    server.bind(("0.0.0.0", SERVER_PORT))
    server.listen(1)

    print(f"[{method_name}] HTTP server running on http://{wifi.radio.ipv4_address}:{SERVER_PORT}/")

    while True:
        gc.collect()
        # 
        client, address = server.accept() # Wait for a client to connect


        print(f"[{method_name}] Client connected: {address}")
        show_client_on_display(address)

        try:
            t_read_ms = 0.0
            print(f"[{method_name}] Client: [{address}]" )
            if hasattr(client, "settimeout"):
                client.settimeout(CLIENT_READ_TIMEOUT_S)
                t_read_start = time.monotonic()
                _ = read_http_request(client)
                t_read_ms = (time.monotonic() - t_read_start) * 1000.0
                print(f"[{method_name}] read_request_ms={t_read_ms:.1f}")

            state = read_battery_state()
            button_states = read_buttons_state()
            update_led_matrix(button_states)

            t_build_start = time.monotonic()
            try:
                page = build_html(state, button_states)
            except MemoryError:
                gc.collect()
                page = "<!doctype html><html><body><h3>Low memory</h3><p>Retry in a moment.</p></body></html>"
            t_build_ms = (time.monotonic() - t_build_start) * 1000.0
            print("build_html_ms={:.1f}  page_bytes={}".format(t_build_ms, len(page)))

            if hasattr(client, "settimeout"):
                client.settimeout(None)  # switch to blocking mode before send
            t_send_start = time.monotonic()
            response_ok = send_http_response(client, page)
            t_send_ms = (time.monotonic() - t_send_start) * 1000.0
            print("send_response_ms={:.1f}".format(t_send_ms))
            if not response_ok:
                print("send_response_status=partial")
            else:
                print("send_response_status=ok")

            print("total_request_ms={:.1f}".format(t_read_ms + t_build_ms + t_send_ms))
        except Exception as exc:
            err = exc.args[0] if hasattr(exc, "args") and exc.args else None
            if err in TRANSIENT_SOCKET_ERRNOS:
                print("Transient socket backpressure; request dropped")
            else:
                print("Request error:", exc)
        finally:
            try:
                client.close()
            except Exception:
                pass
            gc.collect()

        time.sleep(0.01)


run_server()