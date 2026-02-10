# tools/sub_incoming_gear.py
import zenoh
from zenoh_ros_type.tier4_autoware_msgs import GearShiftStamped
s = zenoh.open(config=zenoh.Config.from_file('config.json5'))
scope = 'v1'
keys = [
    scope + '/api/external/set/command/remote/shift',
    scope + '/external/selected/gear_cmd',
    scope + '/control/command/gear_cmd'
]
def make_cb(k):
    def cb(sample):
        print(f'[IN] {k} <{len(sample.payload.to_bytes())} bytes>')
        try:
            data = GearShiftStamped.deserialize(sample.payload.to_bytes())
            print('  parsed GearShiftStamped ->', data.gear_shift.data)
        except Exception as e:
            print('  parse failed:', e)
    return cb

subs = [s.declare_subscriber(k, make_cb(k)) for k in keys]
print('Subscribed to input keys:', keys)
import time
while True:
    time.sleep(1)