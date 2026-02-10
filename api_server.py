import asyncio
import json
import logging
import math
import os
import subprocess
from pathlib import Path

import cv2
import zenoh
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from zenoh_app.camera_autoware import MJPEG_server
from zenoh_app.list_autoware import list_autoware
from zenoh_app.pose_service import PoseServer
from zenoh_app.status_autoware import get_cpu_status, get_vehicle_status
from zenoh_app.teleop_autoware import ManualController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),  # Print to stdout
        logging.FileHandler('logs/api_server.log', mode='a')  # Also write to file
    ]
)
logger = logging.getLogger(__name__)

MJPEG_HOST = '0.0.0.0'
MJPEG_PORT = 5000

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'])

conf = zenoh.Config.from_file('config.json5')
session = zenoh.open(conf)
use_bridge_ros2dds = True
manual_controller = None
mjpeg_server = None
pose_service = PoseServer(session, use_bridge_ros2dds)


def _get_maps_config_file():
    """Get the path to the maps configuration file."""
    return Path(__file__).parent / 'my_scripts' / 'maps_config.json'


def _load_all_maps_config():
    """Load all maps configuration from file."""
    config_file = _get_maps_config_file()
    with open(config_file, 'r') as f:
        return json.load(f)


def _load_current_map_config():
    """Load current map configuration."""
    config = _load_all_maps_config()
    map_key = config.get('current_map', None)
    map_info = config.get('maps', {}).get(map_key)
    return map_key, map_info


def _apply_map_config(map_info):
    if not map_info:
        return
    origin_lat = map_info['origin_lat']
    origin_lon = map_info['origin_lon']
    map_path = Path(__file__).parent / 'frontend' / 'public' / map_info['path'].lstrip('/')
    os.environ['REACT_APP_MAP_ORIGIN_LAT'] = str(origin_lat)
    os.environ['REACT_APP_MAP_ORIGIN_LON'] = str(origin_lon)
    os.environ['REACT_APP_MAP_FILE_PATH'] = map_info['path']
    pose_service.update_map(str(map_path), origin_lat, origin_lon)


# initialize map config on startup
# try:
#     _, info = _load_current_map_config()
#     _apply_map_config(info)
#     logger.info("Map config applied on startup")
# except Exception as e:
#     logger.error(f"failed to apply map config on startup: {e}")


@app.get('/')
async def root():
    return {'message': 'Hello World'}


@app.get('/list')
async def manage_list_autoware():
    return list_autoware(session, use_bridge_ros2dds)


@app.get('/status/{scope}')
async def manage_status_autoware(scope):
    return {'cpu': get_cpu_status(session, scope, use_bridge_ros2dds), 'vehicle': get_vehicle_status(session, scope, use_bridge_ros2dds)}


@app.websocket('/video')
async def handle_ws(websocket: WebSocket):
    await websocket.accept()
    global mjpeg_server

    try:
        while True:
            if mjpeg_server is None or mjpeg_server.camera_image is None:
                await asyncio.sleep(2)
            else:
                # Encode the frame as JPEG
                _, buffer = cv2.imencode('.jpg', mjpeg_server.camera_image)
                frame_bytes = buffer.tobytes()
                await websocket.send_bytes(frame_bytes)
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        await websocket.close()


@app.get('/teleop/startup')
async def manage_teleop_startup(scope):
    global manual_controller, mjpeg_server, mjpeg_server_thread
    if manual_controller is not None:
        manual_controller.stop_teleop()
    manual_controller = ManualController(session, scope, use_bridge_ros2dds)

    if mjpeg_server is not None:
        mjpeg_server.change_vehicle(scope)
    else:
        mjpeg_server = MJPEG_server(session, scope, use_bridge_ros2dds)
    return {
        'text': f'Startup manual control on {scope}.',
        'mjpeg_host': 'localhost' if MJPEG_HOST == '0.0.0.0' else MJPEG_HOST,
        'mjpeg_port': MJPEG_PORT,
    }


@app.get('/teleop/gear')
async def manage_teleop_gear(scope, gear):
    global manual_controller
    if manual_controller is not None:
        manual_controller.pub_gear(gear)
        return f'Set gear {gear} to {scope}.'
    else:
        return 'Please startup the teleop first'


@app.get('/teleop/velocity')
async def manage_teleop_speed(scope, velocity):
    global manual_controller
    if manual_controller is not None:
        manual_controller.update_control_command(float(velocity) * 1000 / 3600, None)
        return f'Set speed {velocity} to {scope}.'
    else:
        return 'Please startup the teleop first'


@app.get('/teleop/turn')
async def manage_teleop_turn(scope, angle):
    global manual_controller
    if manual_controller is not None:
        manual_controller.update_control_command(None, float(angle) * math.pi / 180)
        return f'Set steering angle {angle}.'
    else:
        return 'Please startup the teleop first'


@app.get('/teleop/status')
async def manage_teleop_status():
    global manual_controller
    if manual_controller is not None:
        return {
            'velocity': round(manual_controller.current_velocity * 3600 / 1000, 2),
            'gear': manual_controller.current_gear,
            'steering': manual_controller.current_steer * 180 / math.pi,
        }
    else:
        return {'velocity': '---', 'gear': '---', 'steering': '---'}


@app.get('/map/list')
async def get_vehilcle_list():
    global pose_service
    pose_service.findVehicles()
    return list(pose_service.vehicles.keys())


@app.get('/map/pose')
async def get_vehicle_pose():
    global pose_service
    if pose_service is not None:
        return pose_service.returnPose()
    else:
        return []


@app.get('/map/goalPose')
async def get_vehicle_goalpose():
    global pose_service
    if pose_service is not None:
        return pose_service.returnGoalPose()
    else:
        return []


@app.get('/map/setGoal')
async def set_goal_pose(scope: str, lat: float, lon: float):
    global pose_service
    if pose_service is not None:
        logger.info(f'Set Goal Pose of {scope} as (lat={lat}, lon={lon})')
        pose_service.setGoal(scope, lat, lon)
        return 'success'
    else:
        return 'fail'


@app.get('/map/engage')
async def set_engage(scope):
    global pose_service
    if pose_service is not None:
        pose_service.engage(scope)
        return 'success'
    else:
        return 'fail'


@app.get('/map/list-available')
async def list_available_maps():
    """Get list of all available maps from maps_config.json"""
    try:
        config = _load_all_maps_config()
        maps = {}
        for key, map_info in config.get('maps', {}).items():
            maps[key] = {
                'name': map_info['name'],
                'path': map_info['path'],
                'description': map_info['description'],
                'origin_lat': map_info['origin_lat'],
                'origin_lon': map_info['origin_lon'],
            }
        current_map = config.get('current_map', 'unknown')
        # logger.info(f"list-available current_map={current_map}")
        return {
            'maps': maps,
            'current_map': current_map
        }
    except Exception as e:
        logger.error(f"list-available error: {e}")
        return {'error': str(e), 'maps': {}, 'current_map': 'unknown'}


@app.get('/map/switch')
async def switch_map(map_key: str):
    """Switch to a different map"""
    script_path = Path(__file__).parent / 'my_scripts' / 'switch_map.py'
    try:
        # logger.info(f"switch map to {map_key}")
        result = subprocess.run(
            ['python3', str(script_path), 'set', map_key],
            capture_output=True,
            text=True,
            timeout=10
        )
        # Log the subprocess output
        if result.stdout:
            logger.info(f"switch_map.py stdout:\n{result.stdout}")
        if result.stderr:
            logger.error(f"switch_map.py stderr:\n{result.stderr}")
        
        if result.returncode == 0:
            try:
                _, info = _load_current_map_config()
                _apply_map_config(info)
            except Exception as e:
                logger.error(f"failed to apply map config after switch: {e}")
            logger.info(f"switch map success {map_key}")
            return {'success': True, 'message': f'Switched to {map_key}'}
        else:
            # logger.error(f"switch map failed with return code {result.returncode}")
            return {'success': False, 'error': result.stderr}
    except Exception as e:
        # logger.error(f"switch map error {e}")
        return {'success': False, 'error': str(e)}
