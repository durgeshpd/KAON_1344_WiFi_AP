import pytest
import allure
from tests.client_connectivity.eth.test_02_wired_connection import WiredConnectionRoot
from lib.util.testrail.plugin import pytestrail


@pytest.mark.tag_wan_eth1
@pytest.mark.wan(port="secondary")
@pytest.mark.network_mode(target="bridge")
@pytest.mark.duration(seconds=190)
@pytest.mark.TC_ConnectivityEth_10003
@pytest.mark.tag_pytest_acceptance
@pytestrail.case("C231043", "C396839", "C571860", "C566152")
@allure.title("Wired connection bridge secondary wan port")
class Test02WiredConnectionBridge(WiredConnectionRoot):
    pass
