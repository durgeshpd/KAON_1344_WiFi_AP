import pytest
import allure
import time
import datetime
from lib.util.base_case import BaseCase
from lib_testbed.generic.util.logger import log
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_switch()
@pytest.mark.opensync_cloud()
@pytest.mark.opensync_pod(role="leaf", switch=".*")
@pytest.mark.opensync_pods(name="all")
@pytest.mark.opensync_client(eth=True, name="eth1", vlan=".*")
@pytest.mark.opensync_client(eth=True, name="eth2", vlan=".*")
@pytest.mark.tag_eth
@pytest.mark.tag_frv
@pytest.mark.tag_client_connectivity
@pytest.mark.incremental
@pytest.mark.duration(seconds=1483)
@pytestrail.case("C270131", "C396905", "C566037")
@allure.title("Network mode change with two ethernet clients on the same pod")
class Test09NetworkModeChangeWithTwoEthClients(BaseCase):
    @classmethod
    def setup_class(cls):
        cls.attempts = 3
        with cls.SafeSetup(Test09NetworkModeChangeWithTwoEthClients, cls):
            cls.all_pods = cls.pods.all.get_nicknames()
            cls.leaf_name = cls.pod.leaf.get_nickname()
            cls.eth1_name = cls.client.eth1.get_nickname()
            cls.eth1_iface = cls.client.eth1.get_eth_iface()
            cls.eth2_name = cls.client.eth2.get_nickname()
            cls.eth2_iface = cls.client.eth2.get_eth_iface()
            log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
            cls.switch.api.recovery_switch_configuration(cls.all_pods)
            cls.optimize_time = {}
            cls.topology_data = {}

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(Test09NetworkModeChangeWithTwoEthClients, cls):
            cls.cloud.admin.disable_autooptimization()
            if hasattr(cls.client, "eth1") and hasattr(cls.client, "eth2"):
                log.info(f"Recovery default switch configuration on all used devices: {cls.all_pods}")
                cls.switch.api.recovery_switch_configuration(cls.all_pods)

    @allure.title("Trigger manual optimization")
    def test_01_trigger_manual_optimization(self):
        nowtime = datetime.datetime.utcnow() - datetime.timedelta(seconds=20)
        check_from_time = nowtime.isoformat()
        self.cloud.admin.set_dfs_mode_state("auto")
        self.cloud.admin.enable_autooptimization()
        log.info("Trigger manual optimization to get optimized state on the location")
        assert "createdAt" in self.cloud.admin.trigger_manual_optimization(), "Triggering manual optimization failed"
        log.info("Wait for manual optimization")
        assert self.cloud.admin.check_optimization(nowtime=check_from_time)["result"]
        log.info("Optimization finished successfully")
        self.topology_data["previous_topo"] = self.cloud.admin.get_wifi_config()
        self.optimize_time.update({"checkTime": datetime.datetime.utcnow().isoformat()})

    @allure.title("Connect eth clients to leaf")
    def test_01_2_connect_eth_clients_to_leaf(self):
        log.info("Check loop status before connect eth client to node")
        self.pod.leaf.wait_eth_connection_ready()
        log.info("Connect eth clients to leaf")
        log.info(f"Connect {self.eth1_name} client to {self.leaf_name} device")
        self.switch.api.connect_eth_client(self.leaf_name, self.eth1_name)
        log.info(f"Connect {self.eth2_name} client to {self.leaf_name} device")
        self.switch.api.connect_eth_client(self.leaf_name, self.eth2_name)
        self.check_internet_access_on_clients()
        self.check_ping_between_clients()

    @allure.title("Change network mode")
    def test_02_change_network_mode(self):
        log.info("Change network mode")
        target_net_mode = self.get_net_for_change()
        self.optimize_time["checkTime"] = datetime.datetime.utcnow().isoformat()
        log.info(f"Changing network mode to {target_net_mode}")
        self.cloud.user.set_network_mode_wait(target_net_mode)
        self.wait_pods_ready()
        self.wait_for_connect_eth_client()
        self.check_ping_between_clients()

    @allure.title("Check optimization")
    def test_03_check_optimization(self):
        log.info("Check if optimization is triggered")
        check_from_time = self.optimize_time.get("checkTime")
        assert self.cloud.admin.check_optimization(
            nowtime=check_from_time, top_before=self.topology_data["previous_topo"]
        )["result"], "Optimization check failed"

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

    def check_ping_between_clients(self):
        eth1_ip = self.client.eth1.run(f'ip -4 add show dev {self.eth1_iface} | grep "inet "')
        eth1_ip = eth1_ip[eth1_ip.rfind("inet") + 5 : eth1_ip.rfind("/")]
        eth2_ip = self.client.eth2.run(f'ip -4 add show dev {self.eth2_iface} | grep "inet "')
        eth2_ip = eth2_ip[eth2_ip.rfind("inet") + 5 : eth2_ip.rfind("/")]

        assert eth1_ip and eth2_ip, (
            f"Can not get IP from eth client. "
            f"{self.eth1_name}: ip address: {eth1_ip}, {self.eth2_name}: ip address: {eth2_ip}"
        )

        log.info(f"Check ping from {eth1_ip} to {eth2_ip}")
        assert self.client.eth1.ping_check(ipaddr=eth2_ip, fqdn_check=False), f"Ping from {eth1_ip} to {eth2_ip} failed"
        log.info(f"Ping from {eth1_ip} to {eth2_ip} has been finished successfully")

        log.info(f"Check ping from {eth2_ip} to {eth1_ip}")
        assert self.client.eth2.ping_check(ipaddr=eth1_ip, fqdn_check=False), f"Ping from {eth2_ip} to {eth1_ip} failed"
        log.info(f"Ping from {eth2_ip} to {eth1_ip} has been finished successfully")

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
        self.pod.leaf.wait_eth_connection_ready()

    def wait_for_connect_eth_client(self):
        timeout = time.time() + 300
        status = False
        while timeout > time.time():
            log.info(f"Check if eth clients {self.eth1_name} and {self.eth2_name} have internet access")
            self.client.eth1.refresh_ip_address(timeout=20, skip_exception=True)
            self.client.eth2.refresh_ip_address(timeout=20, skip_exception=True)
            check_ping_eth1 = self.client.eth1.ping_check(skip_exception=True)
            check_ping_eth2 = self.client.eth2.ping_check(skip_exception=True)
            if check_ping_eth1 and check_ping_eth2:
                log.info("Ethernet clients have internet access")
                status = True
                break
            log.info("Wait 5 seconds and try again")
            time.sleep(5)
        assert status, "Ethernet clients have not internet access after expired 300s"
