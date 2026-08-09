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
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------

import argparse
import sys
import traceback

import gencode

DESCRIPTION = 'Generate a ROS2 HSM controller package from a CyberiadaML diagram.'
EPILOG = ('Note that the generated package is always named hsm_controller and declares a '
          'single console script, so only one state machine can be built from a given '
          'output directory: generating a second diagram into the same directory replaces '
          'the setup files and drops the entry point of the first one.')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)
    parser.add_argument('graphml', metavar='<diagram.graphml>',
                        help='the CyberiadaML diagram to convert')
    parser.add_argument('-o', '--output', metavar='DIR', default='.',
                        help='the directory to write the generated package into '
                             '(default: the current directory)')
    parser.add_argument('-f', '--force', action='store_true',
                        help='overwrite an already generated controller')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='do not report the generated files')
    args = parser.parse_args()

    try:
        g = gencode.CodeGenerator(args.graphml, output_dir=args.output,
                                  force=args.force, quiet=args.quiet)
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
