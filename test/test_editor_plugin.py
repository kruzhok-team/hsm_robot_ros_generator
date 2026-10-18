# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The CyberiadaPro editor plugin: the descriptor, the adapter and the installer
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
import shutil
import subprocess

import pytest

from conftest import GENERATOR_DIR, diagrams, examples

pytestmark = pytest.mark.unit

PLUGIN_DIR = os.path.join(GENERATOR_DIR, 'editor-plugin')
ADAPTER = os.path.join(PLUGIN_DIR, 'ros2_env')
EXIT_ADAPTER_USAGE = 5
RESULTS = ('replace', 'new-document', 'diagnostics', 'files', 'log')


def descriptor():
    with open(os.path.join(PLUGIN_DIR, 'plugin.json'), encoding='utf-8') as f:
        return json.load(f)


def adapter(*args, env=None, cwd=None):
    return subprocess.run(['bash', ADAPTER] + list(args), capture_output=True, text=True,
                          env=env, cwd=cwd)


def test_descriptor_is_consistent():
    plugin = descriptor()
    assert plugin['api'] == 1
    assert plugin['id'] == 'hsm-ros2'
    assert plugin['name'] == 'HSM ROS2'
    parameters = {p['id'] for p in plugin['parameters']}
    assert sorted(a['id'] for a in plugin['actions']) == ['build', 'check', 'generate']
    for action in plugin['actions']:
        assert action['result'] in RESULTS
        assert set(action['parameters']) <= parameters
        assert action['argv'][0] == '${plugin_dir}/ros2_env'
        if 'icon' in action:
            assert os.path.isfile(os.path.join(PLUGIN_DIR, action['icon']))
        if action['result'] == 'files':
            assert action['outdir'] in parameters


def test_every_text_is_translated():
    plugin = descriptor()
    with open(os.path.join(PLUGIN_DIR, 'i18n', 'ru.json'), encoding='utf-8') as f:
        ru = json.load(f)
    assert ru[plugin['name']] == 'ROS2 ПРИМС'
    texts = [plugin['description']]
    for item in plugin['parameters'] + plugin['actions']:
        texts += [item[k] for k in ('label', 'description', 'filter') if k in item]
    assert [t for t in texts if t not in ru] == []


def test_adapter_sources_the_setup_and_runs_the_command(tmp_path):
    setup = tmp_path / 'setup.bash'
    setup.write_text('export HSM_ROS2_TEST=sourced\n')
    result = adapter('--setup', str(setup), 'printenv', 'HSM_ROS2_TEST')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'sourced'


def test_adapter_enters_the_workspace(tmp_path):
    ws = tmp_path / 'ws'
    (ws / 'install').mkdir(parents=True)
    (ws / 'install' / 'setup.bash').write_text('export HSM_ROS2_WS=sourced\n')
    result = adapter('--setup', '', '--cd', str(ws), 'bash', '-c', 'pwd; echo $HSM_ROS2_WS')
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == [str(ws), 'sourced']


def test_adapter_passes_the_exit_code(tmp_path):
    assert adapter('--setup', '', 'bash', '-c', 'exit 3').returncode == 3


@pytest.mark.parametrize('args', [('--setup', '/absent/setup.bash', 'true'),
                                  ('--setup', ''),
                                  ('--setup', '', 'absent-command-of-the-test')])
def test_adapter_reports_a_usage_error(args):
    result = adapter(*args)
    assert result.returncode == EXIT_ADAPTER_USAGE
    assert result.stderr.startswith('ros2_env: ')


def test_adapter_runs_the_generator_of_the_source_tree(tmp_path):
    env = dict(os.environ)
    env.pop('HSM_GENERATOR', None)
    result = adapter('--setup', '', 'hsm_generator', examples()['turtle-square'], '--check',
                     env=env, cwd=str(tmp_path))
    assert result.returncode == 0, result.stderr


def test_installer_pins_the_generator_and_the_setup(tmp_path):
    import hsmplugin
    setup = tmp_path / 'setup.bash'
    setup.write_text('')
    folder = hsmplugin.install(PLUGIN_DIR, '/opt/gen/hsm_generator', str(tmp_path),
                               str(setup))
    assert folder == os.path.join(str(tmp_path), 'hsm-ros2')
    with open(os.path.join(folder, 'plugin.json'), encoding='utf-8') as f:
        plugin = json.load(f)
    assert plugin['env']['HSM_GENERATOR'] == '/opt/gen/hsm_generator'
    assert [p['default'] for p in plugin['parameters'] if p['id'] == 'setup'] == [str(setup)]
    assert os.path.isfile(os.path.join(folder, 'ros2_env'))
    # an earlier copy is replaced, a foreign folder is not
    hsmplugin.install(PLUGIN_DIR, '/opt/gen/hsm_generator', str(tmp_path), str(setup))
    foreign = tmp_path / 'foreign'
    (foreign / 'hsm-ros2').mkdir(parents=True)
    with pytest.raises(hsmplugin.PluginError):
        hsmplugin.install(PLUGIN_DIR, '/opt/gen/hsm_generator', str(foreign))


EDITOR = os.environ.get('CYBERIADA_PRO') or shutil.which('CyberiadaPro')
# the generator needs a sourced ROS 2 environment, the editor run starts from it
SETUP = os.path.join(os.environ.get('COLCON_PREFIX_PATH', '').split(os.pathsep)[0],
                     'setup.bash')


def editor(diagram, action, *params):
    command = [EDITOR, '--batch', diagram, '--plugin-path', GENERATOR_DIR,
               '--run-plugin', 'hsm-ros2:' + action, '--plugin-param', 'setup=' + SETUP,
               '--dump-plugin']
    for p in params:
        command += ['--plugin-param', p]
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    return subprocess.run(command, capture_output=True, text=True, env=env, timeout=120)


@pytest.mark.skipif(EDITOR is None or not os.path.isfile(SETUP),
                    reason='needs CyberiadaPro and a sourced workspace')
def test_editor_checks_and_generates(tmp_path):
    result = editor(diagrams('invalid')['unknown_event'], 'check')
    assert result.returncode == 0, result.stderr
    assert 'error undefined-event e1:' in result.stdout
    result = editor(examples()['turtle-square'], 'generate', 'ws={}'.format(tmp_path / 'ws'))
    assert result.returncode == 0, result.stderr
    assert 'new src/hsm_controller/hsm_controller/turtle_square.py' in result.stdout
