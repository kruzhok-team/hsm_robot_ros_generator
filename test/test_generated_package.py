# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The completeness and the style of the package the generator produces
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

import filecmp
import os
import subprocess
import sys

import pytest

import gencode
from conftest import FLAKE8_CONFIG, GENERATOR_DIR, controller_module, diagrams, examples, generate

pytestmark = pytest.mark.unit

VALID = dict(diagrams('valid'))
VALID.update(examples())


def test_the_package_carries_the_runtime_library(tmp_path):
    package = generate(examples()['turtle-square'], tmp_path / 'pkg')
    library = os.path.join(package, 'hsm_controller')
    for name in gencode.LIBRARY_FILES:
        assert os.path.isfile(os.path.join(library, name)), '{} is missing'.format(name)


def test_the_library_is_copied_unchanged(tmp_path):
    package = generate(examples()['turtle-square'], tmp_path / 'pkg')
    for name in gencode.LIBRARY_FILES:
        source = os.path.join(gencode.LIBRARY_DIR, name)
        target = os.path.join(package, 'hsm_controller', name)
        assert filecmp.cmp(source, target, shallow=False), '{} was changed'.format(name)


def test_the_package_carries_the_setup_files(tmp_path):
    package = generate(examples()['turtle-square'], tmp_path / 'pkg')
    for name in ('package.xml', 'setup.py', 'setup.cfg'):
        assert os.path.isfile(os.path.join(package, name)), '{} is missing'.format(name)
    assert os.path.isfile(os.path.join(package, 'resource', 'hsm_controller'))


def test_the_controller_is_named_after_the_state_machine(tmp_path):
    package = generate(VALID['minimal'], tmp_path / 'pkg')
    assert controller_module(package) == 'minimal'


@pytest.mark.parametrize('name', sorted(VALID))
def test_the_generated_code_compiles(name, tmp_path):
    package = generate(VALID[name], tmp_path / 'pkg')
    module = os.path.join(package, 'hsm_controller', controller_module(package) + '.py')
    result = subprocess.run([sys.executable, '-m', 'py_compile', module],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('name', sorted(VALID))
def test_the_generated_code_passes_the_linters(name, tmp_path):
    package = generate(VALID[name], tmp_path / 'pkg')
    # the code the framework writes is held to the style of the code written by hand
    result = subprocess.run(
        [sys.executable, '-m', 'flake8', '--config', FLAKE8_CONFIG, 'hsm_controller', 'setup.py'],
        cwd=package, capture_output=True, text=True)
    assert result.returncode == 0, 'the generated {} has style errors:\n{}'.format(
        name, result.stdout)


def test_the_generator_writes_only_into_the_output_directory(tmp_path):
    before = sorted(os.listdir(GENERATOR_DIR))
    generate(VALID['minimal'], tmp_path / 'pkg')
    assert sorted(os.listdir(GENERATOR_DIR)) == before
