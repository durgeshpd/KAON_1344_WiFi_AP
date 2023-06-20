import pytest
import allure

from lib.util.base_case import BaseCase
from lib_testbed.generic.util.logger import log
from lib.util.testrail.plugin import pytestrail
from tests.client_connectivity.eth.wired_connection_root import (
    connect_eth_client_to_pod,
)


@pytest.mark.opensync_switch()
@pytest.mark.opensync_cloud()
@pytest.mark.opensync_pod(role="gw")
@pytest.mark.opensync_pod(role="leaf", name="leaf1", switch=".*")
@pytest.mark.opensync_pod(role="leaf", name="leaf2", static_eth_client=".*")
@pytest.mark.opensync_client(eth=True, name="eth3", vlan=".*")
@pytest.mark.opensync_client(eth=True, name="eth2", vlan=".*")
@pytest.mark.opensync_client(eth=True, name="eth_static")
@pytest.mark.tag_eth
@pytest.mark.tag_client_connectivity
@pytest.mark.incremental
class DisableEthernetLANRoot(BaseCase):
    pod_names = ()

    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(__class__, cls):
            cls.pod_names = [
                cls.pod.gw.get_nickname(),
                cls.pod.leaf1.get_nickname(),
                cls.pod.leaf2.get_nickname(),
            ]
            cls.client_ips = {}
            # Support single Ethernet port devices
            gw_ports = cls.switch.api.get_all_switch_aliases(cls.pod.gw.get_nickname())
            if len(gw_ports) > 1:
                cls.pod1 = cls.pod.gw
                cls.pod2 = cls.pod.leaf1
                cls.client1 = cls.client.eth2
                cls.client2 = cls.client.eth3
                cls.second_client_static = False
            else:
                cls.pod1 = cls.pod.leaf1
                cls.pod2 = cls.pod.leaf2
                cls.client1 = cls.client.eth2
                cls.client2 = cls.client.eth_static
                cls.second_client_static = True
            cls.reset_config()

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(__class__, cls):
            cls.reset_config()

    @classmethod
    def reset_config(cls):
        cls.enable_ethernet_lan()
        log.info(f"Recovering default switch configuration for used pods: {cls.pod_names}")
        cls.switch.api.recovery_switch_configuration(cls.pod_names)

    @classmethod
    def enable_ethernet_lan(cls):
        log.info("Enabling Ethernet LAN")
        cls.cloud.user.set_ethernet_lan_mode("enable")

    @classmethod
    def disable_ethernet_lan(cls):
        log.info("Disabling Ethernet LAN")
        cls.cloud.user.set_ethernet_lan_mode("disable")

    def check_internet(self, client):
        client_name = client.get_nickname()
        log.info(f"Checking if {client_name} has internet access")
        result = client.ping_check()
        verb = "has" if result else "doesn't have"
        log.info(f"Client {client_name} {verb} internet access")
        return result

    def ping_between_clients(self, source, target, fallback_target_ip):
        source_name = source.get_nickname()
        target_name = target.get_nickname()
        target_ip = target.get_eth_info()["eth"].popitem()[1].get("ip", fallback_target_ip)
        log.info(f"Pinging {target_name} client from {source_name} client ...")
        result = source.ping_check(ipaddr=target_ip, fqdn_check=False)
        outcome = "succeeded" if result else "failed"
        log.info(f"Pinging {target_name} client from {source_name} client {outcome}")
        return result

    def check_internet_accessible(self):
        for client in (self.client1, self.client2):
            assert self.check_internet(client), f"{client.get_nickname()} client has no internet access"

    def check_internet_inaccessible(self):
        for client in (self.client1, self.client2):
            assert not self.check_internet(client), f"{client.get_nickname()} client has internet access"

    def check_clients_accessible(self):
        assert self.ping_between_clients(self.client1, self.client2, self.client_ips["client2"])
        assert self.ping_between_clients(self.client2, self.client1, self.client_ips["client1"])

    def check_clients_inaccessible(self):
        assert not self.ping_between_clients(self.client1, self.client2, self.client_ips["client2"])
        assert not self.ping_between_clients(self.client2, self.client1, self.client_ips["client1"])

    @allure.title("Connect first eth client to gateway or one of the leaf pods")
    def test_01_connect_first_client(self):
        connect_eth_client_to_pod(self.switch.api, self.client1, self.pod1)
        self.client_ips["client1"] = self.client1.get_eth_info()["eth"].popitem()[1]["ip"]

    @allure.title("Connect second eth client to the leaf pod")
    def test_02_connect_second_client(self):
        if self.second_client_static:
            log.info(f"Refreshing ip address on {self.client2.get_nickname()} client")
            self.client2.refresh_ip_address(timeout=20)
        else:
            connect_eth_client_to_pod(self.switch.api, self.client2, self.pod2)
        self.client_ips["client2"] = self.client2.get_eth_info()["eth"].popitem()[1]["ip"]

    @allure.title("Check internet is accessible on both eth clients")
    def test_03_check_internet_connectivity(self):
        self.check_internet_accessible()

    @allure.title("Check eth clients can connect to each other")
    def test_04_check_connectivity_between_clients(self):
        self.check_clients_accessible()

    @allure.title("Disable Ethernet LAN")
    def test_05_disable_ethernet_lan(self):
        self.disable_ethernet_lan()

    @allure.title("Check internet is inaccessible on both eth clients")
    def test_06_check_internet_connectivity(self):
        self.check_internet_inaccessible()

    @allure.title("Check eth clients cannot connect to each other")
    def test_07_check_connectivity_between_clients(self):
        self.check_clients_inaccessible()

    @allure.title("Enable Ethernet LAN")
    def test_08_enable_ethernet_lan(self):
        self.enable_ethernet_lan()
        for client in (self.client1, self.client2):
            log.info(f"Refreshing ip address on {client.get_nickname()} client")
            client.refresh_ip_address(timeout=20)

    @allure.title("Check internet is accessible on both eth clients")
    def test_09_check_internet_connectivity(self):
        self.check_internet_accessible()

    @allure.title("Check eth clients can connect to each other")
    def test_10_check_connectivity_between_clients(self):
        self.check_clients_accessible()


@pytest.mark.network_mode(target="bridge")
@pytestrail.case("C1505316")
@allure.title("Disable Ethernet LAN - Bridge Mode")
class Test19DisableEthernetLANBridge(DisableEthernetLANRoot):
    pass


@pytest.mark.network_mode(target="router")
@pytestrail.case("C1505317")
@allure.title("Disable Ethernet LAN - Router Mode")
class Test19DisableEthernetLANRouter(DisableEthernetLANRoot):
    pass
