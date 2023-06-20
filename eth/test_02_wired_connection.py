import pytest
import allure

from lib.util.base_case import BaseCase
from lib_testbed.generic.util.logger import log
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_switch()
@pytest.mark.opensync_cloud()
@pytest.mark.opensync_pod(role="gw", switch=".*")
@pytest.mark.opensync_pod(role="leaf", switch=".*")
@pytest.mark.opensync_pods(name="all", switch=".*")
@pytest.mark.opensync_client(eth=True, name="eth1", vlan=".*")
@pytest.mark.opensync_client(eth=True, name="eth2", vlan=".*")
@pytest.mark.tag_eth
@pytest.mark.tag_crv
@pytest.mark.tag_frv
@pytest.mark.tag_client_connectivity
@pytest.mark.incremental
class WiredConnectionRoot(BaseCase):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(WiredConnectionRoot, cls):
            cls.all_pods = cls.pods.all.get_nicknames()
            cls.gw_name = cls.pod.gw.get_nickname()
            cls.leaf_name = cls.pod.leaf.get_nickname()
            cls.eth1_name = cls.client.eth1.get_nickname()
            cls.eth2_name = cls.client.eth2.get_nickname()
            cls.eth1_iface = cls.client.eth1.get_eth_iface()
            cls.eth2_iface = cls.client.eth2.get_eth_iface()
            log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
            cls.switch.api.recovery_switch_configuration(cls.all_pods)

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(WiredConnectionRoot, cls):
            if hasattr(cls.client, "eth2"):
                log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
                cls.switch.api.recovery_switch_configuration(cls.all_pods, set_default_wan=True)

    @allure.title("Connect eth client to gateway")
    def test_01_connect_eth_to_gw(self):
        log.info("Check loop status before connect eth client to node")
        self.pod.gw.wait_eth_connection_ready()
        log.info(f"Connect {self.eth1_name} client to {self.gw_name} device")
        self.switch.api.connect_eth_client(self.gw_name, self.eth1_name)

        log.info("Refresh ip address on eth client")
        self.client.eth1.refresh_ip_address(timeout=20)

        log.info(f"Check client internet access on {self.eth1_name}")
        assert self.client.eth1.ping_check(), "Ethernet client has not internet access"
        log.info("Client has internet access")

        log.info("Disconnect eth client from gateway")
        self.switch.api.disconnect_eth_client(self.gw_name, self.eth1_name)

    @allure.title("Connect first eth client to leaf eth0")
    def test_02_connect_eth_to_leaf_eth0(self):
        log.info("Check loop status before connect eth client to node")
        self.pod.leaf.wait_eth_connection_ready()
        log.info(f"Connect {self.eth1_name} client to {self.leaf_name} device")
        self.switch.api.connect_eth_client(self.leaf_name, self.eth1_name)

        log.info("Refresh ip address on eth client")
        self.client.eth1.refresh_ip_address(timeout=20)

        log.info(f"Check client internet access on {self.eth1_name}")
        assert self.client.eth1.ping_check(), "Ethernet client has not internet access"
        log.info("Client has internet access")

    @allure.title("Connect second eth client to leaf eth1")
    def test_03_connect_eth_to_leaf_eth1(self):
        log.info("Check loop status before connect eth client to node")
        self.pod.leaf.wait_eth_connection_ready()
        log.info(f"Connect {self.eth2_name} client to {self.leaf_name} device")
        self.switch.api.connect_eth_client(self.leaf_name, self.eth2_name)

        log.info("Refresh ip address on eth client")
        self.client.eth2.refresh_ip_address(timeout=20)

        log.info(f"Check client internet access on {self.eth2_name}")
        assert self.client.eth2.ping_check(), "Ethernet client has not internet access"
        log.info("Client has internet access")

    @allure.title("Check ping between clients")
    def test_04_check_ping_between_client(self):
        eth1_ip = self.client.eth1.run(f'ip -4 add show dev {self.eth1_iface} | grep "inet "')
        eth1_ip = eth1_ip[eth1_ip.rfind("inet") + 5 : eth1_ip.rfind("/")]
        eth2_ip = self.client.eth2.run(f'ip -4 add show dev {self.eth2_iface} | grep "inet "')
        eth2_ip = eth2_ip[eth1_ip.rfind("inet") + 5 : eth2_ip.rfind("/")]

        log.info(f"Check ping from {eth1_ip} to {eth2_ip}")
        ping_res = self.client.eth1.ping(eth2_ip)
        assert "100% packet loss" not in ping_res, f"Ping from {eth1_ip} to {eth2_ip} failed:\n{ping_res}"
        log.info(f"Ping from {eth1_ip} to {eth2_ip} has been finished successfully")

        log.info(f"Check ping from {eth2_ip} to {eth1_ip}")
        ping_res = self.client.eth2.ping(eth1_ip)
        assert "100% packet loss" not in ping_res, f"Ping from {eth2_ip} to {eth1_ip} failed:\n{ping_res}"
        log.info(f"Ping from {eth2_ip} to {eth1_ip} has been finished successfully")


@pytest.mark.wan(port="primary")
@pytest.mark.network_mode(target="router")
@pytest.mark.duration(seconds=199)
@pytest.mark.tag_res_gw_crv
@pytest.mark.TC_ConnectivityEth_10009
@pytestrail.case("C231042", "C396939", "C571859", "C566151")
@allure.title("Wired connection router eth0")
class Test02WiredConnectionRouter(WiredConnectionRoot):
    pass
