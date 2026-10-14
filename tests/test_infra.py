import pytest

from askoz.cli import doctor


@pytest.mark.integration
def test_services_reachable() -> None:
    assert doctor() == 0
