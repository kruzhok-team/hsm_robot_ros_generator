# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 timer caller intraface
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

Timer = None

class ROSTimerCaller:

    TICK_SERVICE = 'hsm_ros_timer_init_ticks'
    START_SERVICE = 'hsm_ros_timer_start'
    STOP_SERVICE = 'hsm_ros_timer_stop'
    
    def __init__(self, node, **kwargs):
        if Timer is None:
            self.__node = node
            self.__client_start = self.__node.create_client(hsm_interfaces.srv.TimerStart,
                                                            self.START_SERVICE)
            while not self.__client_start.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
                self.__node.get_logger().info('ROS Timer caller start service not available')
            self.__start_request = ros_api.srv.TimerStart.Request()
            self.__client_stop = self.__node.create_client(hsm_interfaces.srv.TimerStop,
                                                           self.STOP_SERVICE)
            self.__stop_request = ros_api.srv.TimerStop.Request()
            while not self.__client_stop.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
                self.__node.get_logger().info('ROS Timer caller stop service not available')
            self.__init_ticks('has_ticks' in kwargs and kwargs['has_ticks'],
                              'has_ticks_1s' in kwargs and kwargs['has_ticks_1s'],
                              'has_ticks_1m' in kwargs and kwargs['has_ticks_1m'])
            self.__node.get_logger().info('ROS Timer caller inerface initialized')
            Timer = self

    def __init_ticks(self, has_ticks, has_ticks_1s, has_ticks_1m):
        client = self.__node.create_client(hsm_interfaces.srv.TimerTick,
                                           self.TICK_SERVICE)
        while not client.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
            self.__node.get_logger().info('ROS Timer tick service not available')
        request = ros_api.srv.TimerTick.Request()
        request.run_ticks = has_ticks
        request.run_ticks_1sec = has_ticks_1s
        request.run_ticks_1min = has_ticks_1m
        client_call = client.call_async(request)
        rclpy.spin_until_future_complete(self.__node, client_call)
        result = client_call.result()
        if result.ok:
            self.__node.get_logger().info('ROS Timer caller ticks initialized')
        else:
            self.__node.get_logger().info('ROS Timer caller ticks initialization failed')            
        
    def start(self, timeout, repeat=False):
        self.__start_request.timeout = timeout
        self.__start_request.repeat = repeat
        self.__client_start.call_async(self.__start_request)
     
    def stop(self):
        self.__client_stop.call_async(self.__stop_request)
