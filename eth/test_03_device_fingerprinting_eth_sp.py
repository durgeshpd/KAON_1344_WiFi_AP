import pytest
import allure
import time
from tests.client_connectivity.device_fingerprinting_root import (
    DeviceFingerprintingRoot,
)
from lib.util.testrail.plugin import pytestrail
from lib_testbed.generic.util.logger import log


@pytest.mark.opensync_client(eth=True, name="eth", vlan=".*")
class DeviceFingerprintingEthRoot(DeviceFingerprintingRoot):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(DeviceFingerprintingEthRoot, cls):
            cls.all_pods = [device["name"] for device in cls.tb_config["Nodes"] if device.get("switch")]
            log.info(f"Recovery switch configuration on all used devices: {cls.all_pods}")
            cls.switch.api.recovery_switch_configuration(cls.all_pods)
            cls.gw_serial = cls.tb_config["Nodes"][0]["id"]
            cls.client_hostname = cls.client.eth.run("hostname")
            cls.client_iface = cls.client.eth.get_eth_iface()
            cls.client_mac = cls.client.eth.get_mac(cls.client_iface)

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(DeviceFingerprintingEthRoot, cls):
            if hasattr(cls.client, "eth"):
                cls.client.eth.run("sudo killall ping", skip_exception=True)
                log.info(f"Recovery switch configuration on all used devices: {cls.all_pods}")
                cls.switch.api.recovery_switch_configuration(cls.all_pods, set_default_wan=True)

    @allure.title("Connect eth client")
    def test_03_connect_eth_client(self):
        client_cfg_name = self.client.eth.get_nickname()
        log.info("Check loop status before connect eth client to node")
        self.wait_eth_connection_ready(dev_obj=self.pod.gw)
        log.info(f"Connect {client_cfg_name} client to {self.gw_name} device")
        self.switch.api.connect_eth_client(self.gw_name, client_cfg_name)
        log.info("Refresh ip address on eth client")
        self.client.eth.refresh_ip_address(timeout=20)
        self.client.eth.ping_check()

        client_ip = self.client.eth.run(
            f'ip -4 add show dev {self.client_iface} | grep "inet "',
            skip_exception=True,
        )
        assert client_ip, f"Can not get ip address for {self.client_hostname}, {self.client_iface}"

        log.info(f"Check client internet access on {self.client_mac} {client_cfg_name}")
        assert self.client.eth.ping_check(), "Ethernet client has not internet access"
        log.info("Client has internet access")
        # Run ping constantly to be sure, that cloud see client as connected
        ip_address = (
            self.tb_config["wifi_check"]["ip_check"] if self.tb_config["wifi_check"].get("ip_check") else "8.8.8.8"
        )
        self.client.eth.run(f"ping {ip_address} &> /dev/null &")

    @allure.title("Check client details in NOC")
    def test_04_check_client_details_in_noc(self):
        client_ip = self.client.eth.run(f'ip -4 add show dev {self.client_iface} | grep "inet "')
        client_ip = client_ip[client_ip.rfind("inet") + 5 : client_ip.rfind("/")]
        self.check_client_in_noc(client_ip)

    @allure.title("Check client connectivity after reboot gateway")
    def test_05_check_client_connectivity_after_reboot_gw(self):
        log.info(f"Rebooting the gateway pod {self.gw_name}")
        self.cloud.user.reboot_pod(self.gw_serial)
        assert self.cloud.user.check_pods_connected(
            timeout=180, minpods=1, option="disconnected"
        ), "Gateway has not been disconnected from cloud after reboot"
        log.info("Waiting for all pods to connect back.")
        assert self.cloud.admin.check_pods_connected(), "Pods are not connected to cloud"
        # TODO: PLAT-1046
        time.sleep(120)
        log.info("Check loop status before connect eth client to node")
        self.wait_eth_connection_ready(dev_obj=self.pod.gw)
        self.client.eth.refresh_ip_address(timeout=20)
        self.client.eth.ping_check()

        client_ip = self.client.eth.run(f'ip -4 add show dev {self.client_iface} | grep "inet "')
        assert client_ip, f"Can not get ip address from {self.client_hostname} client"
        client_ip = client_ip[client_ip.rfind("inet") + 5 : client_ip.rfind("/")]
        self.check_client_in_noc(client_ip)


@pytest.mark.opensync_pod(role="gw", switch=".*", mgmt="optional")
@pytest.mark.wan(port="primary")
@pytest.mark.network_mode(target="bridge")
@pytest.mark.tag_res_gw_crv
@pytest.mark.tag_crv
@pytest.mark.tag_frv
@pytest.mark.duration(seconds=800)
@pytest.mark.TC_ConnectivityEth_10004
@pytestrail.case("C231034", "C396865", "C270123", "C571851", "C566046", "C566143")
@allure.title("Device fingerprinting eth eth0 bridge SuperPod")
class Test03DeviceFingerprintingEthEth0BridgeSuperPod(DeviceFingerprintingEthRoot):
    pass


@pytest.mark.opensync_pod(role="gw", switch=".*", mgmt="optional")
@pytest.mark.network_mode(target="router")
@pytest.mark.TC_ConnectivityEth_10007
@allure.title("Device fingerprinting eth router")
class Test03DeviceFingerprintingEthRouter(DeviceFingerprintingEthRoot):
    pass
