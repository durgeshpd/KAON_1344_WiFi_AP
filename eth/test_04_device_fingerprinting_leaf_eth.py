import pytest
import allure
import time
from tests.client_connectivity.device_fingerprinting_root import (
    DeviceFingerprintingRoot,
)
from lib.util.testrail.plugin import pytestrail
from lib_testbed.generic.util.logger import log


@pytest.mark.opensync_client(eth=True, name="eth", vlan=".*")
class DeviceFingerprintingEthLeafRoot(DeviceFingerprintingRoot):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(DeviceFingerprintingEthLeafRoot, cls):
            cls.all_pods = [device["name"] for device in cls.tb_config["Nodes"] if device.get("switch")]
            log.info(f"Recovery switch configuration on all used devices: {cls.all_pods}")
            cls.switch.api.recovery_switch_configuration(cls.all_pods)
            cls.leaf_name, cls.leaf_serial = cls.get_leaf_to_test()
            cls.client_hostname = cls.client.eth.run("hostname")
            cls.client_iface = cls.client.eth.get_eth_iface()
            cls.client_mac = cls.client.eth.get_mac(cls.client_iface)

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(DeviceFingerprintingEthLeafRoot, cls):
            if hasattr(cls.client, "eth"):
                cls.client.eth.run("sudo killall ping", skip_exception=True)
                log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
                cls.switch.api.recovery_switch_configuration(cls.all_pods, set_default_wan=True)

    @classmethod
    def get_leaf_to_test(cls):
        gw_name = cls.tb_config["Nodes"][0]["name"]
        leaf_id = None
        leaf_name = None
        for device in cls.tb_config["Nodes"]:
            if device["name"] == gw_name:
                continue
            if device.get("static_eth_client"):
                continue
            leaf_name = device["name"]
            leaf_id = device["id"]
            break
        return leaf_name, leaf_id

    @allure.title("Connect eth client")
    def test_03_connect_eth_client(self):
        log.info("Check loop status before connect eth client to node")
        self.wait_eth_connection_ready(self.pod.leaf)
        client_cfg_name = self.client.eth.get_nickname()
        log.info(f"Connect {client_cfg_name} client to {self.leaf_name} device")
        self.switch.api.connect_eth_client(self.leaf_name, client_cfg_name)
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

    @allure.title("Check client connectivity after reboot leaf")
    def test_05_check_client_connectivity_after_reboot_leaf(self):
        log.info(f"Rebooting the leaf pod {self.leaf_name}")
        self.cloud.user.reboot_pod(self.leaf_serial)
        assert self.cloud.user.check_pods_connected(
            timeout=180, minpods=1, option="disconnected"
        ), "Gateway has not been disconnected from cloud after reboot"
        log.info("Waiting for all pods to connect back.")
        assert self.cloud.admin.check_pods_connected(), "Pods are not connected to cloud"
        # TODO: PLAT-1046
        time.sleep(120)
        log.info("Check loop status before checking client eth connectivity")
        self.wait_eth_connection_ready(self.pod.leaf)
        self.client.eth.refresh_ip_address(timeout=20)
        self.client.eth.ping_check()

        client_ip = self.client.eth.run(
            f'ip -4 add show dev {self.client_iface} | grep "inet "',
            skip_exception=True,
        )
        assert client_ip, f"Can not get ip address for {self.client_hostname}, {self.client_iface}"
        log.info(client_ip)
        client_ip = client_ip[client_ip.rfind("inet") + 5 : client_ip.rfind("/")]
        self.check_client_in_noc(client_ip)


@pytest.mark.opensync_pod(role="leaf", switch=".*", mgmt="optional")
@pytest.mark.wan(port="primary")
@pytest.mark.network_mode(target="bridge")
@pytest.mark.tag_frv
@pytest.mark.tag_crv
@pytest.mark.duration(seconds=708)
@pytest.mark.TC_ConnectivityEth_10005
@pytestrail.case("C231040", "C396900", "C571857", "C566149")
@allure.title("Device fingerprinting leaf bridge eth0")
class Test04DeviceFingerprintingLeafEth0Bridge(DeviceFingerprintingEthLeafRoot):
    pass
