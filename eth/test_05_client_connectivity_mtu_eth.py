import pytest
import allure
from lib_testbed.generic.util.logger import log
from lib.util.testrail.plugin import pytestrail
from lib.util.base_case import BaseCase


@pytest.mark.opensync_cloud()
@pytest.mark.opensync_client(name="host", nickname="host")
@pytest.mark.tag_mtu
@pytest.mark.incremental
@pytest.mark.tag_frv
@pytest.mark.opensync_client(name="test_client", eth=True)
class ClientConnectivityMtuEth(BaseCase):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(ClientConnectivityMtuEth, cls):
            cls.test_server = cls.tb_config["wifi_check"]["ipaddr"]

    @allure.title("Check eth client connectivity")
    def test_01_prepare_test_client(self):
        self.prepare_test_client()

    @allure.title("Check ping to test server")
    def test_02_check_ping_to_test_server(self):
        log.info(f"Checking client ping to {self.test_server}")
        cmd = f"sudo /bin/ping -c 5 -w 60 -s 1472 -M do {self.test_server}"
        ping_result = self.client.test_client.run_raw(cmd, skip_exception=True)
        log.debug(ping_result)
        assert not ping_result[0], f"Can not ping {self.test_server}. Ping result:\n{ping_result}"
        log.info(f"Ping results:\n{ping_result[1]}")

    def prepare_test_client(self):
        log.info("Refresh ip address on eth client")
        self.client.test_client.refresh_ip_address(timeout=20)
        log.info("Check client internet access")
        assert self.client.test_client.ping_check(), "Ethernet client has not internet access"
        log.info("Client has internet access")


@pytest.mark.network_mode(target="bridge")
@pytest.mark.duration(seconds=11)
@pytest.mark.TC_ConnectivityEth_10006
@pytest.mark.tag_res_gw_frv
@pytestrail.case("C270225", "C396901", "C571864", "C565959")
@allure.title("Client connectivity mtu eth Bridge")
class Test05ClientConnectivityMtuEthBridge(ClientConnectivityMtuEth):
    pass


@pytest.mark.network_mode(target="router")
@pytest.mark.duration(seconds=9)
@pytestrail.case("C270223", "C396942", "C571863", "C565958")
@allure.title("Client connectivity mtu eth Router")
class Test05ClientConnectivityMtuEthRouter(ClientConnectivityMtuEth):
    pass
