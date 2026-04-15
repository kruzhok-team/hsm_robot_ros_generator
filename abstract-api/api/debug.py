# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The abstract debug class declaration
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

class Debug(api.hsmobject.HSMObject):
    """Debug abstract interface API"""

    #def __new__(cls):
    #    instance = super().__new__(cls)
    #    instance.SIGNALS.union(set((,))) 
    #    return instance 
    
    def __init__(self):
        api.hsmobject.HSMObject.__init__(self)
        
    def print(self, s):
        """
        Print the string s
        
        Arguments:
            s:  string to print
        """
        pass
    
    def println(self, s):
        """
        Print the string s followed by new line character '\n'
        """
        pass

