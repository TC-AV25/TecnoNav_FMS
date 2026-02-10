import math
import os

import lanelet2
import numpy as np

# from lanelet2.core import BasicPoint3d, GPSPoint
import lanelet2
import numpy as np

from lanelet2.io import Origin
from lanelet2.projection import UtmProjector
from lanelet2.core import Point3d
from lanelet2.geometry import distance


def proj_between(p1, p2, p3):
    ### A segment p1 to p2
    ### Project p3 to segment p1 p2, check whether it is between p1 and p2
    # projLen = np.dot((p3-p1), (p2-p1)) / (np.linalg.norm(p2-p1) * np.linalg.norm(p2-p1))
    # p = p1 + projLen * (p2-p1)
    return np.dot((p3 - p1), (p3 - p2)) < 0


def point2line(p1, p2, p3):
    d = np.cross(p2 - p1, p3 - p1) / np.linalg.norm(p2 - p1)
    return d * d


def vec2degree(v1, v2):
    dx = v2.x - v1.x
    dy = v2.y - v1.y
    angle = math.atan(dy / dx)
    if dx < 0:  ## II or III quadrant
        angle += math.pi
    return angle


class OrientationParser:
    def __init__(
        self,
        path=f'frontend/public{os.environ["REACT_APP_MAP_FILE_PATH"]}',
        originX=os.environ['REACT_APP_MAP_ORIGIN_LAT'],
        originY=os.environ['REACT_APP_MAP_ORIGIN_LON'],
    ):
        self.mapPath = path
        self.proj = UtmProjector(Origin(float(originX), float(originY)))
        self.vmap = lanelet2.io.load(path, self.proj)
        self.points = {}
        self.ways = {}
        self.initialize()

    def initialize(self):
        for p in self.vmap.pointLayer:
            self.points[p.id] = p

        for line in self.vmap.lineStringLayer:
            self.ways[line.id] = [point for point in line]

    def genQuaternion_seg(self, x, y):
        """
        Find the closest lanelet and return quaternion based on lane direction.
        Uses lanelet2 centerline for accurate direction on curves.
        """
        query_point = Point3d(1, x, y, 0)
        
        closest_lanelet = None
        closest_distance = float('inf')
        closest_yaw = None
        
        # Step 1: Find which lane is closest (and the best matching segment direction)
        try:
            for lanelet in self.vmap.laneletLayer:
                dist = distance(lanelet.centerline, query_point)
                if dist >= closest_distance:
                    continue

                centerline = lanelet.centerline
                if len(centerline) < 2:
                    continue

                # Find closest segment on this centerline
                lanelet_best_dis = float('inf')
                lanelet_best_yaw = None

                for idx in range(len(centerline) - 1):
                    from_ = centerline[idx]
                    to_ = centerline[idx + 1]
                    p1 = np.array([from_.x, from_.y])
                    p2 = np.array([to_.x, to_.y])
                    p3 = np.array([x, y])

                    if proj_between(p1, p2, p3):
                        seg_dis = point2line(p1, p2, p3)
                    else:
                        # Fallback to endpoint distance when projection is outside
                        seg_dis = min(np.linalg.norm(p3 - p1), np.linalg.norm(p3 - p2))

                    if seg_dis < lanelet_best_dis:
                        lanelet_best_dis = seg_dis
                        lanelet_best_yaw = vec2degree(from_, to_)

                if lanelet_best_yaw is None:
                    continue

                closest_distance = dist
                closest_lanelet = lanelet
                closest_yaw = lanelet_best_yaw

        except Exception as e:
            print(f"Error finding lanelet: {e}")
            return [0, 0, 0, 1]
        
        if closest_lanelet is None:
            print("No lanelet found")
            return [0, 0, 0, 1]
        
        # Step 2: Use the direction of the closest lane segment
        try:
            if closest_yaw is None:
                print("No valid lanelet segment found")
                return [0, 0, 0, 1]

            print(f"Lanelet {closest_lanelet.id}, yaw: {closest_yaw:.2f} rad, distance: {closest_distance:.2f}")

            return [0, 0, math.sin(closest_yaw / 2), math.cos(closest_yaw / 2)]

        except Exception as e:
            print(f"Error generating quaternion: {e}")
            return [0, 0, 0, 1]


if __name__ == '__main__':
    op = OrientationParser('lanelet2_map.osm', originX=35.23808753540768, originY=139.9009591876285)
    op = OrientationParser('Town01.osm', originX=0, originY=0)
    # x = float(input('x: '))
    # y = float(input('y: '))

    print(op.genQuaternion_seg(318.74114990234375, -134.72076416015625))
    # op.plotLane(114.7998046875, -200.10482788085938)
