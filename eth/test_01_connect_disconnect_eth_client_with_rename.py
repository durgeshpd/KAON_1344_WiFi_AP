import pytest
import allure
import uuid
import time
from requests import RequestException

from lib.util.base_case import BaseCase
from lib_testbed.generic.util.logger import log
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_switch()
@pytest.mark.opensync_cloud()
@pytest.mark.opensync_pod(role="gw", switch=".*")
@pytest.mark.opensync_pods(name="all", switch=".*")
@pytest.mark.opensync_client(eth=True, name="eth", vlan=".*")
@pytest.mark.tag_eth
@pytest.mark.tag_client_connectivity
@pytest.mark.incremental
class ConnectDisconnectClientWithRenameRoot(BaseCase):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(ConnectDisconnectClientWithRenameRoot, cls):
            cls.counter = 4
            cls.old_client_name = None
            cls.all_pods = cls.pods.all.get_nicknames()
            cls.gw_name = cls.pod.gw.get_nickname()
            cls.eth_name = cls.client.eth.get_nickname()
            log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
            cls.switch.api.recovery_switch_configuration(cls.all_pods)
            cls.connect_eth_client()
            cls.device_mac = cls.client.eth.get_mac()
            timeout = time.time() + 1 * 60
            while time.time() < timeout:
                try:
                    cls.old_client_name = cls.cloud.user.get_device_nickname(cls.device_mac)
                    break
                except RequestException:
                    log.warning("Cannot get device details. Waiting")
                    time.sleep(5)
            assert cls.old_client_name, "Unable to get device name from API"

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(ConnectDisconnectClientWithRenameRoot, cls):
            if cls.old_client_name:
                log.info(f"Back to original client name: {cls.old_client_name}")
                cls.cloud.user.rename_device_nickname(cls.device_mac, cls.old_client_name)

            if hasattr(cls.client, "eth"):
                log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
                cls.switch.api.recovery_switch_configuration(cls.all_pods, set_default_wan=True)

    @allure.title("Check client connectivity before rename a client")
    def test_01_check_client_connectivity(self):
        log.info("Check client connectivity before rename a client")
        log.info(f"Check client internet access for {self.device_mac} || {self.eth_name}")
        assert self.client.eth.ping_check(), "Ethernet client has not internet access"
        log.info("Client has internet access")

    @allure.title("Rename eth client name")
    def test_02_rename_eth_client_name(self):
        new_name = str(uuid.uuid4().hex.upper()[0:6])
        log.info(f"Rename eth client name from: {self.old_client_name} to {new_name}")
        self.cloud.user.rename_device_nickname(self.device_mac, new_name)

        log.info("Verify that nickname is change successfully by fetching client info from cloud")
        current_name = self.cloud.user.get_device_nickname(self.device_mac)
        assert current_name == new_name, (
            f"Renaming of eth client is not successful for {self.device_mac},"
            f" Current name: {current_name} Expect: {new_name}"
        )

    @allure.title("Check client connectivity after rename a client")
    def test_03_check_client_connectivity(self):
        log.info("Check client connectivity after rename a client")
        log.info(f"Check client internet access for {self.device_mac} || {self.eth_name}")
        assert self.client.eth.ping_check(), "Ethernet client has not internet access"
        log.info("Client has internet access")

    @allure.title("Reconnect eth client a few times")
    def test_04_reconnect_eth_client_a_few_times(self):
        log.info("Reconnect eth client a few times")
        for i in range(0, self.counter):
            log.console("", show_file=False)
            log.info(f"Unplugging and plugging eth client, attempt:{i + 1}")
            log.info("Disconnect eth client")
            self.switch.api.disconnect_eth_client(self.gw_name, self.eth_name)
            log.info("Connect eth client")
            self.connect_eth_client()
            assert self.client.eth.ping_check(), "Ethernet client has not internet access"
            log.info("Client has internet access")

    @allure.title("Check sanity")
    def test_05_check_sanity(self):
        log.info("Checking sanity")
        assert not self.pods.all.poll_pods_sanity(), "Sanity is still failing"
        log.info("Sanity succeeded on all pods.")

    @classmethod
    def connect_eth_client(cls):
        log.info("Check loop status before connect eth client to node")
        cls.pod.gw.wait_eth_connection_ready()
        log.info(f"Connect {cls.eth_name} client to {cls.gw_name} device")
        cls.switch.api.connect_eth_client(cls.gw_name, cls.eth_name)
        log.info("Refresh ip address on eth client")
        cls.client.eth.refresh_ip_address(timeout=20)


@pytest.mark.wan(port="primary")
@pytest.mark.network_mode(target="bridge")
@pytest.mark.duration(seconds=374)
@pytest.mark.TC_ConnectivityEth_10001
@pytestrail.case("C1346777")
@allure.title("Connect disconnect client with rename bridge - uplink on primary port")
class Test01ConnectDisconnectEth0ClientWithRenameBridge(ConnectDisconnectClientWithRenameRoot):
    pass


@pytest.mark.wan(port="primary")
@pytest.mark.network_mode(target="router")
@pytest.mark.duration(seconds=378)
@pytest.mark.TC_ConnectivityEth_10010
@pytestrail.case("C231045", "C396938", "C571862", "C566154")
@allure.title("Connect disconnect client with rename router - uplink on primary port")
@pytest.mark.tag_crv
@pytest.mark.tag_frv
class Test01ConnectDisconnectEth0ClientWithRenameRouter(ConnectDisconnectClientWithRenameRoot):
    pass
