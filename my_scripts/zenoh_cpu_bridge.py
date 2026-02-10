#!/usr/bin/env python3
"""
Bridge that publishes CPU usage to Zenoh using zenoh_ros_type serialization.

This bridge:
1. Reads CPU usage from psutil
2. Creates zenoh_ros_type.tier4_autoware_msgs.CpuUsage messages
3. Publishes directly to Zenoh (not ROS2)

This bypasses the need for tier4_external_api_msgs and works with FMS directly.
"""

import json
import psutil
import time
import sys

import zenoh

# Import the EXACT message types that FMS expects
from zenoh_ros_type.tier4_autoware_msgs import CpuUsage, CpuStatus
from zenoh_ros_type.rcl_interfaces import Time


def create_cpu_usage_message():
    """Create a CpuUsage message matching FMS expectations."""
    
    # Get current time
    current_time = time.time()
    sec = int(current_time)
    nanosec = int((current_time - sec) * 1e9)
    stamp = Time(sec=sec, nanosec=nanosec)
    
    # Get per-CPU and aggregate CPU stats
    cpu_times_percent = psutil.cpu_times_percent(interval=0.1, percpu=True)
    cpu_times_all = psutil.cpu_times_percent(interval=0, percpu=False)
    
    # Create aggregate CpuStatus
    all_cpu = CpuStatus(
        status=0,  # STATUS_OK
        total=float(100.0 - cpu_times_all.idle),
        usr=float(cpu_times_all.user),
        nice=float(cpu_times_all.nice if hasattr(cpu_times_all, 'nice') else 0.0),
        sys=float(cpu_times_all.system),
        idle=float(cpu_times_all.idle)
    )
    
    # Create per-CPU CpuStatus list
    cpus = []
    for cpu_time in cpu_times_percent:
        cpu_status = CpuStatus(
            status=0,  # STATUS_OK
            total=float(100.0 - cpu_time.idle),
            usr=float(cpu_time.user),
            nice=float(cpu_time.nice if hasattr(cpu_time, 'nice') else 0.0),
            sys=float(cpu_time.system),
            idle=float(cpu_time.idle)
        )
        cpus.append(cpu_status)
    
    # Create CpuUsage message
    cpu_usage = CpuUsage(
        stamp=stamp,
        all=all_cpu,
        cpus=cpus
    )
    
    return cpu_usage


def main():
    """Main bridge loop."""
    
    # Configuration
    vehicle_name = 'v1'  # Your vehicle name from Autoware
    fms_endpoint = 'tcp/172.30.10.52:7887'  # FMS Zenoh endpoint
    publish_key = f'{vehicle_name}/api/external/get/cpu_usage'
    
    print(f"[Zenoh CPU Bridge] Starting...")
    print(f"  Vehicle: {vehicle_name}")
    print(f"  FMS Endpoint: {fms_endpoint}")
    print(f"  Publishing to: {publish_key}")
    print()
    
    try:
        # Connect to Zenoh (as a peer connecting to FMS)
        conf = zenoh.Config()
        endpoints = [fms_endpoint]
        conf.insert_json5('connect/endpoints', json.dumps(endpoints))
        
        session = zenoh.open(conf)
        print(f"[Zenoh CPU Bridge] Connected to Zenoh at {fms_endpoint}")
        
        # Create publisher
        publisher = session.declare_publisher(publish_key)
        print(f"[Zenoh CPU Bridge] Publisher declared for: {publish_key}")
        print(f"[Zenoh CPU Bridge] Starting to publish CPU usage...\n")
        
        # Publish loop
        iteration = 0
        while True:
            try:
                # Create message
                cpu_usage = create_cpu_usage_message()
                
                # Serialize to CDR format
                payload = cpu_usage.serialize()
                
                # Publish
                publisher.put(payload)
                
                iteration += 1
                if iteration % 10 == 0:  # Log every 10 iterations
                    print(f"[{iteration}] Published CPU usage: all={cpu_usage.all.total:.1f}% "
                          f"(usr={cpu_usage.all.usr:.1f}%, sys={cpu_usage.all.sys:.1f}%, idle={cpu_usage.all.idle:.1f}%), "
                          f"cores={len(cpu_usage.cpus)}")
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[ERROR] Failed to publish CPU usage: {e}")
                time.sleep(1)
        
        print("\n[Zenoh CPU Bridge] Shutting down...")
        publisher.undeclare()
        session.close()
        print("[Zenoh CPU Bridge] Closed")
        
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
