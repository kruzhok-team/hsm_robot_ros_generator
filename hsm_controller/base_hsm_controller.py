# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The parent ROS2-based controller for HSM diagran
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

import pysm

import sys
import rclpy
import rclpy.node

import hsm_controller.constants
import hsm_controller.debug_caller
import hsm_controller.timer_caller
import hsm_controller.navigation_caller
import hsm_controller.wheels_caller

import hsm_interfaces.msg

HSM_CALLERS = {
    hsm_controller.constants.HSM_DEBUG: hsm_controller.debug_caller.ROSDebugCaller,
    hsm_controller.constants.HSM_NAVIGATION: hsm_controller.navigation_caller.ROSNavigationCaller,
    hsm_controller.constants.HSM_TIMER: hsm_controller.timer_caller.ROSTimerCaller,
    hsm_controller.constants.HSM_WHEELS: hsm_controller.wheels_caller.ROSWheelsCaller
}

class BaseHSMController(rclpy.node.Node):

    def __init__(self, object_name, obj_list,
                 has_tick=False, has_seconds=False, has_minutes=False):

        rclpy.node.Node.__init__(self, object_name)
        self.__msg_listener = self.create_subscription(hsm_interfaces.msg.SimpleMessage,
                                                       hsm_controller.constants.MESSAGES_TOPIC,
                                                       self.__simple_message_callback,
                                                       hsm_controller.constants.MSG_QUEUE_LEN)
        self.get_logger().info('Initializing HSM classes: {}'.format(obj_list))
        self.__api_callers = {}
        for name,cls in HSM_CALLERS.items():
            if name in obj_list:
                if name == hsm_controller.constants.HSM_TIMER:
                    self.__api_callers[name] = cls(self,
                                                   has_ticks=has_ticks,
                                                   has_ticks_1s=has_seconds,
                                                   has_ticks_1m=has_minutes)
                else:
                    self.__api_callers[name] = cls(self)

    def dispatch_event(self, event, arg=None):
        # this functions will be overloaded by the hsm controller implementation
        pass
    
    def terminate(self, *args):
        # close the controller node
        sys.exit()

    def __simple_message_callback(self, msg):
        msg_code = msg.code
        for module in self.__api_callers.keys():
            events = hsm_controller.constants.HSM_EVENTS[module]
            if msg_code in events:
                self.dispatch_event(events[msg_code])
                return
        self.get_logger().warn('Unknown message code: {}'.format(msg_code))

