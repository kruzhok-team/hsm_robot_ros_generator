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

import hsm_robot.timer
import hsm_robot.debug
import hsm_robot.navigator
import hsm_robot.constants

import hsm_robot.msg          # will be generated
import hsm_robot.hsm_messages # will be generated

HSM_CALLERS = {
    constants.HSM_DEBUG: ros_api.debug.Debug,
    constants.HSM_NAVIGATION: ros_api.navigation.Navigation,
    constants.HSM_TIMER: ros_api.timer.Timer
}

class BaseHSMController(rclpy.node.Node):

    def __init__(self, object_name, obj_list,
                 has_tick=False, has_seconds=False, has_minutes=False):

        super().__init__(object_name)
        self.__msg_listener = self.__node.create_subscription(hsm_robot.msg.SimpleMessage,
                                                              hsm_robot.constants.MESSAGES_TOPIC,
                                                              self.__simple_message_callback,
                                                              hsm_robot.constants.QUEUE_LEN)
        self.__api_callers = {}
        for name,cls HSM_CALLERS.items():
            if name in obj_list:
                if name == constants.HSM_TIMER:
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
        self.dispatch_event(ros_api.hsm_messages.HSM_MESSAGES[msg_code])
