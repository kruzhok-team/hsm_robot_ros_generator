# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 debugging module implementation
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

import hsm_robot.srv

class ROSDebug(rclpy.node.Node):

    OBJECT_NAME = 'hsm_ros_debug'
    PRINT_SERVICE = 'hsm_ros_debug_print'
    
    def __init__(self):
        rclpy.node.Node.__init__(self.OBJECT_NAME)
        self.__service_print = self.__node.create_service(hsm_robot.srv.DebugPrint,
                                                          self.PRINT_SERVICE,
                                                          self.on_print_call)
        self.get_logger().info('ROSDebug service node initialized')

    def on_print_call(self, request, response):
        # Debug.print implementation
        self.get_logger().info('Debug.print: {}'.format(request.s))
        
        response.ok = True
        return response
