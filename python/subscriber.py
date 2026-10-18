import json, time
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

TOPIC = "ptit/b23dccn224/lab2/+/telemetry"

db = InfluxDBClient(
    url="http://localhost:8086",
    token="bNmVK4GBk7i1aL2r5Yg3SGWbPHvwmtovTitvVLqse7Cut582Wod4pZNbY3ilQY7OLkJju1P2H1apAtoACUM8-Q==",
    org="ptit"
)
write = db.write_api(write_options=SYNCHRONOUS)

RANGES = {"temperature": (-40, 80), "humidity": (0, 100), "distance_cm": (2, 400)}
last_seq = {}

def valid(d):
    for k, (lo, hi) in RANGES.items():
        v = d.get(k)
        if not isinstance(v, (int, float)) or not (lo <= v <= hi):
            return False
    return True

def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected to broker")
    client.subscribe(TOPIC, qos=1)

def on_message(client, userdata, msg):
    recv = time.time()
    try:
        d = json.loads(msg.payload)
    except json.JSONDecodeError:
        print("Bad JSON"); return

    if not valid(d):
        print("Invalid data, skip:", d); return

    dev = d.get("device_id", "unknown")
    seq = d.get("sequence", 0)

    if last_seq.get(dev) == seq:
        print("Duplicate, skip"); return
    if dev in last_seq and seq > last_seq[dev] + 1:
        print(f"Lost {seq - last_seq[dev] - 1} packet(s)")
    last_seq[dev] = seq

    ts = d.get("ts", recv)
    latency = (recv - ts) * 1000

    p = (Point("environment")
         .tag("device_id", dev)
         .field("temperature",  float(d["temperature"]))
         .field("humidity",     float(d["humidity"]))
         .field("distance_cm",  float(d["distance_cm"]))
         .field("rssi",         int(d["rssi"]))
         .field("sequence",     int(seq))
         .field("latency_ms",   latency)
         .time(int(recv * 1e9), WritePrecision.NS))

    try:
        write.write(bucket="iot", record=p)
        print(f"Written: temp={d['temperature']} hum={d['humidity']} dist={d['distance_cm']} latency={latency:.0f}ms")
    except Exception as e:
        print("Write error:", e)

cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
cl.on_connect = on_connect
cl.on_message = on_message
cl.connect("broker.hivemq.com", 1883, keepalive=60)
cl.loop_forever()