# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 implementation constants
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

MESSAGES_TOPIC = '/hsm_ros_msg' # the ROS2 topic for HSM messages
FRAME_ID = 'hsm_ros_api'        # the ROS2 frame for HSM messages
MSG_QUEUE_LEN = 10              # the ROS2 messages queue length
LOOP_TIME = 0.05                # loop timer
TICK_LEN = 0.1                  # tick event timer

# HSM modules names
HSM_DEBUG =      'Debug'
HSM_NAVIGATION = 'Navigation'
HSM_TIMER =      'Timer'

# HSM events
import hsm_controller.constants
import hsm_interface.msg

HSM_TICK_EVENT = 'TIMER_TICK'
HSM_TICK_1S_EVENT = 'TIMER_TICK_1S'
HSM_TICK_1M_EVENT = 'TIMER_TICK_1M'

HSM_EVENTS = {
    HSM_DEBUG:      (),
    HSM_TIMER:      {hsm_interface.msg.SimpleMessage.MSG_TIMER_ELAPSED: 'TIMER_ELAPSED',
                     hsm_interface.msg.SimpleMessage.MSG_TIMER_TICK: HSM_TICK_EVENT,
                     hsm_interface.msg.SimpleMessage.MSG_TIMER_TICK_1S: HSM_TICK_1S_EVENT,
                     hsm_interface.msg.SimpleMessage.MSG_TIMER_TICK_1M: HSM_TICK_1M_EVENT}
    HSM_NAVIGATION: {hsm_interface.msg.SimpleMessage.MSG_NAVIGATION_PATH_FOUND: 'PATH_FOUND'
                     hsm_interface.msg.SimpleMessage.MSG_NAVIGATION_PATH_NOT_FOUND: 'PATH_NOT_FOUND' 
                     hsm_interface.msg.SimpleMessage.MSG_NAVIGATION_MOVE_COMPLETED: 'MOVE_COMPLETED'
                     hsm_interface.msg.SimpleMessage.MSG_NAVIGATION_COLLISION_WARNING: 'COLLISION_WARNING'
                     hsm_interface.msg.SimpleMessage.MSG_NAVIGATION_COLLISION_DETECTED: 'COLLISION_DETECTED'},
}
