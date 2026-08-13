# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 navigation caller interface
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
# Copyright (C) 2026 Anastasia Viktorova <viktorovaa.04@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
import math

import hsm_controller.constants
from hsm_controller.service_utils import wait_for_service
import hsm_interfaces.srv

Navigation = None


class ROSNavigationCaller:

    MOVE_TO_POINT_SERVICE = 'hsm_ros_navigation_move_to_point'
    MOVE_ALONG_TRAJ_SERVICE = 'hsm_ros_navigation_move_along_traj'
    STOP_SERVICE = 'hsm_ros_navigation_stop'

    def __init__(self, node):
        global Navigation
        if Navigation is None:
            self.__node = node
            self.__client_move_to_point = self.__node.create_client(hsm_interfaces.srv.NavigationMoveToPoint,
                                                                    self.MOVE_TO_POINT_SERVICE)
            wait_for_service(self.__node, self.__client_move_to_point,
                             'ROS Navigation Caller move_to_point')
            self.__move_to_point_request = hsm_interfaces.srv.NavigationMoveToPoint.Request()
            self.__client_move_along_traj = self.__node.create_client(hsm_interfaces.srv.NavigationMoveAlongTraj,
                                                                      self.MOVE_ALONG_TRAJ_SERVICE)
            wait_for_service(self.__node, self.__client_move_along_traj,
                             'ROS Navigation Caller move_along_traj')
            self.__move_along_traj_request = hsm_interfaces.srv.NavigationMoveAlongTraj.Request()
            self.__client_stop = self.__node.create_client(hsm_interfaces.srv.NavigationStop,
                                                           self.STOP_SERVICE)
            self.__stop_request = hsm_interfaces.srv.NavigationStop.Request()
            wait_for_service(self.__node, self.__client_stop, 'ROS Navigation stop')
            # get_point() has to answer immediately inside the HSM actions, so the robot
            # position is read from the odometry topic and cached here instead of being
            # requested by a service call, which would block the controller node
            self.__point = None
            self.__odom_subscriber = self.__node.create_subscription(
                Odometry,
                hsm_controller.constants.ODOMETRY_TOPIC,
                self.__odom_callback,
                hsm_controller.constants.MSG_QUEUE_LEN)
            self.__node.get_logger().info('ROS Navigation caller inerface initialized')
            Navigation = self

    def __odom_callback(self, msg):
        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        # the yaw of the plain (z, w) rotation around the vertical axis; computed here to
        # keep the controller free of the transforms3d dependency
        theta = math.atan2(2.0 * orientation.w * orientation.z,
                           1.0 - 2.0 * orientation.z * orientation.z)
        self.__point = (position.x, position.y, theta)

    def __make_pose(self, x, y, theta=None):
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.__node.get_clock().now().to_msg()
        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.position.z = 0.0

        if theta is not None:
            # Convert angle to quaternion
            pose.pose.orientation.z = math.sin(float(theta) / 2)
            pose.pose.orientation.w = math.cos(float(theta) / 2)
        else:
            pose.pose.orientation.w = 1.0

        return pose

    def move_to_point(self, x, y, theta=None):
        self.__move_to_point_request.pose = self.__make_pose(x, y, theta)
        self.__client_move_to_point.call_async(self.__move_to_point_request)

    def move_along_traj(self, traj):
        # the trajectory is the sequence of the points (x, y) or (x, y, theta); the module
        # travels them one by one and reports every passed point
        poses = []
        for point in traj or []:
            try:
                values = [float(value) for value in point]
            except TypeError:
                values = None
            if values is None or not 2 <= len(values) <= 3:
                # a malformed trajectory is reported and dropped: an exception raised here
                # would escape through the state machine handler and stop the controller
                self.__node.get_logger().error(
                    'ROS Navigation caller move_along_traj(): bad point {}'.format(point))
                return
            poses.append(self.__make_pose(*values))
        self.__move_along_traj_request.poses = poses
        self.__client_move_along_traj.call_async(self.__move_along_traj_request)

    def stop(self):
        self.__client_stop.call_async(self.__stop_request)

    def get_point(self):
        # returns the (x, y, theta) position of the robot, or None while no odometry
        # message has been received yet
        return self.__point
