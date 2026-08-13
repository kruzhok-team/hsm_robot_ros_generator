# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The errors the generator reports for the diagrams it rejects
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

import pytest

from conftest import (EXIT_GENERATOR_ERROR, EXIT_OK, EXIT_PARSER_ERROR, diagrams,
                      examples, generate, run_generator)

pytestmark = pytest.mark.unit

INVALID = diagrams('invalid')

# the phrase the report of every rejected diagram has to contain, so that the message
# names the problem and not only the file
REPORTED = {
    'no_initial': 'no initial pseudostate',
    'two_initial': 'initial pseudostate',
    'dangling_initial': 'no initial state',
    'unknown_module': 'unknown module',
    'undeclared_module': 'does not declare it',
    'unknown_event': 'undefined event',
    'unknown_event_internal': 'undefined event',
    'empty_transition': 'empty external transition',
    'empty_internal_trigger': 'action text',
    'empty_state_name': 'empty name',
    'spaced_name': 'spaces in name',
    'duplicate_name': 'same qualified name',
}


@pytest.mark.parametrize('name', sorted(INVALID))
def test_invalid_diagram_is_rejected(name, tmp_path):
    result = run_generator(INVALID[name], tmp_path / 'pkg')
    assert result.returncode == EXIT_PARSER_ERROR, \
        'expected a parsing error for {}, got {}:\n{}'.format(name, result.returncode,
                                                              result.stderr)
    assert name in REPORTED, 'no expected message declared for {}'.format(name)
    assert REPORTED[name] in result.stderr, \
        'the report of {} does not mention "{}":\n{}'.format(name, REPORTED[name],
                                                             result.stderr)


@pytest.mark.parametrize('name', sorted(INVALID))
def test_rejected_diagram_writes_no_controller(name, tmp_path):
    output = tmp_path / 'pkg'
    run_generator(INVALID[name], output)
    controllers = []
    directory = os.path.join(str(output), 'hsm_controller')
    if os.path.isdir(directory):
        controllers = [f for f in os.listdir(directory) if f.endswith('.py')]
    assert controllers == [], 'the rejected {} produced {}'.format(name, controllers)


def test_missing_file_is_reported_as_a_parsing_error(tmp_path):
    result = run_generator(str(tmp_path / 'absent.graphml'), tmp_path / 'pkg')
    assert result.returncode == EXIT_PARSER_ERROR
    assert 'FileException' in result.stderr
    # the report names the problem instead of dumping a traceback
    assert 'Traceback' not in result.stderr


def test_file_which_is_not_a_diagram_is_reported(tmp_path):
    not_a_diagram = tmp_path / 'plain.graphml'
    not_a_diagram.write_text('this is not a graphml document\n')
    result = run_generator(str(not_a_diagram), tmp_path / 'pkg')
    assert result.returncode == EXIT_PARSER_ERROR
    assert 'Traceback' not in result.stderr


def test_existing_controller_is_not_replaced(tmp_path):
    diagram = examples()['turtle-square']
    output = tmp_path / 'pkg'
    generate(diagram, output)
    result = run_generator(diagram, output)
    assert result.returncode == EXIT_GENERATOR_ERROR
    assert '--force' in result.stderr


def test_force_replaces_the_controller(tmp_path):
    diagram = examples()['turtle-square']
    output = tmp_path / 'pkg'
    generate(diagram, output)
    # regenerating over a complete package used to fail on the existing directories
    result = run_generator(diagram, output, '-f')
    assert result.returncode == EXIT_OK, result.stderr


def test_quiet_generates_the_same_package(tmp_path):
    diagram = examples()['turtle-square']
    loud = generate(diagram, tmp_path / 'loud')
    result = run_generator(diagram, tmp_path / 'quiet', '-q')
    assert result.returncode == EXIT_OK
    assert result.stdout == '', 'the quiet mode reported {}'.format(result.stdout)
    # the quiet mode used to report nothing because it generated nothing
    quiet_files = sorted(os.listdir(os.path.join(str(tmp_path / 'quiet'), 'hsm_controller')))
    loud_files = sorted(os.listdir(os.path.join(loud, 'hsm_controller')))
    assert quiet_files == loud_files
