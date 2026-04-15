# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The abstract navigation class declaration
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

import api.hsmobject

class Navigation(api.hsmobject.HSMObject):
    """Navigation abstract interface API"""

    # events constants
    PATH_FOUND = 'PATH_FOUND'
    PATH_NOT_FOUND = 'PATH_NOT_FOUND'
    MOVE_COMPLETED = 'MOVE_COMPLETED'
    COLLISION_WARNING = 'COLLISION_WARNING'
    COLLISION_DETECTED = 'COLLISION_DETECTED'

    def __new__(cls):
        instance = super().__new__(cls)
        instance.SIGNALS.union(set((PATH_FOUND,
                                    PATH_NOT_FOUND,
                                    MOVE_COMPLETED,
                                    COLLISION_WARNING,
                                    COLLISION_DETECTED)))
        return instance 

    def __init__(self):
        api.hsmobject.HSMObject.__init__(self)
        self.__moving = False

    def move_to_point(self, x, y, theta=None):
        """
        Navigate robot to point with coordinates (x, y)
        
        Arguments:
            x:     X coordinate in map frame (meters)
            y:     Y coordinate in map frame (meters)
            theta: Optional orientation (radians)
        """
        self.__moving = True

    def stop(self):
        """
        Stop navigation
        """
        self.__moving = False

    def is_moving(self):
        """
        Get navigation status
        
        Returns:
            current status of the navigation object
            
        """
        return self.__moving

