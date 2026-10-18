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
import json
import os
import sys
import traceback

import gencode
import hsmplugin

DESCRIPTION = 'Generate a ROS2 HSM controller package from a CyberiadaML diagram.'
EPILOG = ('Note that the generated package is always named hsm_controller and declares a '
          'single console script, so only one state machine can be built from a given '
          'output directory: generating a second diagram into the same directory replaces '
          'the setup files and drops the entry point of the first one.')

EDITOR_PLUGIN_DIR = 'editor-plugin'


def write_diagnostics(path, graphml, error=None):
    # the diagnostics file of the CyberiadaPro editor: empty for a clean diagram. The
    # editor passes a temporary copy, so the file name is left out of the message
    findings = []
    if error is not None:
        message = str(error).strip().replace('The graph {} '.format(graphml), 'The diagram ')
        finding = {'severity': 'error',
                   'rule': getattr(error, 'rule', None) or 'generator',
                   'message': message}
        if getattr(error, 'element', None):
            finding['element'] = error.element
        findings.append(finding)
    with open(path, 'w', encoding='utf-8') as out:
        json.dump(findings, out, indent=1, ensure_ascii=False)


def install_editor_plugin(target):
    try:
        folder = hsmplugin.install(gencode.shipped_dir(EDITOR_PLUGIN_DIR),
                                   os.path.abspath(sys.argv[0]), target or None)
    except hsmplugin.PluginError as e:
        sys.stderr.write('Editor plugin error: {}\n'.format(e))
        sys.exit(2)
    print('Installed the editor plugin into {}'.format(folder))
    sys.exit(0)


def main():

    parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)
    parser.add_argument('graphml', metavar='<diagram.graphml>', nargs='?',
                        help='the CyberiadaML diagram to convert')
    # the output directory is required unless only checking: the generator used to write
    # into the current directory by default, which overwrote its own sources when it was
    # run from the generator checkout
    parser.add_argument('-o', '--output', metavar='DIR',
                        help='the directory to write the generated package into')
    parser.add_argument('-f', '--force', action='store_true',
                        help='overwrite an already generated controller')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='do not report the generated files')
    parser.add_argument('--check', action='store_true',
                        help='check the diagram only, write no package')
    parser.add_argument('--json', metavar='FILE',
                        help='write the findings as the diagnostics file of the editor')
    parser.add_argument('--install-editor-plugin', metavar='DIR', nargs='?', const='',
                        help='install the CyberiadaPro plugin into DIR/hsm-ros2 '
                             '(default: the user plugin folder)')
    args = parser.parse_args()

    if args.install_editor_plugin is not None:
        install_editor_plugin(args.install_editor_plugin)
    if args.graphml is None:
        parser.error('the diagram is required')
    if args.output is None and not args.check:
        parser.error('the output directory -o is required')

    def fail(error, prefix, code):
        sys.stderr.write('{}: {}\n'.format(prefix, error))
        if args.json is not None:
            write_diagnostics(args.json, args.graphml, error)
        sys.exit(code)

    try:
        g = gencode.CodeGenerator(args.graphml, output_dir=args.output or gencode.SETUP_TARGET_DIR,
                                  force=args.force, quiet=args.quiet)
        if not args.check:
            g.generate_code()
    except gencode.ParserError as e:
        fail(e, 'Graph parsing error', 1)
    except gencode.GeneratorError as e:
        fail(e, 'Code generating error', 2)
    except gencode.ConvertorError as e:
        fail(e, 'Strange convertor error', 3)
    except Exception as e:
        sys.stderr.write('Unexpected exception: {}\n'.format(e.__class__))
        sys.stderr.write('{}\n'.format(traceback.format_exc()))
        if args.json is not None:
            write_diagnostics(args.json, args.graphml, gencode.GeneratorError(str(e)))
        sys.exit(4)
    if args.json is not None:
        write_diagnostics(args.json, args.graphml)
    sys.exit(0)


if __name__ == '__main__':
    main()
