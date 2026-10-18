import pandas as pd
import numpy as np
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

TOKEN = "bNmVK4GBk7i1aL2r5Yg3SGWbPHvwmtovTitvVLqse7Cut582Wod4pZNbY3ilQY7OLkJju1P2H1apAtoACUM8-Q=="
ORG   = "ptit"

db = InfluxDBClient(url="http://localhost:8086", token=TOKEN, org=ORG)

# 1) Đọc dữ liệu từ bucket raw
query = '''
from(bucket:"iot")
  |> range(start: -1h)
  |> filter(fn:(r) => r._measurement == "environment")
  |> filter(fn:(r) => r._field == "temperature" or r._field == "humidity" or r._field == "distance_cm")
  |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
'''
df = db.query_api().query_data_frame(query)

if df.empty:
    print("Không có dữ liệu, chạy subscriber trước rồi thử lại")
    exit()

print(f"Dữ liệu gốc: {len(df)} điểm")

# Giữ lại cột cần thiết
df = df[["_time","temperature","humidity","distance_cm"]].copy()
df = df.set_index("_time").sort_index()

# 2) Resample 2s, xử lý missing values
df = df.resample("2s").mean().interpolate("time", limit=5)
print(f"Sau resample: {len(df)} điểm")

# 3) Phát hiện và xử lý outlier bằng IQR
for col in ["temperature","humidity","distance_cm"]:
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    mask = (df[col] < q1 - 1.5*iqr) | (df[col] > q3 + 1.5*iqr)
    print(f"  {col}: phát hiện {int(mask.sum())} outlier")
    df.loc[mask, col] = np.nan
df = df.interpolate("time")

# 4) Rolling mean và delta
for col in ["temperature","humidity","distance_cm"]:
    df[col+"_roll"] = df[col].rolling(3, min_periods=1).mean()
    df[col+"_delta"] = df[col].diff().fillna(0)

# 5) Chuẩn hóa min-max
from sklearn.preprocessing import MinMaxScaler
base_cols = ["temperature","humidity","distance_cm"]
df[[c+"_norm" for c in base_cols]] = MinMaxScaler().fit_transform(df[base_cols])

print(f"Các cột sau xử lý: {list(df.columns)}")

# 6) Ghi vào bucket processed
write = db.write_api(write_options=SYNCHRONOUS)
count = 0
for ts, row in df.iterrows():
    p = Point("environment_clean").tag("device_id","node01").time(ts)
    for k, v in row.items():
        if pd.notna(v):
            p.field(k, float(v))
    write.write(bucket="processed", record=p)
    count += 1

print(f"Đã ghi {count} điểm vào bucket processed")
db.close()