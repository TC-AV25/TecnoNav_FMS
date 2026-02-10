import logging
import os
import time
import warnings

import zenoh
from lanelet2.core import BasicPoint3d, GPSPoint
from lanelet2.io import Origin
from lanelet2.projection import UtmProjector
from zenoh_ros_type.autoware_adapi_msgs import (
    ChangeOperationModeResponse,
    ClearRouteResponse,
    Route,
    RouteOption,
    SetRoutePointsRequest,
    SetRoutePointsResponse,
    VehicleKinematics,
)
from zenoh_ros_type.common_interfaces import (
    Header,
    Point,
    Pose,
    Quaternion,
)
from zenoh_ros_type.rcl_interfaces import Time
from zenoh_ros_type.tier4_autoware_msgs import GateMode

from .map_parser import OrientationParser

logger = logging.getLogger(__name__)

GET_POSE_KEY_EXPR = '/api/vehicle/kinematics'
GET_GOAL_POSE_KEY_EXPR = '/api/routing/route'
SET_AUTO_MODE_KEY_EXPR = '/api/operation_mode/change_to_autonomous'
SET_ROUTE_POINT_KEY_EXPR = '/api/routing/set_route_points'
SET_CLEAR_ROUTE_KEY_EXPR = '/api/routing/clear_route'

### TODO: Should be replaced by ADAPI
SET_GATE_MODE_KEY_EXPR = '/control/gate_mode_cmd'


class VehiclePose:
    def __init__(self, session, scope, use_bridge_ros2dds=True):
        ### Information
        self.use_bridge_ros2dds = use_bridge_ros2dds
        self.session = session
        self.scope = scope
        self.originX = float(os.environ['REACT_APP_MAP_ORIGIN_LAT'])
        self.originY = float(os.environ['REACT_APP_MAP_ORIGIN_LON'])
        self.projector = UtmProjector(Origin(self.originX, self.originY))
        self.initialize()

    def initialize(self):
        self.lat = 0.0
        self.lon = 0.0
        self.heading = 0.0  # heading in degrees (0 = North, 90 = East, etc.)

        self.positionX = 0.0
        self.positionY = 0.0

        self.topic_prefix = self.scope if self.use_bridge_ros2dds else self.scope + '/rt'

        # Lazy initialize OrientationParser - will be created when first needed
        self.orientationGen = None

        self.goalX = 0.0
        self.goalY = 0.0
        self.goalLat = 0.0
        self.goalLon = 0.0
        self.goalValid = False

        def callback_position(sample):
            # print("size of the message (bytes) ", struct.calcsize(sample.payload))
            # print(sample.payload)
            data = VehicleKinematics.deserialize(sample.payload.to_bytes())
            # print(data)
            self.positionX = data.pose.pose.pose.position.x
            self.positionY = data.pose.pose.pose.position.y
            gps = self.projector.reverse(BasicPoint3d(self.positionX, self.positionY, 0.0))
            self.lat = gps.lat
            self.lon = gps.lon
            
            # Extract heading from quaternion orientation
            # quaternion format: (x, y, z, w)
            qx = -data.pose.pose.pose.orientation.x
            qy = -data.pose.pose.pose.orientation.y
            qz = -data.pose.pose.pose.orientation.z
            qw = -data.pose.pose.pose.orientation.w
            
            # Convert quaternion to yaw (heading)
            import math
            siny_cosp = 2 * (qw * qz + qx * qy)
            cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
            yaw = math.atan2(siny_cosp, cosy_cosp)
            # Convert from radians to degrees
            self.heading = math.degrees(yaw)

        def callback_goalPosition(sample):
            data = Route.deserialize(sample.payload.to_bytes())
            if len(data.data) == 1:
                self.goalX = data.data[0].goal.position.x
                self.goalY = data.data[0].goal.position.y
                gps = self.projector.reverse(BasicPoint3d(self.goalX, self.goalY, 0.0))
                self.goalLat = gps.lat
                self.goalLon = gps.lon
                print('Echo back goal pose: ', self.goalLat, self.goalLon)
                self.goalValid = True
            else:
                self.goalValid = False

        ### Topics
        ###### Subscribers
        self.subscriber_pose = self.session.declare_subscriber(self.topic_prefix + GET_POSE_KEY_EXPR, callback_position)
        self.subscriber_goalPose = self.session.declare_subscriber(self.topic_prefix + GET_GOAL_POSE_KEY_EXPR, callback_goalPosition)

        ###### Publishers
        self.publisher_gate_mode = self.session.declare_publisher(self.topic_prefix + SET_GATE_MODE_KEY_EXPR)

    def _ensure_orientation_parser(self):
        """Lazily initialize OrientationParser if not already done"""
        if self.orientationGen is not None:
            return True
        
        try:
            # Suppress all output (including stderr) from lanelet2 parsing
            import sys
            import io
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            
            try:
                self.orientationGen = OrientationParser()
                logger.info(f"OrientationParser initialized successfully for {self.scope}")
                return True
            finally:
                # Restore stdout/stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
        except Exception as e:
            logger.error(f"Failed to initialize OrientationParser for {self.scope}: {e}", exc_info=True)
            return False

    def setGoal(self, lat, lon):
        try:
            # Ensure OrientationParser is initialized
            if not self._ensure_orientation_parser():
                raise RuntimeError(f"OrientationParser initialization failed for {self.scope}")
                
            replies = self.session.get(self.topic_prefix + SET_CLEAR_ROUTE_KEY_EXPR)

            for reply in replies:
                try:
                    print(">> Received ('{}': {})".format(reply.ok.key_expr, ClearRouteResponse.deserialize(reply.ok.payload.to_bytes())))
                except Exception as e:
                    print(f'Failed to handle response: {e}')

            coordinate = self.projector.forward(GPSPoint(float(lat), float(lon), 0))
            q = self.orientationGen.genQuaternion_seg(coordinate.x, coordinate.y)
            request = SetRoutePointsRequest(
                header=Header(stamp=Time(sec=0, nanosec=0), frame_id='map'),
                option=RouteOption(allow_goal_modification=False),
                goal=Pose(position=Point(x=coordinate.x, y=coordinate.y, z=0), orientation=Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])),
                waypoints=[],
            ).serialize()

            replies = self.session.get(self.topic_prefix + SET_ROUTE_POINT_KEY_EXPR, payload=request)
            for reply in replies:
                try:
                    print(">> Received ('{}': {})".format(reply.ok.key_expr, SetRoutePointsResponse.deserialize(reply.ok.payload.to_bytes())))
                except Exception as e:
                    print(f'Failed to handle response: {e}')
            logger.info(f"Goal set successfully for {self.scope}: lat={lat}, lon={lon}")
        except Exception as e:
            logger.error(f"Error setting goal for {self.scope}: {e}", exc_info=True)
            raise

    def update_map(self, map_path, origin_lat, origin_lon):
        self.originX = float(origin_lat)
        self.originY = float(origin_lon)
        self.projector = UtmProjector(Origin(self.originX, self.originY))
        try:
            # Suppress all output (including stderr) from lanelet2 parsing
            import sys
            import io
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            
            try:
                self.orientationGen = OrientationParser(path=map_path, originX=self.originX, originY=self.originY)
            finally:
                # Restore stdout/stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
        except Exception as e:
            logger.info(f"Failed to update OrientationParser with map {map_path}: {e}")
            self.orientationGen = None
            self.orientationGen = None

    def engage(self):
        self.publisher_gate_mode.put(GateMode(data=GateMode.DATA['AUTO'].value).serialize())

        # Ensure Autoware receives the gate mode change before the operation mode change
        time.sleep(1)

        replies = self.session.get(self.topic_prefix + SET_AUTO_MODE_KEY_EXPR)
        for reply in replies:
            try:
                print(">> Received ('{}': {})".format(reply.ok.key_expr, ChangeOperationModeResponse.deserialize(reply.ok.payload.to_bytes())))
            except Exception as e:
                print(f'Failed to handle response: {e}')


class PoseServer:
    def __init__(self, session, use_bridge_ros2dds=False):
        self.use_bridge_ros2dds = use_bridge_ros2dds
        self.session = session
        self.vehicles = {}

    def findVehicles(self, time=10):
        # ✓ NEW: Save goal data before clearing vehicles
        goal_backup = {}
        for scope, vehicle in self.vehicles.items():
            if vehicle is not None:
                vehicle.subscriber_pose.undeclare()
                # Store goal data if it exists
                if vehicle.goalValid:
                    goal_backup[scope] = {
                        'goalX': vehicle.goalX,
                        'goalY': vehicle.goalY,
                        'goalLat': vehicle.goalLat,
                        'goalLon': vehicle.goalLon,
                        'goalValid': True
                    }

        self.vehicles = {}
        for _ in range(time):
            replies = self.session.get('@/**/ros2/**' + GET_POSE_KEY_EXPR)
            for reply in replies:
                key_expr = str(reply.ok.key_expr)
                if 'pub' in key_expr:
                    end = key_expr.find(GET_POSE_KEY_EXPR)
                    vehicle = key_expr[:end].split('/')[-1]
                    #print(f'find vehicle {vehicle}')
                    self.vehicles[vehicle] = None
        # ✓ NEW: Pass goal backup to constructVehicle
        self.constructVehicle(goal_backup)

    def constructVehicle(self, goal_backup=None):
        if goal_backup is None:
            goal_backup = {}
            
        for scope in self.vehicles.keys():
            try:
                self.vehicles[scope] = VehiclePose(self.session, scope)
                
                # ✓ NEW: Restore goal data if it was backed up
                if scope in goal_backup:
                    restored = goal_backup[scope]
                    self.vehicles[scope].goalX = restored['goalX']
                    self.vehicles[scope].goalY = restored['goalY']
                    self.vehicles[scope].goalLat = restored['goalLat']
                    self.vehicles[scope].goalLon = restored['goalLon']
                    self.vehicles[scope].goalValid = restored['goalValid']
                    print(f"Goal restored for {scope}")
                    
            except Exception as e:
                print(f"Failed to initialize VehiclePose for {scope}: {e}")
                self.vehicles[scope] = None

    def update_map(self, map_path, origin_lat, origin_lon):
        for scope, vehicle in self.vehicles.items():
            if vehicle is not None:
                vehicle.update_map(map_path, origin_lat, origin_lon)

    def returnPose(self):
        poseInfo = []
        for scope, vehicle in self.vehicles.items():
            if vehicle is not None:
                poseInfo.append({
                    'name': scope, 
                    'lat': vehicle.lat, 
                    'lon': vehicle.lon,
                    'heading': vehicle.heading
                })
        return poseInfo

    def returnGoalPose(self):
        goalPoseInfo = []
        for scope, vehicle in self.vehicles.items():
            if vehicle is not None and vehicle.goalValid:
                goalPoseInfo.append({'name': scope, 'lat': vehicle.goalLat, 'lon': vehicle.goalLon})
        return goalPoseInfo

    def setGoal(self, scope, lat, lon):
        if scope in self.vehicles.keys() and self.vehicles[scope] is not None:
            self.vehicles[scope].setGoal(lat, lon)
        else:
            logger.warning(f"Vehicle {scope} not found or not initialized for goal setting")

    def engage(self, scope):
        if scope in self.vehicles.keys() and self.vehicles[scope] is not None:
            self.vehicles[scope].engage()
        else:
            logger.warning(f"Vehicle {scope} not found or not initialized for engagement")


if __name__ == '__main__':
    session = zenoh.open()
    mc = PoseServer(session, 'v1')

    while True:
        time.sleep(1)
