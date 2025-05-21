# Copyright 2025 Ubuntu
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import unittest

from ops import testing

from charm import MicroovnCharmCharm


def test_start():
    # Arrange:
    ctx = testing.Context(MicroovnCharmCharm)
    # Act:
    state_out = ctx.run(ctx.on.start(), testing.State())
    # Assert:
    assert state_out.unit_status == testing.ActiveStatus()
