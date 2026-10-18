# config.py
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "bNmVK4GBk7i1aL2r5Yg3SGWbPHvwmtovTitvVLqse7Cut582Wod4pZNbY3ilQY7OLkJju1P2H1apAtoACUM8-Q=="
INFLUXDB_ORG = "ptit"
INFLUXDB_BUCKET_RAW = "iot"
INFLUXDB_BUCKET_PROCESSED = "processed"

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "ptit/b23dccn224/lab2/+/telemetry"