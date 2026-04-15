# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 timer implementation
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

import robot.timer
import ros_api.constants
import ros_api.srv
import ros_api.msg

class ROSTimer(rclpy.node.Node):
    
    def __init__(self, node):
        api.timer.Timer.__init__(self)
        self.__node = node
        # self.__msg_listener = self.__node.create_subscription(ros_api.msg.SimpleMessage,
        #                                                       ros_api.constants.FRAME_ID,
        #                                                       self.__message_callback,
        #                                                       ros_api.constants.QUEUE_LEN)
        self.__client_start = self.__node.create_client(ros_api.srv.TimerStart,
                                                        robot.timer.ROSTimer.OBJECT_NAME)
        while not self.__client_start.wait_for_service(timeout_sec=1.0):
            self.__node.get_logger().info('ROSTimer start service not available')
        self.__start_request = ros_api.srv.TimerStart.Request()
        self.__client_stop = self.__node.create_client(ros_api.srv.TimerStop,
                                                       robot.timer.ROSTimer.OBJECT_NAME)
        self.__stop_request = ros_api.srv.TimerStop.Request()
        while not self.__client_stop.wait_for_service(timeout_sec=1.0):
            self.__node.get_logger().info('ROSTimer stop service not available')
        self.__node.get_logger().info('ROSTimer inerface node initialized')

    def start(self, timeout, repeat=False):
        self.__start_request.timeout = timeout
        self.__start_request.repeat = repeat
        self.__client_start.call_async(self.__start_request)
    
    def stop(self):
        self.__client_stop.call_async(self.__stop_request)
