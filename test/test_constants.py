# -----------------------------------------------------------------------------
# The Cyberiada HSM-to-ROS2 library
#
# The module table the generator and the controller share
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

import pytest

import gencode

pytestmark = pytest.mark.unit

constants = gencode._library_constants
with_dependencies = gencode.hsm_modules_with_dependencies


def test_navigation_implies_wheels():
    assert with_dependencies(['Navigation']) == ['Navigation', 'Wheels']


def test_the_declared_order_is_kept():
    assert with_dependencies(['Debug', 'Navigation']) == ['Debug', 'Navigation', 'Wheels']


def test_an_implied_module_is_not_added_twice():
    assert with_dependencies(['Navigation', 'Wheels']) == ['Navigation', 'Wheels']
    assert with_dependencies(['Wheels', 'Navigation']) == ['Wheels', 'Navigation']


def test_a_module_without_dependencies_is_left_alone():
    assert with_dependencies(['Debug']) == ['Debug']
    assert with_dependencies([]) == []


def test_every_module_has_an_event_table():
    modules = (constants.HSM_DEBUG, constants.HSM_NAVIGATION, constants.HSM_PUMP,
               constants.HSM_STORAGE, constants.HSM_TIMER, constants.HSM_WHEELS)
    for module in modules:
        assert module in gencode.HSM_EVENTS, '{} has no event table'.format(module)


def test_the_event_codes_are_unique_within_a_module():
    for module, events in gencode.HSM_EVENTS.items():
        assert len(set(events.values())) == len(events), \
            'the events of {} are not unique'.format(module)


def test_the_generator_knows_the_tick_events():
    timer_events = gencode.HSM_EVENTS[constants.HSM_TIMER].values()
    for event in (gencode.HSM_TICK_EVENT, gencode.HSM_TICK_1S_EVENT, gencode.HSM_TICK_1M_EVENT):
        assert event in timer_events
