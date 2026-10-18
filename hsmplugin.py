# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The installer of the CyberiadaPro editor plugin
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

import json
import os
import shutil

PLUGIN_ID = 'hsm-ros2'
DESCRIPTOR = 'plugin.json'
EDITOR_FOLDER = ('Cyberiada', 'CyberiadaPro', 'plugins')
SETUP_PARAMETER = 'setup'
SETUP_SCRIPT = 'setup.bash'
GENERATOR_VARIABLE = 'HSM_GENERATOR'


# no plugin to install, or the copy failed
class PluginError(Exception):
    pass


def user_folder(environ=None):
    # the user plugin folder of the editor on Linux
    environ = os.environ if environ is None else environ
    home = environ.get('HOME') or os.path.expanduser('~')
    base = environ.get('XDG_DATA_HOME') or os.path.join(home, '.local', 'share')
    return os.path.join(base, *EDITOR_FOLDER)


def ros_setup(environ=None):
    # the setup script of the ROS 2 environment the installer runs in: the first colcon
    # prefix (the overlay holding this package), else the distribution
    environ = os.environ if environ is None else environ
    candidates = [os.path.join(p, SETUP_SCRIPT)
                  for p in environ.get('COLCON_PREFIX_PATH', '').split(os.pathsep) if p]
    if environ.get('ROS_DISTRO'):
        candidates.append(os.path.join('/opt/ros', environ['ROS_DISTRO'], SETUP_SCRIPT))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _ours(folder):
    try:
        with open(os.path.join(folder, DESCRIPTOR), encoding='utf-8') as file:
            return json.load(file).get('id') == PLUGIN_ID
    except (OSError, ValueError, AttributeError):
        return False


def pinned(descriptor, generator, setup):
    # the descriptor running the given generator in the given environment
    descriptor.setdefault('env', {})[GENERATOR_VARIABLE] = generator
    if setup:
        for parameter in descriptor.get('parameters', []):
            if parameter.get('id') == SETUP_PARAMETER:
                parameter['default'] = setup
    return descriptor


def install(origin, generator, target=None, setup=None):
    # copy the plugin directory origin into target/hsm-ros2 (the user plugin folder of
    # the editor by default), replacing an earlier copy; return the copy
    if not os.path.isfile(os.path.join(origin, DESCRIPTOR)):
        raise PluginError('the editor plugin is not found in {}'.format(origin))
    folder = os.path.join(target or user_folder(), PLUGIN_ID)
    if os.path.abspath(folder) == os.path.abspath(origin):
        raise PluginError('{} is the plugin itself'.format(folder))
    if os.path.lexists(folder) and not _ours(folder):
        raise PluginError('{} exists and is not the plugin {}'.format(folder, PLUGIN_ID))
    try:
        with open(os.path.join(origin, DESCRIPTOR), encoding='utf-8') as file:
            descriptor = pinned(json.load(file), generator, setup or ros_setup())
        if os.path.lexists(folder):
            shutil.rmtree(folder)
        shutil.copytree(origin, folder)
        with open(os.path.join(folder, DESCRIPTOR), 'w', encoding='utf-8') as file:
            json.dump(descriptor, file, ensure_ascii=False, indent=2)
            file.write('\n')
    except (OSError, ValueError) as error:
        raise PluginError(str(error)) from error
    return folder
