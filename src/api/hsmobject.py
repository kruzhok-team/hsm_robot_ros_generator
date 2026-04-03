# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The abstract HSM diagram object class declaration
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

class HSMObject:
    """HSM Object abstract interface API"""

    SIGNALS = set([])
    
    def __init__(self):
        self.__signal_queue = []

    def send(self, signal):
        if signal in SIGNALS:
            self.__signal_queue.append(signal)

    def get_signal(self):
        if self.__signal_queue:
            return self.__signal_queue.pop(0)
        else:
            return None
