# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 pump caller interface
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
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


from hsm_controller.service_utils import wait_for_service
import hsm_interfaces.srv

Pump = None


class ROSPumpCaller:

    TURN_ON_SERVICE = 'hsm_ros_pump_turn_on'
    TURN_OFF_SERVICE = 'hsm_ros_pump_turn_off'

    def __init__(self, node):
        global Pump
        if Pump is None:
            self.__node = node

            # turn_on
            self.__client_turn_on = self.__node.create_client(hsm_interfaces.srv.PumpTurnOn,
                                                              self.TURN_ON_SERVICE)
            self.__turn_on_request = hsm_interfaces.srv.PumpTurnOn.Request()
            wait_for_service(self.__node, self.__client_turn_on, 'ROS Pump caller turn on')

            # turn_off
            self.__client_turn_off = self.__node.create_client(hsm_interfaces.srv.PumpTurnOff,
                                                               self.TURN_OFF_SERVICE)
            self.__turn_off_request = hsm_interfaces.srv.PumpTurnOff.Request()
            wait_for_service(self.__node, self.__client_turn_off, 'ROS Pump caller turn off')

            self.__node.get_logger().info('ROS Pump caller inerface initialized')
            Pump = self

    def turn_on(self):
        self.__client_turn_on.call_async(self.__turn_on_request)

    def turn_off(self):
        self.__client_turn_off.call_async(self.__turn_off_request)
