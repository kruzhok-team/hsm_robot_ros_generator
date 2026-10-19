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
import gencode

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
    'bad_test_rule': ('test-rule', 'nTest'),
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


def test_rules_are_parsed():
    rules = gencode.parse_test_rules('MOVE_COMPLETED\n'
                                     'MOVE_COMPLETED x4 within 60  # the four corners\n'
                                     '\n'
                                     'never COLLISION_DETECTED\n')
    assert [(r.event, r.count, r.within, r.never) for r in rules] == [
        ('MOVE_COMPLETED', 1, None, False),
        ('MOVE_COMPLETED', 4, 60.0, False),
        ('COLLISION_DETECTED', 1, None, True)]


@pytest.mark.parametrize('line', ['MOVE_COMPLETED twice', 'never MOVE_COMPLETED within 5',
                                  'MOVE_COMPLETED x0', 'NO_SUCH_EVENT', 'never'])
def test_bad_rule_is_reported(line):
    with pytest.raises(gencode.ParserError) as error:
        gencode.parse_test_rules(line, 'nTest')
    assert error.value.rule == 'test-rule'
    assert error.value.element == 'nTest'


def test_valid_test_comment_is_accepted(tmp_path):
    # the comment changes nothing in the generated code, so it is added to a copy
    with open(diagrams('valid')['minimal'], encoding='utf-8') as f:
        text = f.read()
    comment = ('    <node id="nTest">\n      <data key="dNote">informal</data>\n'
               '      <data key="dData">ROS2 HSM Test\n\nTIMER_TICK x3 within 5\n'
               'never COLLISION_DETECTED</data>\n    </node>\n')
    position = text.index('    <node id="nInit">')
    diagram = tmp_path / 'tested.graphml'
    diagram.write_text(text[:position] + comment + text[position:], encoding='utf-8')
    result, findings = check(str(diagram), tmp_path)
    assert result.returncode == EXIT_OK, result.stderr
    assert findings == []
    rules, element = gencode.CodeGenerator(str(diagram)).test_rules()
    assert element == 'nTest'
    assert [r.line for r in rules] == ['TIMER_TICK x3 within 5', 'never COLLISION_DETECTED']
