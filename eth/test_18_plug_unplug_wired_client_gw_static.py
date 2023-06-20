import allure
import pytest
from lib_testbed.generic.util.logger import log
from tests.client_connectivity.eth.wired_connection_root import WiredConnectionRoot
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_pod(role="gw", switch=".*")
@pytest.mark.tag_xtom
class PlugUnplugWiredClientGwStatic(WiredConnectionRoot):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(__class__, cls):
            cls.static_mode = True
            cls.gw_onboard_time = cls.tb_config["Nodes"][0]["capabilities"]["kpi"].get("cloud_gw_onboard_time")

    @allure.title("Plugging and unplugging a wired client")
    def test_01_plug_and_unplug_eth_client(self, wan_id):
        max_conn_time = self.gw_onboard_time + 60
        max_conn_time_noc = self.gw_onboard_time + 60 + 30
        for i in range(0, 4):
            log.info("*" * 75)
            log.info(f"Unplugging and plugging eth client, attempt: {i + 1}")
            con_time, start_time = self.connect_eth_client(device=self.pod.gw, dhcp_timeout=200)
            log.info("Verify client at the NOC")
            stop_time = self.verify_client_noc(self.pod.gw)
            noc_conn_time = stop_time - start_time
            log.info(f"Eth client connection time: {con_time:.2f} sec")
            log.info(f"Eth client NOC appear time: {noc_conn_time:.2f} sec")
            assert con_time < max_conn_time, f"Connection time too long about {con_time - max_conn_time}"
            assert (
                noc_conn_time < max_conn_time_noc
            ), f"NOC appear time too long about {noc_conn_time - max_conn_time_noc}"
            log.info("Disconnecting eth client")
            self.switch.api.disconnect_eth_client(self.pod.gw.nickname, self.eth_name)
            log.info(f"Reboot {self.pod.gw.nickname} after connect eth client")
            self.cloud.user.reboot_pod(self.pod.gw.lib.device.config["id"])
            log.info("Wait for disconnect")
            assert self.cloud.user.check_pods_disconnected(
                minpods=2
            ), f"{self.pod.gw.get_nickname()} not disconnected after reboot"
            log.info("GW device disconnected")
            log.info("Wait for connect all pods to the cloud")
            assert self.cloud.user.check_pods_connected(), "Not all devices connected to cloud"
            log.info("All devices connected to the cloud")
            self.verify_client_noc(present=False)


@pytest.mark.tag_frv
@pytest.mark.duration(seconds=1713)
@pytestrail.case("C298356")
@pytest.mark.network_mode(target="bridge")
@allure.title("Plugging and unplugging a wired client at a gw pod static - bridge")
class Test18PlugUnplugWiredClientGwStaticBridge(PlugUnplugWiredClientGwStatic):
    pass


@pytest.mark.tag_frv
@pytest.mark.duration(seconds=1713)
@pytestrail.case("C594561")
@pytest.mark.network_mode(target="router")
@allure.title("Plugging and unplugging a wired client at a gw pod static - router")
class Test18PlugUnplugWiredClientGwStaticRouter(PlugUnplugWiredClientGwStatic):
    pass
