# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 timer module implementation
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

class ROSTimer(rclpy.node.Node):

    OBJECT_NAME = 'hsm_ros_timer'
    TICK_SERVICE = 'hsm_ros_timer_init_ticks'
    START_SERVICE = 'hsm_ros_timer_start'
    STOP_SERVICE = 'hsm_ros_timer_stop'

    def __init__(self):
        rclpy.node.Node.__init__(self.OBJECT_NAME)
        self.__msg_publisher = self.__node.create_publisher(hsm_robot.msg.SimpleMessage,
                                                            hsm_robot.constants.MESSAGES_TOPIC,
                                                            hsm_robot.constants.QUEUE_LEN)
        self.__service_tick = self.__node.create_service(hsm_robot.srv.TimerTick,
                                                          self.TICK_SERVICE,
                                                          self.on_init_ticks_call)
        self.__service_start = self.__node.create_service(hsm_robot.srv.TimerStart,
                                                          self.START_SERVICE,
                                                          self.on_start_call)
        self.__service_stop = self.__node.create_service(hsm_robot.srv.TimerStop,
                                                          self.STOP_SERVICE,
                                                          self.on_stop_call)
        # TODO: additional initialization
        # ...
        self.__node.get_logger().info('ROSTimer service node initialized')

    def __tick_timer_callback(self):
        msg = hsm_robot.msg.SimpleMessage()
        msg.code = hsm_robot.msg.SimpleMessage.MSG_TIMER_TICK
        self.__msg_publisher.publish(msg)

    def __second_timer_callback(self):
        msg = hsm_robot.msg.SimpleMessage()
        msg.code = hsm_robot.msg.SimpleMessage.MSG_TIMER_1SEC
        self.__msg_publisher.publish(msg)

    def __minute_timer_callback(self):
        msg = hsm_robot.msg.SimpleMessage()        
        msg.code = hsm_robot.msg.SimpleMessage.MSG_TIMER_1MIN
        self.__msg_publisher.publish(msg)

    def __timer_elapsed(self):
        msg = hsm_robot.msg.SimpleMessage()        
        msg.code = hsm_robot.msg.SimpleMessage.MSG_TIMER_ELAPSED
        self.__msg_publisher.publish(msg)        

    def on_init_ticks_call(self, request, resonse):
        # Start standard timers
        if request.run_tick:
            self.__tick_timer = self.create_timer(robot.constants.TICK_LEN, self.__tick_timer_callback)
        if request.run_tick_1sec:
            self.__second_timer = self.create_timer(1.0, self.__second_timer_callback)
        if request.run_tick_1min:
            self.__minute_timer = self.create_timer(60.0, self.__minute_timer_callback)
        response.ok = True
        return response

    def on_start_call(self, request, response):
        # Timer.start implementation
        period = request.timeout / 1000.0 # convert to seconds
        repeat = request.repeat
        self.get_logger().info('Timer.start({}, {})'.format(period, repeat))
        # TODO: start timer

        response.ok = True
        return response

    def on_stop_call(self, request, response):
        # Timer.stop implementation
        self.get_logger().info('Timer.stop()')
        # TODO: stop timer
        
        response.ok = True
        return response

