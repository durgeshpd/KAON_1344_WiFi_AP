import pytest
import allure
import time
from lib.util.base_case import BaseCase
from lib_testbed.generic.util.logger import log
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_switch()
@pytest.mark.opensync_cloud()
@pytest.mark.opensync_pod(role="leaf", switch=".*", mgmt="optional")
@pytest.mark.opensync_pods(name="all", mgmt="optional")
@pytest.mark.opensync_client(eth=True, name="eth1", vlan=".*")
@pytest.mark.opensync_client(eth=True, name="eth2", vlan=".*")
@pytest.mark.tag_eth
@pytest.mark.tag_frv
@pytest.mark.tag_client_connectivity
@pytest.mark.incremental
class EthClientConnectivityAfterRebootRoot(BaseCase):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(__class__, cls):
            cls.all_pods = [device["name"] for device in cls.tb_config["Nodes"] if device.get("switch")]
            cls.leaf_name, cls.leaf_serial = cls.get_leaf_to_test()
            cls.eth1_name = cls.client.eth1.get_nickname()
            cls.eth1_iface = cls.client.eth1.get_eth_iface()
            cls.eth2_name = cls.client.eth2.get_nickname()
            cls.eth2_iface = cls.client.eth2.get_eth_iface()
            log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
            cls.switch.api.recovery_switch_configuration(cls.all_pods)
            cls.single_pod_rebooted = False

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(__class__, cls):
            if hasattr(cls.client, "eth1") and hasattr(cls.client, "eth2"):
                log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
                cls.switch.api.recovery_switch_configuration(cls.all_pods)

    @allure.title("Connect eth clients to leaf")
    def test_01_connect_eth_clients_to_leaf(self):
        log.info("Check loop status before connect eth client to node")
        self.wait_eth_connection_ready(self.pod.leaf)
        log.info("Connect eth clients to leaf")
        log.info(f"Connect {self.eth1_name} client to {self.leaf_name} device")
        self.switch.api.connect_eth_client(self.leaf_name, self.eth1_name)
        log.info(f"Connect {self.eth2_name} client to {self.leaf_name} device")
        self.switch.api.connect_eth_client(self.leaf_name, self.eth2_name)
        self.check_internet_access_on_clients()

    @allure.title("Reboot device")
    def test_02_reboot_device(self):
        self.reboot_device()
        self.wait_pods_ready()

    @allure.title("Check client connectivity")
    def test_03_check_client_eth_connectivity(self):
        timeout = time.time() + 300
        eth1_dhcp_status = self.client.eth1.refresh_ip_address(timeout=20, skip_exception=True)
        eth2_dhcp_status = self.client.eth2.refresh_ip_address(timeout=20, skip_exception=True)
        while timeout > time.time():
            log.info(f"Check if eth clients: {self.eth1_name} and {self.eth2_name} got IP from {self.leaf_name}")
            if not eth1_dhcp_status:
                log.warn(f"{self.eth1_name} did not get IP address from {self.leaf_name}. Refreshing IP address...")
                eth1_dhcp_status = self.client.eth1.refresh_ip_address(timeout=20, skip_exception=True)

            if not eth2_dhcp_status:
                log.warn(f"{self.eth2_name} did not get IP address from {self.leaf_name}. Refreshing IP address...")
                eth2_dhcp_status = self.client.eth2.refresh_ip_address(timeout=20, skip_exception=True)

            if eth1_dhcp_status and eth2_dhcp_status:
                log.info(f"All clients got IP address from {self.leaf_name}")
                break
            log.info("Wait 5 seconds and try again")
            time.sleep(5)

        assert eth1_dhcp_status and eth2_dhcp_status, f"" f"Eth Clients did not get IP address from {self.leaf_name}"

        assert self.client.eth1.ping_check(), f"{self.eth1_name} has no internet access"
        assert self.client.eth2.ping_check(), f"{self.eth2_name} has no internet access"

    def wait_pods_ready(self):
        log.info("Waiting for disconnect pods from cloud")
        minpods = 1 if self.single_pod_rebooted else 2
        assert self.cloud.user.check_pods_disconnected(
            minpods=minpods
        ), "Pods have not been disconnected from cloud after recreate location"
        log.info("Waiting for pods to be ready")
        assert self.cloud.user.check_pods_connected(), "Location is still disconnected from cloud"
        if "" not in self.pods.all.get_nicknames():
            log.info("Check sanity on connected pods")
            assert not self.pods.all.poll_pods_sanity(), "Sanity is still failing"
            log.info("Sanity has been finished successfully")
        log.info("Wait for disable loop status")
        self.wait_eth_connection_ready(self.pod.leaf)

    def check_internet_access_on_clients(self):
        log.info("Refresh ip address on eth clients")
        self.client.eth1.refresh_ip_address(timeout=20)
        self.client.eth2.refresh_ip_address(timeout=20)

        log.info(f"Check client internet access on {self.eth1_name}")
        assert self.client.eth1.ping_check(), f"Ethernet client: {self.eth1_name} has not internet access"
        log.info(f"Client: {self.eth1_name} has internet access")

        log.info(f"Check client internet access on {self.eth2_name}")
        assert self.client.eth2.ping_check(), f"Ethernet client: {self.eth2_name} has not internet access"
        log.info(f"Client: {self.eth2_name} has internet access")

    @classmethod
    def get_leaf_to_test(cls):
        leaf_id = None
        leaf_name = None
        for i, device in enumerate(cls.tb_config["Nodes"]):
            device_name, device_id = device["name"], device["id"]
            switch_aliases_count = len(cls.switch.api.get_all_switch_aliases(device_name))
            # skip gw node
            if i == 0 or device.get("static_eth_client"):
                continue
            if switch_aliases_count <= 1:
                continue
            leaf_name = device_name
            leaf_id = device_id
            break
        assert leaf_id and leaf_name, (
            "Not found a properly leaf device for this test. " "Required leaf device with at least two eth ports"
        )
        return leaf_name, leaf_id

    @staticmethod
    def wait_eth_connection_ready(dev_obj):
        if dev_obj.get_nickname():
            dev_obj.wait_eth_connection_ready()
        else:
            time.sleep(60)


@pytest.mark.network_mode(target="router")
@pytest.mark.duration(seconds=502)
@pytestrail.case("C270125", "C396946", "C566034")
@allure.title("Ethernet client connectivity after location reboot router")
class Test10EthClientConnectivityAfterRebootLocationRouter(EthClientConnectivityAfterRebootRoot):
    def reboot_device(self):
        log.info("Reboot whole location")
        self.cloud.user.reboot()


@pytest.mark.network_mode(target="bridge")
@pytest.mark.duration(seconds=507)
@pytestrail.case("C270126", "C396906", "C566033")
@allure.title("Ethernet client connectivity after location reboot bridge")
class Test10EthClientConnectivityAfterRebootLocationBridge(EthClientConnectivityAfterRebootRoot):
    def reboot_device(self):
        log.info("Reboot whole location")
        self.cloud.user.reboot()


@pytest.mark.duration(seconds=419)
@pytestrail.case("C270127", "C396947", "C566036")
@allure.title("Ethernet client connectivity after leaf reboot")
class Test10EthClientConnectivityAfterLeafReboot(EthClientConnectivityAfterRebootRoot):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(__class__, cls):
            cls.single_pod_rebooted = True

    def reboot_device(self):
        log.info("Reboot leaf device")
        self.cloud.user.reboot_pod(self.leaf_serial)


@pytest.mark.duration(seconds=507)
@pytestrail.case("C270128", "C396948", "C566035")
@allure.title("Ethernet client connectivity after gw reboot")
class Test10EthClientConnectivityAfterGwReboot(EthClientConnectivityAfterRebootRoot):
    def reboot_device(self):
        self.gw_serial = self.tb_config["Nodes"][0]["id"]
        log.info("Reboot gateway device")
        self.cloud.user.reboot_pod(self.gw_serial)
