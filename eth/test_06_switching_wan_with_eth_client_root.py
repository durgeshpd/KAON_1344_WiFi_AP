import pytest
import allure
from lib.util.base_case import BaseCase
from lib_testbed.generic.util.logger import log
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_switch()
@pytest.mark.opensync_cloud()
@pytest.mark.opensync_pod(role="gw", switch=".*")
@pytest.mark.opensync_pods(name="all")
@pytest.mark.opensync_client(eth=True, name="eth", vlan=".*")
@pytest.mark.tag_eth
@pytest.mark.tag_frv
@pytest.mark.tag_client_connectivity
@pytest.mark.tag_wired_clients
@pytest.mark.incremental
class SwitchingWanWithEthClientRoot(BaseCase):
    @classmethod
    def setup_class(cls):
        cls.attempts = 3
        with cls.SafeSetup(SwitchingWanWithEthClientRoot, cls):
            cls.all_pods = cls.pods.all.get_nicknames()
            cls.gw_name = cls.pod.gw.get_nickname()
            cls.eth_name = cls.client.eth.get_nickname()
            cls.eth_iface = cls.client.eth.get_eth_iface()
            log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
            cls.switch.api.recovery_switch_configuration(cls.all_pods)

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(SwitchingWanWithEthClientRoot, cls):
            if hasattr(cls.client, "eth"):
                log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
                cls.switch.api.recovery_switch_configuration(cls.all_pods)

    @allure.title("Connect eth client to gateway")
    def test_01_connect_eth_to_gw(self):
        log.info("Check loop status before connect eth client to node")
        self.pod.gw.wait_eth_connection_ready()
        log.info(f"Connect {self.eth_name} client to {self.gw_name} device")
        self.switch.api.connect_eth_client(self.gw_name, self.eth_name)
        self.check_ping_on_client()

    @allure.title("Reboot gateway device")
    def test_02_reboot_gateway_device(self):
        log.info(f"Rebooting gateway {self.gw_name}")
        self.pod.gw.reboot()
        log.info("Wait for disconnect location from cloud")
        assert self.cloud.admin.check_pods_connected(option="disconnected"), "Location" "is still connected to cloud"
        self.wait_pods_ready()
        log.info("Check loop status before checking eth client connectivity")
        self.pod.gw.wait_eth_connection_ready()
        self.check_ping_on_client()

    @allure.title("Switch wan and client a few times")
    def test_03_switch_wan_and_client(self):
        log.info(f"Switch wan and client {self.attempts} times")
        for i in range(0, self.attempts):
            log.info("")
            log.info(f"Switching between wan port and client port. Attempt: {i + 1}")
            self.switch.api.disconnect_eth_client(self.gw_name, self.eth_name)
            log.info("Switch wan port")
            self.switch.api.switch_wan_port(self.gw_name)
            log.info("Check loop status before connect eth client to node")
            self.pod.gw.wait_eth_connection_ready()
            log.info("Connect eth client to gateway")
            self.switch.api.connect_eth_client(self.gw_name, self.eth_name)
            self.wait_pods_ready()
            self.check_ping_on_client()

    @allure.title("Reconnect wan and client eth")
    def test_04_reconnect_wan_port_and_client(self):
        log.info(f"Reconnect wan port and eth client {self.attempts} times")
        for i in range(0, self.attempts):
            log.info("")
            log.info(f"Reconnect wan port and client eth. Attempt: {i + 1}")
            wan_port = self.switch.api.get_wan_port(self.gw_name)
            self.switch.api.disconnect_eth_client(self.gw_name, self.eth_name)
            self.switch.api.disable_port(wan_port)
            log.info("Wait for disconnect location from cloud")
            assert self.cloud.admin.check_pods_connected(option="disconnected"), "Location is still connected to cloud"
            log.info(f"Enabling wan port on {self.gw_name}")
            self.switch.api.enable_port(wan_port)
            log.info("Check loop status before connect eth client to node")
            self.pod.gw.wait_eth_connection_ready()
            log.info("Connect eth client to gateway")
            self.switch.api.connect_eth_client(self.gw_name, self.eth_name)
            self.wait_pods_ready()
            self.check_ping_on_client()

    def wait_pods_ready(self):
        log.info("Waiting for pods to be ready")
        assert self.cloud.admin.check_pods_connected(), "Location is still disconnected from cloud"
        log.info("Check sanity on connected pods")
        assert not self.pods.all.poll_pods_sanity(), "Sanity is still failing"
        log.info("Sanity has been finished successfully")

    def check_ping_on_client(self):
        log.info("Refresh ip address on eth client")
        self.client.eth.refresh_ip_address(timeout=20)
        log.info(f"Check client internet access on {self.eth_name}")
        assert self.client.eth.ping_check(), "Ethernet client has not internet access"
        log.info("Client has internet access")


@pytest.mark.network_mode(target="router")
@pytest.mark.duration(seconds=1538)
@pytestrail.case("C270136", "C566043", "C594562")
@allure.title("Switching wan port with eth client router")
class Test06SwitchingWanWithEthClientRouter(SwitchingWanWithEthClientRoot):
    pass


@pytest.mark.network_mode(target="bridge")
@pytest.mark.duration(seconds=1538)
@pytestrail.case("C270135", "C566042", "C298357")
@allure.title("Switching wan port with eth client bridge")
class Test06SwitchingWanWithEthClientBridge(SwitchingWanWithEthClientRoot):
    pass
