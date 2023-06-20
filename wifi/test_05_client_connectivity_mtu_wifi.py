import pytest
import allure
from lib_testbed.generic.util.logger import log
from lib.util.testrail.plugin import pytestrail
from lib.util.base_case import BaseCase


@pytest.mark.opensync_cloud()
@pytest.mark.opensync_client(name="host", nickname="host")
@pytest.mark.tag_mtu
@pytest.mark.tag_frv
@pytest.mark.incremental
@pytest.mark.opensync_client(name="test_client", wifi=True)
class ClientConnectivityMtuWifi(BaseCase):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(__class__, cls):
            cls.ssid, cls.password = cls.cloud.user.get_home_network_credentials()
            cls.test_server = cls.tb_config["wifi_check"]["ipaddr"]
            cls.bssids = cls.cloud.admin.get_node_home_ap_bssids(cls.tb_config.get("Nodes")[1]["id"])

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(__class__, cls):
            cls.client.test_client.disconnect(cls.cls.client.test_client.ifname, skip_exception=True)

    @allure.title("Connect wifi client")
    def test_01_prepare_test_client(self):
        for bssid in self.bssids:
            self.prepare_test_client(bssid)
            log.info(f"Checking client ping to {self.test_server}")
            cmd = f"sudo /bin/ping -c 5 -w 60 -s 1472 -M do {self.test_server}"
            ping_result = self.client.test_client.run_raw(cmd, skip_exception=True)
            log.debug(ping_result)
            assert not ping_result[0], f"Can not ping {self.test_server}. Ping result:\n{ping_result}"
            log.info(f"Ping results:\n{ping_result[1]}")

    def prepare_test_client(self, bssid):
        self.client.test_client.connect(ssid=self.ssid, psk=self.password, bssid=bssid[1])
        log.info(f"Client connected to ssid: {self.ssid}, band: {bssid[0]}, bssid: {bssid[1]}")
        log.info("Check client internet access")
        assert self.client.test_client.ping_check(), "Client does not have internet access"
        log.info("Client has internet access")


@pytest.mark.network_mode(target="bridge")
@pytest.mark.duration(seconds=35)
@pytest.mark.TC_ConnectivityWifi_10008
@pytest.mark.tag_res_gw_frv
@pytestrail.case("C270226", "C396910", "C571847", "C565954")
@allure.title("Client connectivity mtu wifi Bridge")
class Test05ClientConnectivityMtuWifiBridge(ClientConnectivityMtuWifi):
    pass


@pytest.mark.network_mode(target="router")
@pytest.mark.duration(seconds=34)
@pytest.mark.TC_ConnectivityWifi_10009
@pytestrail.case("C270224", "C396953", "C571846", "C565953")
@allure.title("Client connectivity mtu wifi Router")
class Test05ClientConnectivityMtuWifiRouter(ClientConnectivityMtuWifi):
    pass
