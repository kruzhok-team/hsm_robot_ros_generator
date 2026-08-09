# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The ROS2 service startup helpers shared by the caller interfaces
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

from hsm_controller.constants import SERVICE_STARTUP_TIMEOUT, SERVICE_STARTUP_LIMIT

class ServiceUnavailableError(Exception):
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg
    def __str__(self):
        return self.msg

def wait_for_service(node, client, description):
    # Wait for an HSM module service to appear, but give up after
    # SERVICE_STARTUP_LIMIT seconds instead of blocking the controller forever:
    # a module node that is never started used to leave the constructor spinning
    # with nothing but one log line per second to show for it.
    waited = 0.0
    while not client.wait_for_service(timeout_sec=SERVICE_STARTUP_TIMEOUT):
        waited += SERVICE_STARTUP_TIMEOUT
        if waited >= SERVICE_STARTUP_LIMIT:
            raise ServiceUnavailableError('{} service is not available after {} seconds'.format(
                description, SERVICE_STARTUP_LIMIT))
        node.get_logger().info('{} service not available'.format(description))
