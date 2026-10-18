# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The diagram check and the diagnostics file of the editor
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


import json
import os
import subprocess
import sys

import pytest

from conftest import EXIT_OK, EXIT_PARSER_ERROR, GENERATOR_DIR, diagrams, examples

pytestmark = pytest.mark.unit

INVALID = diagrams('invalid')

# the rule and the element of the finding of every rejected diagram
FINDINGS = {
    'no_initial': ('no-initial', None),
    # the library rejects the second initial pseudostate before the generator does
    'two_initial': ('cyberiadaml', None),
    'dangling_initial': ('no-initial-state', None),
    'unknown_module': ('unknown-module', 'nModules'),
    'undeclared_module': ('undeclared-module', 'nA'),
    'unknown_event': ('undefined-event', 'e1'),
    'unknown_event_internal': ('undefined-event', 'nA'),
    'empty_transition': ('empty-transition', 'e1'),
    'empty_internal_trigger': ('empty-trigger', 'nA'),
    'empty_state_name': ('empty-name', 'nA'),
    'spaced_name': ('spaced-name', 'nA'),
    'duplicate_name': ('duplicate-name', 'nB'),
}


def check(diagram, tmp_path):
    # check the diagram the way the editor plugin does, in an empty directory
    findings = tmp_path / 'diagnostics.json'
    command = [sys.executable, os.path.join(GENERATOR_DIR, 'hsm_generator.py'),
               diagram, '--check', '--json', str(findings)]
    result = subprocess.run(command, cwd=str(tmp_path), capture_output=True, text=True)
    with open(str(findings), encoding='utf-8') as f:
        return result, json.load(f)


@pytest.mark.parametrize('name', sorted(INVALID))
def test_invalid_diagram_has_one_finding(name, tmp_path):
    result, findings = check(INVALID[name], tmp_path)
    assert result.returncode == EXIT_PARSER_ERROR, result.stderr
    assert name in FINDINGS, 'no expected finding declared for {}'.format(name)
    rule, element = FINDINGS[name]
    assert len(findings) == 1, findings
    assert findings[0]['severity'] == 'error'
    assert findings[0]['rule'] == rule
    assert findings[0].get('element') == element
    # the editor checks a temporary copy, so the message does not name the file
    assert INVALID[name] not in findings[0]['message']


@pytest.mark.parametrize('name', sorted(set(diagrams('valid')) | set(examples())))
def test_valid_diagram_has_no_findings(name, tmp_path):
    diagram = {**diagrams('valid'), **examples()}[name]
    result, findings = check(diagram, tmp_path)
    assert result.returncode == EXIT_OK, result.stderr
    assert findings == []


def test_check_writes_no_package(tmp_path):
    check(examples()['turtle-square'], tmp_path)
    assert sorted(os.listdir(str(tmp_path))) == ['diagnostics.json']


def test_output_is_required_without_check(tmp_path):
    command = [sys.executable, os.path.join(GENERATOR_DIR, 'hsm_generator.py'),
               examples()['turtle-square']]
    result = subprocess.run(command, cwd=str(tmp_path), capture_output=True, text=True)
    assert result.returncode != EXIT_OK
    assert '-o' in result.stderr
    assert os.listdir(str(tmp_path)) == []
