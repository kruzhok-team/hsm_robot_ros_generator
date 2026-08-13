# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The generated code compared with the reference output
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

# The reference files catch every unintended change of the conversion and of the
# templates, including the changes which are still valid Python. Regenerate them with
# test/regold.sh when the change is intended and review the difference as a part of the
# patch.

import difflib
import os
import re

import pytest

from conftest import GOLDEN_DIR, controller_module, diagrams, examples, generate

pytestmark = pytest.mark.unit

VALID = dict(diagrams('valid'))
VALID.update(examples())

# the generator writes the year of the run into the header of the generated file
YEAR_RE = re.compile(r'^# Copyright \(C\) \d{4} ', re.M)


def normalize(text):
    return YEAR_RE.sub('# Copyright (C) YEAR ', text)


def golden_path(name):
    return os.path.join(GOLDEN_DIR, name + '.py.expected')


@pytest.mark.parametrize('name', sorted(VALID))
def test_generated_code_matches_the_reference(name, tmp_path):
    package = generate(VALID[name], tmp_path / 'pkg')
    module = os.path.join(package, 'hsm_controller', controller_module(package) + '.py')
    with open(module) as f:
        produced = normalize(f.read())
    reference = golden_path(name)
    assert os.path.isfile(reference), \
        'no reference file for {}; run test/regold.sh to record it'.format(name)
    with open(reference) as f:
        expected = f.read()
    if produced != expected:
        difference = '\n'.join(difflib.unified_diff(
            expected.splitlines(), produced.splitlines(),
            fromfile=reference, tofile=module, lineterm=''))
        pytest.fail('the generated {} differs from the reference; run test/regold.sh if '
                    'the change is intended:\n{}'.format(name, difference))


def test_every_reference_file_belongs_to_a_diagram():
    if not os.path.isdir(GOLDEN_DIR):
        return
    recorded = {f[:-len('.py.expected')] for f in os.listdir(GOLDEN_DIR)
                if f.endswith('.py.expected')}
    assert recorded <= set(VALID), \
        'the reference files {} have no diagram'.format(sorted(recorded - set(VALID)))
