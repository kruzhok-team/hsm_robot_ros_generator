# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The shared fixtures of the code generator tests
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

import os
import subprocess
import sys

import pytest

GENERATOR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAGRAMS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diagrams')
EXAMPLES_DIR = os.path.join(GENERATOR_DIR, 'examples')
GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'golden')
FLAKE8_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ament_flake8.ini')

# the exit codes of hsm_generator.py
EXIT_OK = 0
EXIT_PARSER_ERROR = 1
EXIT_GENERATOR_ERROR = 2
EXIT_CONVERTOR_ERROR = 3
EXIT_UNEXPECTED = 4


def diagrams(kind):
    # the diagram files of test/diagrams/<kind>, by name
    directory = os.path.join(DIAGRAMS_DIR, kind)
    return {os.path.splitext(f)[0]: os.path.join(directory, f)
            for f in sorted(os.listdir(directory)) if f.endswith('.graphml')}


def examples():
    # the example diagrams shipped with the generator, by name
    return {os.path.splitext(f)[0]: os.path.join(EXAMPLES_DIR, f)
            for f in sorted(os.listdir(EXAMPLES_DIR)) if f.endswith('.graphml')}


def run_generator(diagram, output, *args):
    # run the generator the way the user runs it
    command = [sys.executable, os.path.join(GENERATOR_DIR, 'hsm_generator.py'),
               diagram, '-o', str(output)] + list(args)
    return subprocess.run(command, cwd=GENERATOR_DIR, capture_output=True, text=True)


def generate(diagram, output, *args):
    # generate a package and fail the test if the generator reports an error
    result = run_generator(diagram, output, '-q', *args)
    assert result.returncode == EXIT_OK, \
        'generating {} failed with {}:\n{}'.format(diagram, result.returncode, result.stderr)
    return str(output)


def controller_module(package_dir):
    # the name of the generated controller module of a generated package
    library = {os.path.splitext(f)[0] for f in os.listdir(GENERATOR_DIR + '/hsm_controller')
               if f.endswith('.py')}
    names = [os.path.splitext(f)[0]
             for f in sorted(os.listdir(os.path.join(package_dir, 'hsm_controller')))
             if f.endswith('.py') and os.path.splitext(f)[0] not in library]
    assert len(names) == 1, 'expected one generated module, got {}'.format(names)
    return names[0]


@pytest.fixture
def generated(tmp_path):
    # generate a diagram into a temporary directory and return the package path
    def _generate(diagram, *args):
        return generate(diagram, tmp_path / 'pkg', *args)
    return _generate
