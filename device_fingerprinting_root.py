import time
import pytest
import allure
from lib_testbed.generic.util.logger import log
from lib.util.base_case import BaseCase
from lib.util.base_case import skip_if_pods_have_no_mgmt


@pytest.mark.opensync_switch()
@pytest.mark.opensync_cloud()
@pytest.mark.opensync_pods(name="all", mgmt="optional")
@pytest.mark.tag_finger
@pytest.mark.tag_client_connectivity
@pytest.mark.incremental
class DeviceFingerprintingRoot(BaseCase):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(DeviceFingerprintingRoot, cls):
            cls.gw_name = cls.tb_config["Nodes"][0]["name"]

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(DeviceFingerprintingRoot, cls):
            try:
                cls.cloud.user.restore_location()
            except Exception as e:
                # In case of setup_class failure cloud objects might be not created
                log.error(repr(e))

    @allure.title("Recreate test location")
    def test_01_recreate_test_location(self):
        log.info("Recreating location")
        self.cloud.user.recreate_location()
        self.cloud.admin.disable_autooptimization()
        log.info("Waiting for connect pods to cloud")
        assert self.cloud.admin.check_pods_connected(), "Pods are not connected to cloud"
        # Disabling target matrix in recreate_location() gets ignored if pod
        # claimed to fresh location onboards with firmware < minimum version.
        # Clearing it again after pod gets online seems to "stick" for now.
        self.cloud.admin.clear_target_matrix()

    @skip_if_pods_have_no_mgmt
    @allure.title("Check sanity after recreated location")
    def test_02_check_sanity(self):
        log.info("Checking sanity after recreated location")
        assert not self.pods.all.poll_pods_sanity(), "Sanity is still failing"
        log.info("Sanity succeeded on all pods.")

    def check_client_in_noc(self, client_ip):
        log.info("Check the client name from cloud and verify with the client on NOC")
        timeout = time.time() + 1 * 60
        client_details = None
        while time.time() < timeout:
            client_details = self.cloud.user.get_clients_details(self.client_mac)
            if (
                client_details
                and client_details["ip"]
                and client_details.get("conn_state") == "connected"
                and client_details.get("device_type", "") != "unknown"
                and client_details.get("name") != self.client_mac
            ):
                break
            elif client_details and (
                not client_details["ip"]
                or client_details.get("conn_state") == "disconnected"
                or not client_details.get("device_type")
                or not client_details.get("name")
            ):
                log.warning("Got client information, but without all details")
                time.sleep(5)
            else:
                log.warning("Cannot get device details. Waiting")
                time.sleep(5)
        assert client_details, f"Can not get client details from cloud for {self.client_mac};{self.client_hostname}"
        client_name = client_details.get("name")
        client_noc_ip = client_details.get("ip")
        client_type = client_details.get("device_type")
        client_state = client_details.get("conn_state")
        log.debug(f"Client details: {client_details}")
        log.info(f"Current active device is {client_name}")

        assert client_state == "connected", (
            f"Client {self.client_hostname} is currently disconnected." f" Information from cloud:\n{client_details}"
        )
        log.info(f"Client {self.client_hostname} is currently connected!")

        assert client_name and client_name != self.client_hostname and client_name != self.client_mac, (
            f"Expected " f"client {self.client_hostname} not found on NOC. Information from cloud:\n{client_details}"
        )
        log.info(f"Expected client {client_name} found on NOC!")

        log.info("Check the client ip from cloud and verify with the client on NOC")
        assert client_noc_ip and client_ip == client_noc_ip, (
            f"Expected client ip {client_ip} not found on NOC," f" Information from cloud:\n{client_details}"
        )
        log.info(f"Expected client ip {client_noc_ip} found on NOC")

        # Check the client device type section is visible in NOC
        # device type on NOC
        assert client_type, "Client device-type not found on NOC"
        log.info(f"Client device-type {client_type} found on NOC")

    @staticmethod
    def wait_eth_connection_ready(dev_obj):
        if dev_obj.get_nickname():
            dev_obj.wait_eth_connection_ready()
        else:
            time.sleep(60)
