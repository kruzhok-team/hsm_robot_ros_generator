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
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------

import rclpy

from hsm_robot.constants import DEFAULT_TIMER
from hsm_controller.service_utils import wait_for_service
import hsm_interfaces.srv

Timer = None

class ROSTimerCaller:

    TICK_SERVICE = 'hsm_ros_timer_init_ticks'
    START_SERVICE = 'hsm_ros_timer_start'
    STOP_SERVICE = 'hsm_ros_timer_stop'
    
    def __init__(self, node, **kwargs):
        global Timer
        if Timer is None:
            self.__node = node
            self.__client_start = self.__node.create_client(hsm_interfaces.srv.TimerStart,
                                                            self.START_SERVICE)
            wait_for_service(self.__node, self.__client_start, 'ROS Timer caller start')
            self.__start_request = hsm_interfaces.srv.TimerStart.Request()
            self.__client_stop = self.__node.create_client(hsm_interfaces.srv.TimerStop,
                                                           self.STOP_SERVICE)
            self.__stop_request = hsm_interfaces.srv.TimerStop.Request()
            wait_for_service(self.__node, self.__client_stop, 'ROS Timer caller stop')
            self.__init_ticks('has_ticks' in kwargs and kwargs['has_ticks'],
                              'has_ticks_1s' in kwargs and kwargs['has_ticks_1s'],
                              'has_ticks_1m' in kwargs and kwargs['has_ticks_1m'])
            self.__node.get_logger().info('ROS Timer caller inerface initialized')
            Timer = self

    def __init_ticks(self, has_ticks, has_ticks_1s, has_ticks_1m):
        client = self.__node.create_client(hsm_interfaces.srv.TimerTicks,
                                           self.TICK_SERVICE)
        wait_for_service(self.__node, client, 'ROS Timer tick')
        request = hsm_interfaces.srv.TimerTicks.Request()
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
        
    def start(self, timeout, repeat=False, name=DEFAULT_TIMER):
        self.__start_request.timeout = timeout
        self.__start_request.repeat = repeat
        self.__start_request.name = name
        self.__client_start.call_async(self.__start_request)
     
    def stop(self, name=DEFAULT_TIMER):
        self.__stop_request.name = name
        self.__client_stop.call_async(self.__stop_request)
