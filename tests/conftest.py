"""Fixtures for the BenQ Projector tests."""

import sys

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request):
    """Enable custom integrations when running inside the Home Assistant test harness."""
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")
    yield


if sys.platform == "win32":
    # Home Assistant only supports Linux. To run these tests on a Windows workstation the
    # Proactor event loop needs a loopback socketpair, which the harness would block. The
    # tests only talk to a fake projector on 127.0.0.1.
    try:
        import pytest_socket
    except ImportError:
        pass
    else:
        pytest_socket.disable_socket = lambda *args, **kwargs: None
