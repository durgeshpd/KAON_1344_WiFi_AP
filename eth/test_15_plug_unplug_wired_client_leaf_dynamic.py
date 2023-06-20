import allure
import pytest
import time
from lib_testbed.generic.util.logger import log
from tests.client_connectivity.eth.wired_connection_root import WiredConnectionRoot
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_pod(role="leaf", switch=".*")
class PlugUnplugWiredClientLeafDynamic(WiredConnectionRoot):
    @allure.title("Plugging and unplugging a wired client")
    def test_01_plug_and_unplug_eth_client(self, wan_id):
        for i in range(0, 4):
            log.info("*" * 75)
            log.info(f"Unplugging and plugging eth client, attempt: {i + 1}")
            # Timeout no matter here, because verification of KPI is done after.
            con_time, start_time = self.connect_eth_client(device=self.pod.leaf, dhcp_timeout=200)
            log.info("Verify client at the NOC")
            stop_time = self.verify_client_noc(self.pod.leaf)
            noc_conn_time = stop_time - start_time
            self.switch.api.disconnect_eth_client(self.pod.leaf.get_nickname(), self.eth_name)
            start_time = time.time()
            stop_time = self.verify_client_noc(present=False)
            noc_disconn_time = stop_time - start_time
            log.info(f"Eth client connection time: {con_time:.2f} sec")
            log.info(f"Eth client NOC appear time: {noc_conn_time:.2f} sec")
            log.info(f"Eth client NOC disappear time: {noc_disconn_time:.2f} sec")
            assert con_time < 20, "Connection time too long"
            assert noc_conn_time < 50, "NOC appear time too long"
            assert noc_disconn_time < 30, "NOC disappear time too long"


@pytest.mark.tag_frv
@pytest.mark.duration(seconds=531)
@pytestrail.case("C298351")
@pytest.mark.network_mode(target="bridge")
@allure.title("Plugging and unplugging a wired client at a leaf pod dynamic - bridge")
class Test15PlugUnplugWiredClientLeafDynamicBridge(PlugUnplugWiredClientLeafDynamic):
    pass


@pytest.mark.tag_frv
@pytest.mark.duration(seconds=543)
@pytestrail.case("C594556")
@pytest.mark.network_mode(target="router")
@allure.title("Plugging and unplugging a wired client at a leaf pod dynamic - router")
class Test15PlugUnplugWiredClientLeafDynamicRouter(PlugUnplugWiredClientLeafDynamic):
    pass
