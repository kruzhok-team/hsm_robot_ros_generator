# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 timer caller interface
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

from hsm_controller.constants import SERVICE_STARTUP_TIMEOUT
import hsm_interfaces.srv

class __ROSDebugCaller:

    PRINT_SERVICE = 'hsm_ros_debug_print'

    def __init__(self, node):
        self.__node = node
        self.__client_start = self.__node.create_client(hsm_interfaces.srv.DebugPrint,
                                                        self.PRINT_SERVICE)
        while not self.__client_start.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
            self.__node.get_logger().info('ROS Debug caller print service not available')
        self.__print_request = ros_api.srv.DebugPrint.Request()
        self.__node.get_logger().info('ROS Debug caller inerface initialized')

    def print(self, s):
        self.__print_request.s = s
        self.__client_start.call_async(self.__print_request)

    def println(self, s):
        self.print(s + '\n')

class Debug(__ROSDebugCaller):

    __object = None

    def __new__(cls, *args, **kwargs):
        if cls.__object is None:
            cls.__object = super().__new__(self, *args, **kwargs)
        else:
            return cls.__object
    
    @classmethod
    def print(cls, s):
        if cls.__object is not None:
            cls.__object.print(s)

    @classmethod
    def println(cls, s):
        if cls.__object is not None:
            cls.__object.println(s)
