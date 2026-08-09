# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 wheels caller interface
#
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

import rclpy
import math

from hsm_controller.service_utils import wait_for_service
import hsm_interfaces.srv

Wheels = None

class ROSWheelsCaller:

    STOP_SERVICE = 'hsm_ros_wheels_stop'
    FORWARD_SERVICE = 'hsm_ros_wheels_forward'
    BACK_SERVICE = 'hsm_ros_wheels_back'
    TURN_RIGHT_SERVICE = 'hsm_ros_wheels_turn_right'
    TURN_LEFT_SERVICE = 'hsm_ros_wheels_turn_left'
    
    def __init__(self, node):
        global Wheels
        if Wheels is None:
            self.__node = node
            
            # stop
            self.__client_stop = self.__node.create_client(hsm_interfaces.srv.WheelsStop,
                                                           self.STOP_SERVICE)
            self.__stop_request = hsm_interfaces.srv.WheelsStop.Request()
            wait_for_service(self.__node, self.__client_stop, 'ROS Wheels Caller stop')

            # forward
            self.__client_forward = self.__node.create_client(hsm_interfaces.srv.WheelsForward,
                                                              self.FORWARD_SERVICE)
            self.__forward_request = hsm_interfaces.srv.WheelsForward.Request()
            wait_for_service(self.__node, self.__client_forward, 'ROS Wheels Caller forward')

            # back
            self.__client_back = self.__node.create_client(hsm_interfaces.srv.WheelsBack,
                                                           self.BACK_SERVICE)
            self.__back_request = hsm_interfaces.srv.WheelsBack.Request()
            wait_for_service(self.__node, self.__client_back, 'ROS Wheels Caller back')

            # turn_right
            self.__client_turn_right = self.__node.create_client(hsm_interfaces.srv.WheelsTurnRight,
                                                                 self.TURN_RIGHT_SERVICE)
            self.__client_turn_right_request = hsm_interfaces.srv.WheelsTurnRight.Request()
            wait_for_service(self.__node, self.__client_turn_right, 'ROS Wheels Caller turn right')
            
            # turn_left
            self.__client_turn_left = self.__node.create_client(hsm_interfaces.srv.WheelsTurnLeft,
                                                                self.TURN_LEFT_SERVICE)
            self.__client_turn_left_request = hsm_interfaces.srv.WheelsTurnLeft.Request()
            wait_for_service(self.__node, self.__client_turn_left, 'ROS Wheels Caller turn left')
            
            self.__node.get_logger().info('ROS Wheels caller inerface initialized')
            Wheels = self

    def stop(self):
        self.__client_stop.call_async(self.__stop_request)

    def forward(self, v):
        self.__forward_request.v = v
        self.__client_forward.call_async(self.__forward_request)

    def back(self, v):
        self.__back_request.v = v
        self.__client_back.call_async(self.__back_request)

    def turn_right(self, w):
        self.__client_turn_right_request.w = w
        self.__client_turn_right.call_async(self.__client_turn_right_request)

    def turn_left(self, w):
        self.__client_turn_left_request.w = w
        self.__client_turn_left.call_async(self.__client_turn_left_request)
