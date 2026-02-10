# tools/sub_vehicle_gear_status.py
import zenoh
from zenoh_ros_type.autoware_auto_msgs import GearReport
s = zenoh.open(config=zenoh.Config.from_file('config.json5'))
scope = 'v1'
key = scope + '/vehicle/status/gear_status'
def cb(sample):
    try:
        data = GearReport.deserialize(sample.payload.to_bytes())
        print('[STATUS] gear report value:', data.report)
    except Exception as e:
        print('parse error:', e)
s.declare_subscriber(key, cb)
print('Subscribed to', key)
import time
while True:
    time.sleep(1)