# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 storage caller interface
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

import rclpy

from hsm_controller.service_utils import wait_for_service
import hsm_interfaces.srv

Storage = None

def _point_to_list(point):
    # the diagram code may pass a single number as a point as well as a coordinate
    # sequence, while the service always carries an array of numbers
    try:
        return [float(value) for value in point]
    except TypeError:
        return [float(point)]

class ROSStorageCaller:

    NEW_SERVICE = 'hsm_ros_storage_new'
    ADD_SERVICE = 'hsm_ros_storage_add'
    LOAD_SERVICE = 'hsm_ros_storage_load'

    def __init__(self, node):
        global Storage
        if Storage is None:
            self.__node = node

            # new
            self.__client_new = self.__node.create_client(hsm_interfaces.srv.StorageNew,
                                                          self.NEW_SERVICE)
            self.__new_request = hsm_interfaces.srv.StorageNew.Request()
            wait_for_service(self.__node, self.__client_new, 'ROS Storage caller new')

            # add
            self.__client_add = self.__node.create_client(hsm_interfaces.srv.StorageAdd,
                                                          self.ADD_SERVICE)
            self.__add_request = hsm_interfaces.srv.StorageAdd.Request()
            wait_for_service(self.__node, self.__client_add, 'ROS Storage caller add')

            # load
            self.__client_load = self.__node.create_client(hsm_interfaces.srv.StorageLoad,
                                                           self.LOAD_SERVICE)
            self.__load_request = hsm_interfaces.srv.StorageLoad.Request()
            wait_for_service(self.__node, self.__client_load, 'ROS Storage caller load')

            # next() and has_data() have to answer immediately inside the HSM actions, so
            # the points read by load() are kept here instead of being asked for one by
            # one: a blocking service call from a state machine handler would deadlock
            # the single-threaded executor of the controller node
            self.__points = {}
            self.__cursors = {}

            self.__node.get_logger().info('ROS Storage caller inerface initialized')
            Storage = self

    def new(self, name, array):
        points = [_point_to_list(array)]
        self.__points[name] = points
        self.__cursors[name] = 0
        self.__new_request.name = name
        self.__new_request.array = points[0]
        self.__client_new.call_async(self.__new_request)

    def add(self, name, point):
        point = _point_to_list(point)
        if name not in self.__points:
            self.__points[name] = []
            self.__cursors[name] = 0
        self.__points[name].append(point)
        self.__add_request.name = name
        self.__add_request.point = point
        self.__client_add.call_async(self.__add_request)

    def load(self, name):
        # the only blocking call of the interface: the diagram asks for the stored data
        # before reading it, the same way the timer caller initializes its ticks
        self.__load_request.name = name
        client_call = self.__client_load.call_async(self.__load_request)
        rclpy.spin_until_future_complete(self.__node, client_call)
        result = client_call.result()
        if result is None or not result.ok:
            self.__node.get_logger().info('ROS Storage caller load({}) failed'.format(name))
            return False
        points = []
        position = 0
        for length in result.lengths:
            points.append([float(value) for value in result.data[position:position + length]])
            position += length
        self.__points[name] = points
        self.__cursors[name] = 0
        self.__node.get_logger().info('ROS Storage caller loaded {} point(s) from {}'.format(
            len(points), name))
        return True

    def next(self, name):
        # returns the point as the list of numbers, or None when the storage is exhausted
        if not self.has_data(name):
            return None
        point = self.__points[name][self.__cursors[name]]
        self.__cursors[name] += 1
        return point

    def has_data(self, name):
        if name not in self.__points:
            return False
        return self.__cursors[name] < len(self.__points[name])
