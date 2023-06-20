import allure
import pytest
from lib.util.testrail.plugin import pytestrail
from tests.client_connectivity.eth.test_08_switching_network_mode_eth_client import (
    SwitchingNetworkModeClientRoot,
)


@pytest.mark.tag_wan_eth1
@pytest.mark.wan(port="secondary")
@pytest.mark.network_mode(target="router")
@pytest.mark.duration(seconds=1546)
@pytestrail.case("C270132", "C396945", "C566038")
@allure.title("Switching network mode with eth client router secondary wan port")
class Test08SwitchingNetworkModeClientRouterSecondaryWan(SwitchingNetworkModeClientRoot):
    pass
