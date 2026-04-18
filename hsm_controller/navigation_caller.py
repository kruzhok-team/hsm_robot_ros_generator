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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------

import rclpy
from geometry_msgs.msg import PoseStamped
import math

from hsm_controller.constants import SERVICE_STARTUP_TIMEOUT
import hsm_interfaces.srv

class ROSNavigationCaller:

    MOVE_TO_POINT_SERVICE = 'hsm_ros_navigation_move_to_point'
    STOP_SERVICE = 'hsm_ros_navigation_stop'
    
    def __init__(self, node):
        self.__node = node
        self.__client_move_to_point = self.__node.create_client(hsm_interfaces.srv.NavigationMoveToPoint,
                                                                self.MOVE_TO_POINT_SERVICE)
        while not self.__client_move_to_point.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
            self.__node.get_logger().info('ROS Navigation Caller move_to_point service not available')
        self.__start_request = ros_api.srv.NavigationMoveToPoint.Request()
        self.__client_stop = self.__node.create_client(hsm_interfaces.srv.NavigationStop,
                                                       self.STOP_SERVICE)
        self.__stop_request = ros_api.srv.NavigationStop.Request()
        while not self.__client_stop.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
            self.__node.get_logger().info('ROS Navigation stop service not available')
        self.__moving = False
        self.__node.get_logger().info('ROS Navigation caller inerface initialized')

    def move_to_point(self, x, y, theta=None):
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.__node.get_clock().now().to_msg()
        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.position.z = 0.0

        if theta is not None:
            # Convert angle to quaternion
            goal.pose.orientation.z = math.sin(float(theta) / 2)
            goal.pose.orientation.w = math.cos(float(theta) / 2)
        else:
            goal.pose.orientation.w = 1.0
        
        self.__move_to_point_request.pose = pose
        self.__client_start.call_async(self.__move_to_point_request)

        self.__moving = True
        
    def stop(self):
        self.__client_stop.call_async(self.__stop_request)
        self.__moving = False

    def is_moving(self):
        return self.__moving

class Navigation(ROSNavigationCaller):

    __object = None
    
    def __new__(cls, *args, **kwargs):
        if cls.__object is None:
            cls.__object = super().__new__(cls)
        else:
            return cls.__object

    def __init__(self, node):
        ROSNavigationCaller.__init__(self, node)
        
    @classmethod
    def move_to_point(cls, x, y, theta=None):
        if cls.__object is not None:
            ROSNavigationCaller.move_to_point(cls.__object, x, y, theta)

    @classmethod
    def stop(cls):
        if cls.__object is not None:
            ROSNavigationCaller.stop(cls.__object)
