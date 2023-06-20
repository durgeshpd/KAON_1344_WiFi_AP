import allure
import pytest
from lib_testbed.generic.util.logger import log
from tests.client_connectivity.eth.wired_connection_root import WiredConnectionRoot
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_pod(role="leaf", switch=".*")
@pytest.mark.tag_xtom
class PlugUnplugWiredClientLeafStatic(WiredConnectionRoot):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(PlugUnplugWiredClientLeafStatic, cls):
            cls.static_mode = True
            cls.leaf_onboard_time = cls.tb_config["Nodes"][0]["capabilities"]["kpi"].get("cloud_leaf_onboard_time")

    @allure.title("Plugging and unplugging a wired client")
    def test_01_plug_and_unplug_eth_client(self, wan_id):
        max_conn_time = self.leaf_onboard_time + 60
        max_conn_time_noc = self.leaf_onboard_time + 60 + 30
        log.info(f"KPI for Leaf's ETH client working after leaf reboot: {max_conn_time} sec")
        log.info(f"KPI for Leaf's ETH client showing in FTL after leaf reboot: {max_conn_time_noc} sec")
        for i in range(0, 4):
            log.info("*" * 75)
            log.info(f"Unplugging and plugging eth client, attempt: {i + 1}")
            # Timeout no matter here, because verification of KPI is done after.
            con_time, start_time = self.connect_eth_client(device=self.pod.leaf, dhcp_timeout=200)
            log.info("Verify client at the NOC")
            stop_time = self.verify_client_noc(self.pod.leaf)
            noc_conn_time = stop_time - start_time
            log.info(f"Eth client connection time: {con_time:.2f} sec")
            log.info(f"Eth client NOC appear time: {noc_conn_time:.2f} sec")
            assert con_time < max_conn_time, f"Connection time too long about {con_time - max_conn_time}"
            assert (
                noc_conn_time < max_conn_time_noc
            ), f"NOC appear time too long about {noc_conn_time - max_conn_time_noc}"

            self.switch.api.disconnect_eth_client(self.pod.leaf.nickname, self.eth_name)
            log.info(f"Reboot {self.pod.leaf.nickname} after connect eth client")
            self.pod.leaf.reboot()
            log.info("Wait for disconnect")
            assert self.cloud.user.check_pods_connected(
                minpods=1, option="disconnected"
            ), f"{self.pod.leaf.nickname} not disconnected after reboot"
            log.info("Leaf device disconnected")
            log.info("Wait for connect all pods to cloud")
            assert self.cloud.user.check_pods_connected(), "Not all devices connected to cloud"
            log.info("All devices connected to cloud")
            self.verify_client_noc(present=False)


@pytest.mark.duration(seconds=1577)
@pytestrail.case("C298352")
@pytest.mark.tag_frv
@pytest.mark.network_mode(target="bridge")
@allure.title("Plugging and unplugging a wired client at a leaf pod static - bridge")
class Test16PlugUnplugWiredClientLeafStaticBridge(PlugUnplugWiredClientLeafStatic):
    pass


@pytest.mark.duration(seconds=1607)
@pytestrail.case("C594557")
@pytest.mark.tag_frv
@pytest.mark.network_mode(target="router")
@allure.title("Plugging and unplugging a wired client at a leaf pod static - router")
class Test16PlugUnplugWiredClientLeafStaticRouter(PlugUnplugWiredClientLeafStatic):
    pass
