import json
import time
import zenoh
import threading
import sys
import os
import math 
# --- IMPORTS ---
# We use the files you already have. 
# We use Tier4 definitions to read Universe data where compatible (TurnSignal).
try:
    # 1. Load Tier4 Types (For CPU & Turn Signal)
    from zenoh_ros_type.tier4_autoware_msgs import (
        CpuUsage, 
        CpuStatus, 
        TurnSignalStamped, # We will use this to read the Universe Turn message
        Time
    )
    # 2. Load Auto Types (For Gear, Steering, Velocity - you have these)
    from zenoh_ros_type.autoware_auto_msgs import (
        GearReport, 
        SteeringReport, 
        VelocityReport
    )
except ImportError:
    # Fallback for running as a script directly
    from zenoh_ros_type.tier4_autoware_msgs import CpuUsage, CpuStatus, TurnSignalStamped, Time
    from zenoh_ros_type.autoware_auto_msgs import GearReport, SteeringReport, VelocityReport


# --- CONFIGURATION ---
TOPIC_CPU       = '/api/external/get/cpu_usage'
TOPIC_GEAR      = '/vehicle/status/gear_status'
TOPIC_TURN      = '/vehicle/status/turn_indicators_status'
TOPIC_STEER     = '/vehicle/status/steering_status'
TOPIC_VELOCITY  = '/vehicle/status/velocity_status'

# --- GLOBAL CACHE ---
VEHICLE_CACHE = {}
ACTIVE_SUBSCRIBERS = {}

def class2dict(instance):
    if not hasattr(instance, '__dict__'):
        return instance
    new_subdic = vars(instance)
    for key, value in new_subdic.items():
        if isinstance(new_subdic[key], list):
            for i in range(len(new_subdic[key])):
                new_subdic[key][i] = class2dict(new_subdic[key][i])
        else:
            new_subdic[key] = class2dict(round(value, 4)) if isinstance(value, float) else class2dict(value)
    return new_subdic

# --- CALLBACKS ---

def callback_cpu(sample, scope):
    try:
        data = CpuUsage.deserialize(sample.payload.to_bytes())
        d = class2dict(data)
        try:
            d['all']['status'] = CpuStatus.STATUS(d['all']['status']).name
            print(d['all']['status'])
            for i in range(len(d['cpus'])):
                d['cpus'][i]['status'] = CpuStatus.STATUS(d['cpus'][i]['status']).name
        except: pass
        
        if scope not in VEHICLE_CACHE: VEHICLE_CACHE[scope] = {}
        VEHICLE_CACHE[scope]['cpu'] = d
    except Exception:
        pass 

def callback_gear(sample, scope):
    try:
        # Use GearReport (from your autoware_auto_vehicle_msgs.py)
        data = GearReport.deserialize(sample.payload.to_bytes())
        val = data.report 
        
        gear_str = "UNKNOWN"
        # Universe Constants
        if val == 2: gear_str = "DRIVE"
        elif val == 20 or val == 3: gear_str = "REVERSE"
        elif val == 22 or val == 4: gear_str = "PARKING"
        elif val == 1: gear_str = "NEUTRAL"
        elif val == 0: gear_str = "NONE"
        
        if scope not in VEHICLE_CACHE: VEHICLE_CACHE[scope] = {}
        VEHICLE_CACHE[scope]['gear'] = gear_str
    except Exception as e:
        print(f"[ERROR] Gear Parse: {e}")

def callback_turn(sample, scope):
    try:
        # HERE IS THE FIX: Use TurnSignalStamped (from your tier4_external_api_msgs.py)
        # It fits the binary data perfectly.
        data = TurnSignalStamped.deserialize(sample.payload.to_bytes())
        
        # We access .turn_signal.data as you suggested
        val = data.turn_signal.data
        
        turn_str = "NONE"
        # Universe Constants (1=Left, 2=Right)
        if val == 1: turn_str = "LEFT" 
        elif val == 2: turn_str = "RIGHT"
        elif val == 3: turn_str = "RIGHT" 
        
        if scope not in VEHICLE_CACHE: VEHICLE_CACHE[scope] = {}
        VEHICLE_CACHE[scope]['turn'] = turn_str
    except Exception as e:
        print(f"[ERROR] Turn Parse: {e}")

def callback_steering(sample, scope):
    try:
        # Use SteeringReport (from your autoware_auto_vehicle_msgs.py)
        data = SteeringReport.deserialize(sample.payload.to_bytes())
        val = data.steering_tire_angle
        val= val*(180.0/math.pi)  # Convert to degrees
        val= round(val,2)
        
        if scope not in VEHICLE_CACHE: VEHICLE_CACHE[scope] = {}
        VEHICLE_CACHE[scope]['steer'] = val
    except Exception as e:
        print(f"[ERROR] Steer Parse: {e}")

def callback_velocity(sample, scope):
    try:
        # Use VelocityReport (from your autoware_auto_vehicle_msgs.py)
        data = VelocityReport.deserialize(sample.payload.to_bytes())
        val = data.longitudinal_velocity
        val= val*(3.6)  # Convert to km/h
        val= round(val,2)
        
        if scope not in VEHICLE_CACHE: VEHICLE_CACHE[scope] = {}
        VEHICLE_CACHE[scope]['vel'] = val
    except Exception as e:
        print(f"[ERROR] Vel Parse: {e}")


# --- MANAGER ---
def ensure_subscribers(session, scope, use_bridge_ros2dds):
    if scope in ACTIVE_SUBSCRIBERS:
        return 

    print(f"\n[INIT] Starting background subscribers for {scope}...")
    ACTIVE_SUBSCRIBERS[scope] = {}
    if scope not in VEHICLE_CACHE: VEHICLE_CACHE[scope] = {}

    prefix = scope if use_bridge_ros2dds else scope + '/rt'

    def create_sub(topic, callback):
        full_key = prefix + topic
        sub = session.declare_subscriber(full_key, lambda s: callback(s, scope))
        return sub

    ACTIVE_SUBSCRIBERS[scope]['cpu']   = create_sub(TOPIC_CPU, callback_cpu)
    ACTIVE_SUBSCRIBERS[scope]['gear']  = create_sub(TOPIC_GEAR, callback_gear)
    ACTIVE_SUBSCRIBERS[scope]['turn']  = create_sub(TOPIC_TURN, callback_turn)
    ACTIVE_SUBSCRIBERS[scope]['steer'] = create_sub(TOPIC_STEER, callback_steering)
    ACTIVE_SUBSCRIBERS[scope]['vel']   = create_sub(TOPIC_VELOCITY, callback_velocity)
    
    print(f"[INIT] Subscribers active for {scope}")


# --- API FUNCTIONS ---

def get_cpu_status(session, scope, use_bridge_ros2dds=True):
    ensure_subscribers(session, scope, use_bridge_ros2dds)
    default_cpu = {'all': {'status': 'WAIT', 'total': 0.0, 'sys':0.0, 'usr':0.0, 'idle':0.0}, 'cpus': []}
    return VEHICLE_CACHE.get(scope, {}).get('cpu', default_cpu)

def get_vehicle_status(session, scope, use_bridge_ros2dds=True):
    ensure_subscribers(session, scope, use_bridge_ros2dds)
    
    cache = VEHICLE_CACHE.get(scope, {})
    
    gear_str = cache.get('gear', "CONNECTING")
    turn_str = cache.get('turn', "NONE")
    steer_val = cache.get('steer', 0.0)
    vel_val = cache.get('vel', 0.0)
    
    # Construct Response for React App
    response = {
        'status': {
            'turn_signal': {'data': turn_str},
            'gear_shift': {'data': gear_str},
            'steering': {'data': steer_val},
            'twist': {
                'linear': {'x': vel_val}
            }
        }
    }
    return response