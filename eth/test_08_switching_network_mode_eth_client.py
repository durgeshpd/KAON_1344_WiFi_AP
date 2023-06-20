import pytest
import allure
import time
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
@pytest.mark.incremental
class SwitchingNetworkModeClientRoot(BaseCase):
    @classmethod
    def setup_class(cls):
        cls.attempts = 3
        with cls.SafeSetup(SwitchingNetworkModeClientRoot, cls):
            cls.all_pods = cls.pods.all.get_nicknames()
            cls.gw_name = cls.pod.gw.get_nickname()
            cls.eth_name = cls.client.eth.get_nickname()
            cls.eth_iface = cls.client.eth.get_eth_iface()
            log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
            cls.switch.api.recovery_switch_configuration(cls.all_pods)

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(SwitchingNetworkModeClientRoot, cls):
            if hasattr(cls.client, "eth"):
                log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
                cls.switch.api.recovery_switch_configuration(cls.all_pods, set_default_wan=True)

    @allure.title("Connect eth client to gateway")
    def test_01_connect_eth_to_gw(self):
        log.info("Check loop status before connect eth client to node")
        self.pod.gw.wait_eth_connection_ready()
        log.info(f"Connect {self.eth_name} client to {self.gw_name} device")
        self.switch.api.connect_eth_client(self.gw_name, self.eth_name)
        log.info("Refresh ip address on eth client")
        self.client.eth.refresh_ip_address(timeout=20)
        log.info(f"Check client internet access on {self.eth_name}")
        assert self.client.eth.ping_check(), "Ethernet client has not internet access"
        log.info("Client has internet access")

    @allure.title("Switch network mode in the loop")
    def test_02_switch_network_mode_loop(self):
        log.info(f"Switch network mode in the loop {self.attempts} times")
        for i in range(0, self.attempts):
            log.info("")
            log.info(f"Switch network mode. Attempt: {i + 1}")
            target_mode = self.get_net_for_change()
            log.info(f"Changing network mode to {target_mode}")
            self.cloud.user.set_network_mode_wait(target_mode)
            self.wait_pods_ready()
            self.wait_for_connect_eth_client()

    def get_net_for_change(self):
        network_mode = self.cloud.user.get_network_mode()
        if network_mode == "bridge":
            network_mode = "router"
        elif network_mode == "router":
            network_mode = "bridge"
        return network_mode

    def wait_pods_ready(self):
        log.info("Waiting for pods to be ready")
        assert self.cloud.user.check_pods_connected(), "Location is still disconnected from cloud"
        log.info("Check sanity on connected pods")
        assert not self.pods.all.poll_pods_sanity(), "Sanity is still failing"
        log.info("Sanity has been finished successfully")
        log.info("Wait for disable loop status")
        self.pod.gw.wait_eth_connection_ready()

    def wait_for_connect_eth_client(self):
        timeout = time.time() + 300
        status = False
        while timeout > time.time():
            log.info(f"Check if eth client {self.eth_name} has internet access")
            self.client.eth.refresh_ip_address(timeout=20, skip_exception=True)
            check_ping = self.client.eth.ping_check()
            if check_ping:
                log.info("Client eth has internet access")
                status = True
                break
            log.info("Wait 5 seconds and try again")
            time.sleep(5)
        assert status, "Ethernet clients have not internet access after expired 300s"


@pytest.mark.wan(port="primary")
@pytest.mark.network_mode(target="bridge")
@pytest.mark.duration(seconds=1523)
@pytestrail.case("C270221", "C396904", "C566039")
@allure.title("Switching network mode with eth client bridge eth0")
class Test08SwitchingNetworkModeClientBridgeEth0(SwitchingNetworkModeClientRoot):
    pass
