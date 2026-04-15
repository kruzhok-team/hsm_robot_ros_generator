# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 navigation module implementation
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

import hsm_robot.constants
import hsm_robot.msg
import hsm_robot.srv

class ROSNavigation(rclpy.node.Node):

    OBJECT_NAME = 'hsm_ros_navigation'
    MOVE_TO_POINT_SERVICE = 'hsm_ros_navigation_move_to_point'
    STOP_SERVICE = 'hsm_ros_navigation_stop'

    def __init__(self):
        rclpy.node.Node.__init__(self.OBJECT_NAME)
        self.__msg_publisher = self.__node.create_publisher(hsm_robot.msg.SimpleMessage,
                                                            hsm_robot.constants.MESSAGES_TOPIC,
                                                            hsm_robot.constants.QUEUE_LEN)
        self.__service_move_to_point = self.__node.create_service(hsm_robot.srv.NavigationMoveToPoint,
                                                                  self.MOVE_TO_POINT_SERVICE,
                                                                  self.on_move_to_point_call)
        self.__service_stop = self.__node.create_service(hsm_robot.srv.NavigationStop,
                                                          self.STOP_SERVICE,
                                                          self.on_stop_call)
        # TODO: additional initialization
        # ...
        self.__node.get_logger().info('ROSNavigation service node initialized')

    def __path_found(self):
        msg = hsm_robot.msg.SimpleMessage()        
        msg.code = hsm_robot.msg.SimpleMessage.MSG_NAVIGATION_PATH_FOUND
        self.__msg_publisher.publish(msg)        
    # TODO: event publisher helpers
    # ...

    def on_move_to_point_call(self, request, response):
        # Navigation.move_to_point implementation
        pose = request.pose
        self.get_logger().info('Navigation.move_to_point({})'.format(pose))
        # TODO: move_to_point 
        # ...
        
        response.ok = True
        return response

    def on_stop_call(self, request, response):
        # Navigation.stop implementation
        self.get_logger().info('Navigation.stop()')
        # TODO: stop
        # ...
        
        response.ok = True
        return response

