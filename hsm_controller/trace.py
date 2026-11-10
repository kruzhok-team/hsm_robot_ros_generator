# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The trace of the controller: its steps published for an observer
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

import json
import time

import hsmd

import hsm_controller.constants

TIME_DIGITS = 3
COMPLETION_ORIGIN = 'model'
API_ORIGIN = 'system'


def step_message(session, dispatcher, outcomes, records, now, elements, error=None):
    # the message of a step (docs/editor_plugin.md, The trace), None for a tick firing
    # nothing; session is hsmd.session; elements maps the model ids to the diagram's, and
    # an id without a diagram element is left out
    def ids(values):
        return session.unique(elements[v] for v in values if v in elements)

    history = []
    for outcome in outcomes:
        if outcome is None:
            continue
        if outcome.event.name == hsm_controller.constants.HSM_TICK_EVENT and \
                outcome.status == hsmd.DROPPED:
            continue
        origin = COMPLETION_ORIGIN if outcome.event.name == '' else API_ORIGIN
        row = session.history_row(outcome, now, origin)
        row['fired'] = ids(row['fired'])
        history.append(row)
    fired = ids(session.fired(records))
    if not history and not fired and error is None:
        return None
    message = {'time': round(now, TIME_DIGITS), 'history': history, 'fired': fired,
               'active': ids(session.active(dispatcher)),
               'finished': error is not None or dispatcher.finished()}
    if error is not None:
        message['error'] = error
    return message


class Tracer:
    # publishes the steps of the dispatcher on TRACE_TOPIC while enabled; the ROS2
    # modules are imported only then, so the tests of the controller need no ROS2

    def __init__(self, node, enabled, elements, queue_length):
        self.__node = node
        self.__elements = elements if elements is not None else {}
        self.__records = []
        self.__start = time.monotonic()
        self.__publisher = None
        self.__session = None
        if not enabled:
            return
        import hsmd.session  # pylint: disable=import-outside-toplevel
        if not hasattr(hsmd.session, 'history_row'):
            node.get_logger().error('The trace needs hsm-dispatcher-py with hsmd.session.history_row')
            return
        import rclpy.qos  # pylint: disable=import-outside-toplevel
        import std_msgs.msg  # pylint: disable=import-outside-toplevel
        self.__session = hsmd.session
        self.__string = std_msgs.msg.String
        qos = rclpy.qos.QoSProfile(depth=queue_length,
                                   reliability=rclpy.qos.ReliabilityPolicy.RELIABLE,
                                   durability=rclpy.qos.DurabilityPolicy.TRANSIENT_LOCAL)
        self.__publisher = node.create_publisher(self.__string, hsm_controller.constants.TRACE_TOPIC, qos)

    def hook(self):
        # the trace argument of the dispatcher
        return self.__records.append if self.__publisher is not None else None

    def step(self, dispatcher, outcomes, error=None):
        if self.__publisher is None:
            return
        message = step_message(self.__session, dispatcher, outcomes, self.__records,
                               time.monotonic() - self.__start, self.__elements, error)
        del self.__records[:]
        if message is not None:
            self.__publisher.publish(self.__string(data=json.dumps(message, separators=(',', ':'))))
