import pytest
import allure
from lib.util.testrail.plugin import pytestrail
from tests.client_connectivity.eth.test_01_connect_disconnect_eth_client_with_rename import (
    ConnectDisconnectClientWithRenameRoot,
)


@pytest.mark.wan(port="secondary")
@pytest.mark.network_mode(target="bridge")
@pytest.mark.duration(seconds=357)
@pytest.mark.TC_ConnectivityEth_10002
@pytestrail.case("C231044", "C396838", "C270129", "C571861", "C566153", "C566044")
@allure.title("Connect disconnect client with rename bridge - uplink on secondary port")
@pytest.mark.tag_crv
@pytest.mark.tag_frv
@pytest.mark.tag_wan_eth1
class Test01ConnectDisconnectEth1ClientWithRenameBridge(ConnectDisconnectClientWithRenameRoot):
    pass


@pytest.mark.tag_wan_eth1
@pytest.mark.wan(port="secondary")
@pytest.mark.network_mode(target="router")
@pytest.mark.duration(seconds=515)
@pytestrail.case("C270130", "C566045")
@allure.title("Connect disconnect client with rename router - uplink on secondary port")
class Test01ConnectDisconnectEth1ClientWithRenameRouter(ConnectDisconnectClientWithRenameRoot):
    pass
