import time
import board
import digitalio
import os
import wifi
import socketpool
import analogio


enable_display = digitalio.DigitalInOut(board.D16)
enable_display.direction = digitalio.Direction.OUTPUT
enable_display.value = False

WIFI_SSID = "skipperglume"
WIFI_PASSWORD = "shashasha"



BATTERY_DIVIDER_COEFF = 2.0
BATTERY_MIN_VOLTAGE = 3.2
BATTERY_MAX_VOLTAGE = 4.2

# D14 enables the battery divider transistor: LOW enables, HIGH disables.
battery_en = digitalio.DigitalInOut(board.D14)
battery_en.direction = digitalio.Direction.OUTPUT
battery_en.value = True
battery_adc = analogio.AnalogIn(board.D6)


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


def build_html(state):
    """Render a compact HTML page with battery telemetry."""
    return """<!doctype html>
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
    <p class=\"muted\">Auto-refresh every 5 s.</p>
  </main>
</body>
</html>
""".format(
        percent=state["battery_percent"],
        voltage=state["battery_voltage"],
        adc=state["adc_voltage"],
        raw=state["raw"],
    )


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
    while sent < len(packet):
        sent += client.send(packet[sent:])


def read_http_request(client):
    """Read and discard one HTTP request in a CircuitPython-safe way."""
    # Some CircuitPython socket implementations do not provide recv(),
    # but they do provide recv_into().
    buf = bytearray(1024)
    if hasattr(client, "recv_into"):
      return client.recv_into(buf)
    if hasattr(client, "recv"):
      data = client.recv(1024)
      return len(data) if data else 0
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


def run_server():
    method_name = 'run_server'

    connect_wifi()

    pool = socketpool.SocketPool(wifi.radio)
    server = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    server.bind(("0.0.0.0", 80))
    server.listen(1)

    print("HTTP server running on http://{}/".format(wifi.radio.ipv4_address))

    while True:
        client, address = server.accept()
        try:
            print("Client:", address)
            if hasattr(client, "settimeout"):
                client.settimeout(1)
                _ = read_http_request(client)

            state = read_battery_state()
            page = build_html(state)
            send_http_response(client, page)
        except Exception as exc:
            print("Request error:", exc)
        finally:
            try:
                client.close()
            except Exception:
                pass

        time.sleep(0.05)


run_server()