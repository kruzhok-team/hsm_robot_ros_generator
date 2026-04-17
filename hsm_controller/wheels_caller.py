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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------

import rclpy
import math

from hsm_controller.constants import SERVICE_STARTUP_TIMEOUT
import hsm_interfaces.srv

class __ROSWheelsCaller:

    STOP_SERVICE = 'hsm_ros_wheels_stop'
    FORWARD_SERVICE = 'hsm_ros_wheels_forward'
    BACK_SERVICE = 'hsm_ros_wheels_back'
    TURN_RIGHT_SERVICE = 'hsm_ros_wheels_turn_right'
    TURN_LEFT_SERVICE = 'hsm_ros_wheels_turn_left'
    
    def __init__(self, node):
        self.__node = node
        self.__client_stop = self.__node.create_client(hsm_interfaces.srv.WheelsStop,
                                                       self.STOP_SERVICE)
        while not self.__client_stop.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
            self.__node.get_logger().info('ROS Wheels Caller stop service not available')
        self.__stop_request = ros_api.srv.WheelsStop.Request()

        self.__client_forward = self.__node.create_client(hsm_interfaces.srv.WheelsForward,
                                                          self.FORWARD_SERVICE)
        self.__forward_request = ros_api.srv.WheelsForward.Request()
        while not self.__client_forward.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
            self.__node.get_logger().info('ROS Wheels Caller forward service not available')

        self.__client_back = self.__node.create_client(hsm_interfaces.srv.WheelsBack,
                                                       self.BACK_SERVICE)
        self.__back_request = ros_api.srv.WheelsBack.Request()
        while not self.__client_back.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
            self.__node.get_logger().info('ROS Wheels Caller back service not available')
        
        self.__client_turn_right = self.__node.create_client(hsm_interfaces.srv.WheelsTurnRight,
                                                             self.TURN_RIGHT_SERVICE)
        self.__client_turn_right_request = ros_api.srv.WheelsTurnRight.Request()
        while not self.__client_turn_right.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
            self.__node.get_logger().info('ROS Wheels Caller turn right service not available')

        self.__client_turn_left = self.__node.create_client(hsm_interfaces.srv.WheelsTurnRight,
                                                           self.TURN_LEFT_SERVICE)
        self.__client_turn_left_request = ros_api.srv.WheelsTurnLeft.Request()
        while not self.__client_turn_left.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
            self.__node.get_logger().info('ROS Wheels Caller turn left service not available')

        self.__node.get_logger().info('ROS Wheels caller inerface initialized')

    def stop(self):
        self.__client_stop.call_async(self.__stop_request)

    def forward(self, v):
        self.__forward_request.v = v
        self.__client_start.call_async(self.__forward_request)

    def back(self, v):
        self.__back_request.v = v
        self.__client_start.call_async(self.__back_request)

    def turn_right(self, w):
        self.__client_turn_right_request.w = w
        self.__client_start.call_async(self.__client_turn_right_request)

    def turn_left(self, w):
        self.__client_turn_left_request.w = w
        self.__client_start.call_async(self.__client_turn_left_request)

class Wheels(__ROSWheelsCaller):

    __object = None

    def __new__(cls, *args, **kwargs):
        if cls.__object is None:
            cls.__object = super().__new__(cls)
        else:
            return cls.__object

    @classmethod
    def stop(cls):
        if cls.__object is not None:
            __ROSWheelsCaller.stop(cls.__object)

    @classmethod
    def forward(cls, v):
        if cls.__object is not None:
            __ROSWheelsCaller.forward(cls.__object, v)

    @classmethod
    def back(cls, v):
        if cls.__object is not None:
            __ROSWheelsCaller.back(cls.__object, v)

    @classmethod
    def turn_right(cls, w):
        if cls.__object is not None:
            __ROSWheelsCaller.turn_right(cls.__object, w)

    @classmethod
    def turn_left(cls, w):
        if cls.__object is not None:
            __ROSWheelsCaller.turn_left(cls.__object, w)
