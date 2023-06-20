import allure
import pytest

from lib.util.base_case import BaseCase
from lib.util.testrail.plugin import pytestrail
from lib_testbed.generic.util.logger import log
from lib_testbed.generic.util.common import wait_for


# Cloud is needed for pytest.mark.network_mode
@pytest.mark.opensync_cloud()
@pytest.mark.opensync_client(name="wifi", wifi=True)
@pytest.mark.incremental
@pytest.mark.tag_client_connectivity
class PPTPClientOnWifiClientRoot(BaseCase):
    pptp_server = "192.168.7.218"
    vpned_host = "192.168.218.1"

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(__class__, cls):
            cls.client.wifi.run("sudo poff pptptest", skip_exception=True)
            cls.client.wifi.run("sudo kilall pptp", skip_exception=True)
            cls.client.wifi.disconnect(skip_exception=True)

    @allure.title("Connect wireless client to testbed location")
    def test_01_connect_wifi_client(self):
        assert self.client.wifi.connect(), "wifi client failed to connect to testbed network"
        assert self.client.wifi.ping_check(), "wifi client has no internet access"
        assert self.client.wifi.ping_check(self.pptp_server, fqdn_check=False), "PPTP server is unreachable"
        assert self.client.wifi.run(f"nc -z {self.pptp_server} 1723 && echo 'ok'"), "PPTP server is not listening"
        log.info("wifi client connected to testbed network successfully")

    @allure.title("Check that client cannot reach PPTP VPN")
    def test_02_pptp_vpn_unreachable(self):
        assert not self.client.wifi.ping_check(self.vpned_host, fqdn_check=False), "host behind VPN already reachable"
        assert "ppp" not in self.client.wifi.run("ip --brief link show"), "point-to-point interface already present"
        log.info("PPTP VPN is not yet reachable")

    @allure.title("Connect wireless client to PPTP VPN")
    def test_03_connect_pptp_client(self):
        assert self.client.wifi.run("sudo pon pptptest && echo 'ok'"), "connection to PPTP server failed"
        assert self.pptp_server in self.client.wifi.run("ps aux | grep pptp"), "connection to PPTP server lost"
        assert "ppp" in self.client.wifi.run("ip --brief link show"), "no point-to-point interface on client"
        assert wait_for(self.client_got_pptp_address, timeout=60, tick=3)[1], "client is missing PPTP IP address"
        log.info("PPTP VPN connection established")

    def client_got_pptp_address(self):
        return "192.168.218." in self.client.wifi.run("ip -4 --brief addr show")

    @allure.title("Check that wireless client can reach PPTP VPN")
    def test_04_pptp_vpn_reachable(self):
        assert f"{self.vpned_host} dev ppp" in self.client.wifi.run("ip route show"), "route over PPTP network missing"
        assert self.client.wifi.ping_check(), "wifi client has no internet access"
        assert self.client.wifi.ping_check(self.vpned_host, fqdn_check=False), "host behind PPTP VPN is unreachable"
        log.info("PPTP VPN connection is functional")


@pytest.mark.network_mode(target="bridge")
@pytestrail.case("C2103383", "C2109137")
@allure.title("PPTP VPN - client connection - Bridge")
@pytest.mark.duration(seconds=67)
class Test04PPTPClientOnWifiClientBridge(PPTPClientOnWifiClientRoot):
    pass


@pytest.mark.network_mode(target="router")
@pytestrail.case("C2103309", "C2109136")
@allure.title("PPTP VPN - client connection - Router")
class Test04PPTPClientOnWifiClientRouter(PPTPClientOnWifiClientRoot):
    pass
