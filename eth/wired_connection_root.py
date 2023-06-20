import pprint
import time
import pytest
from lib.util.base_case import BaseCase
from lib_testbed.generic.util.logger import log
from lib.util.common_marks import WanParam


def connect_eth_client_to_pod(switch, client, pod):
    client_name = client.get_nickname()
    pod_name = pod.get_nickname()
    log.info(f"Checking loop status before connecting {client_name} client to {pod_name} device")
    assert pod.wait_eth_connection_ready()
    log.info(f"Connecting {client_name} client to {pod_name} device")
    switch.connect_eth_client(pod_name, client_name)
    log.info(f"Refreshing ip address on {client_name} client")
    client.refresh_ip_address(timeout=20)
    log.info(f"Client {client_name} is connected to {pod_name} device")


@pytest.mark.opensync_switch()
@pytest.mark.opensync_cloud()
@pytest.mark.opensync_client(eth=True, name="eth1", vlan=".*")
@pytest.mark.incremental
@pytest.mark.tag_wired_clients
@pytest.mark.tag_wired_clients_wan
@pytest.mark.parametrize("wan_id", WanParam.wan_parametrization(), scope="session")
class WiredConnectionRoot(BaseCase):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(__class__, cls):
            cls.all_pods = [device["name"] for device in cls.tb_config["Nodes"]]
            log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
            cls.switch.api.recovery_switch_configuration(cls.all_pods)
            cls.eth_iface = cls.client.eth1.get_eth_iface()
            cls.client_mac = cls.client.eth1.get_mac(cls.eth_iface)
            cls.eth_name = cls.client.eth1.get_nickname()
            cls.static_mode = False

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(__class__, cls):
            log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
            cls.switch.api.recovery_switch_configuration(cls.all_pods)

    def connect_eth_client(self, device, dhcp_timeout=20):
        log.info("Check loop status before connect eth client to node")
        device.wait_eth_connection_ready()
        device_name = device.get_nickname()
        self.client.eth1.stop_dhcp_client(self.eth_iface)
        device_id = device.get_serial_number()
        log.info(f"Connect {self.eth_name} client to {device_name} device")
        self.switch.api.connect_eth_client(device_name, self.eth_name)
        start_time = time.time()
        if self.static_mode:
            log.info(f"Reboot {device_name} after connect eth client")
            device.reboot()
            log.info(f"Wait for {device_id} disconnect")
            assert self.cloud.user.check_pods_connected(
                expect_pods=[device_id], option="disconnected"
            ), f"{device_name} no disconnected after reboot"
            log.info("Device is disconnected")
            log.info(f"Wait for connect {device_id} to the cloud")
            assert self.cloud.user.check_pods_connected(
                expect_pods=[device_id], only_controller=True
            ), "Not all devices connected to cloud"
            log.info("Required DUT connected to cloud")
            onboarding_time = time.time() - start_time
            log.info(f"Onboarding time (without home VAPs): {onboarding_time:.2f} seconds")
            # we don't need to check loop protection on the gateway.
            if device.lib.device.config.get("role", "") != "gw":
                st_time = time.time()
                log.info("Check loop status before connect eth client to node")
                device.wait_eth_connection_ready()
                log.info(f"Time spent on putting loop flag down: {time.time() - st_time:.2f}")
        log.info("Refresh ip address on eth client")
        st_time = time.time()
        timeout = st_time + dhcp_timeout
        while time.time() < timeout:
            ret = self.client.eth1.refresh_ip_address(timeout=7, clear_dhcp=False, skip_exception=True)
            if ret:
                log.info(f"DHCP received after: {time.time() - st_time:.2f} sec")
                break
            time.sleep(2)
        else:
            assert False, "Client did not received IP address"
        ip_refresh_time = time.time() - start_time
        log.info(f"Check client internet access on {self.eth_name}")
        assert self.client.eth1.ping_check(), "Ethernet client has not internet access"
        log.info("Client has internet access")
        return ip_refresh_time, start_time

    def verify_client_noc(self, pod=None, present=True):
        timeout = time.time() + 180
        client_info = {}
        state = "connected" if present else "disconnected"
        while timeout > time.time():
            client_info = self.cloud.user.get_clients_details(self.client_mac)
            if client_info.get("conn_state", "") == state:
                if state == "disconnected":
                    break
                else:
                    if client_info.get("ip") is not None:
                        break
            time.sleep(5)
        else:
            log.info(f"Current information about the client:\n{pprint.pformat(client_info)}")
            assert False, "We do not have all info about the client in FTL"
        log.info("Verify connection state")
        assert client_info.get("conn_state") == state, (
            f"Invalid connection state. " f'Expected: "{state}" but got: {client_info.get("conn_state")}'
        )
        if pod:
            assert client_info.get("leaf_to_root", [{}])[0].get("id", "Disconnected") == pod.get_serial_number()
        stop_time = time.time()
        log.info("Connection state is correct")
        if not present:
            return stop_time
        log.info("Verify IP address")
        client_ip = self.client.eth1.run(f'ip -4 add show dev {self.eth_iface} | grep "inet "')
        client_ip = client_ip[client_ip.rfind("inet") + 5 : client_ip.rfind("/")]
        assert client_info.get("ip") == client_ip, (
            f"Incorrect ip address. Expected: {client_ip}" f' but got from NOC: {client_info.get("ip")}'
        )
        log.info("IP address is correct")
        return stop_time
