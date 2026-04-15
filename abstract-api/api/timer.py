# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The abstract timer class declaration
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

class Timer(api.hsmobject.HSMObject):
    """Timer abstract interface API"""

    # events constants
    TIMER_ELAPSED = 'TIMER_ELAPSED'
    TIMER_TICK = 'TIMER_TICK'
    TIMER_TICK_1S = 'TIMER_TICK_1S'
    TIMER_TICK_1M = 'TIMER_TICK_1M'
    
    def __new__(cls):
        instance = super().__new__(cls)
        instance.SIGNALS.union(set((TIMER_ELAPSED,
                                    TIMER_TICK,
                                    TIMER_TICK_1S,
                                    TIMER_TICK_1M))) 
        return instance 
    
    def __init__(self):
        api.hsmobject.HSMObject.__init__(self)
        
    def start(self, timeout, repeat=False):
        """
        Start the timer
        
        Arguments:
            timeout: set timeous (milliseconds)
            repeat:  rerun timer on timeout (boolean, default is False)
        """
        pass
    
    def stop(self):
        """
        Stop the timer
        """
        pass

