#!/usr/bin/python3
# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# HSM (CyberiadaML diagram)-to-Python conversion script
#
# Copyright (C) 2025-2026 Alexey Fedoseev <aleksey@fedoseev.net>
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

import sys
import traceback

import gencode

def usage():
    print('usage: {} <diagram.graphml>'.format(sys.argv[0]))
    sys.exit(1)

if __name__ == '__main__':

    if len(sys.argv) != 2:
        usage()

    graph = sys.argv[1]

    try:
        g = gencode.CodeGenerator(graph)
        g.generate_code()
    except gencode.ParserError as e:
        sys.stderr.write('Graph parsing error: {}\n'.format(e))
        sys.exit(1)
    except gencode.GeneratorError as e:
        sys.stderr.write('Code generating error: {}\n'.format(e))
        sys.exit(2)
    except gencode.ConvertorError as e:
        sys.stderr.write('Strange convertor error: {}\n'.format(e))
        sys.exit(3)
    except Exception as e:
        sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
        sys.stderr.write('{}\n'.format(traceback.format_exc()))
        sys.exit(4)

    sys.exit(0)
