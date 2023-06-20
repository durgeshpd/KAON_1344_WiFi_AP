import allure
import pytest
import json
import time
from lib.util.base_case import BaseCase
from lib.util.testrail.plugin import pytestrail
from lib_testbed.generic.util.common import DeviceCommon
from lib_testbed.generic.util.logger import log


@pytest.mark.opensync_pod(role="gw")
@pytest.mark.opensync_client(name="wifi", wifi=True, type="linux")
@pytest.mark.opensync_cloud()
@pytest.mark.incremental
@pytest.mark.tag_frv
@pytest.mark.duration(seconds=464)
@pytestrail.case("C270229", "C396908", "C565956")
@allure.title("Enable disable GTK rekeying")
class Test03EnableDisableGtkRekeying(BaseCase):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(__class__, cls):
            cls.node_id = cls.pod.gw.get_serial_number()
            cls.ssid = cls.tb_config.get("Networks")[0]["ssid"]
            cls.password = cls.tb_config.get("Networks")[0]["key"]
            cls.gw_name = cls.pod.gw.get_nickname()
            # get 5g bssid from pod
            cls.bssid_5g = cls.cloud.admin.get_node_5g_home_ap_bssid(cls.node_id)[0]
            cls.wifi_iface = cls.client.wifi.get_wlan_iface()
            cls.home_ap = {}
            cls.br_home = DeviceCommon.get_gw_br_home(cls.tb_config)

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(Test03EnableDisableGtkRekeying, cls):
            log.info("Set gtk rekeying to auto mode")
            cls.cloud.admin.set_gtk_rekeying(state="auto")
            if hasattr(cls, "home_ap"):
                log.info("Set default gtk rekeying time")
                cls.change_rekey_time(86400)
            cls.client.wifi.disconnect(skip_exception=True)

    @allure.title("Enable GTK rekeying")
    def test_01_enable_gtk_rekeying(self):
        log.info("Enabling gtk rekeying")
        self.cloud.admin.set_gtk_rekeying(state="enable")
        log.info("Checking if gtk status has been changed...")
        network = self.cloud.user._cs.get_customer_location_wifinetwork(self.cloud.user.cid, self.cloud.user.lid).get(
            "wifiNetwork"
        )
        assert network, "Can not get wifi network  location information from cloud"
        assert network.get("groupRekey") == "enable", (
            f"GroupRekey status has not been changed." f" Expected: enabled, current status: {network}"
        )

    @allure.title("Connect client on 5G band to gateway")
    def test_02_connect_client(self):
        time.sleep(10)
        log.info("Connect client on 5G band to gateway")
        self.client.wifi.connect(ssid=self.ssid, psk=self.password, bssid=self.bssid_5g, timeout=60)
        log.info(f"Successfully connected client to SSID {self.ssid} with key {self.password} to {self.bssid_5g}")

    @allure.title("Checking group_rekey time")
    def test_03_check_group_rekey_time(self):
        log.info("Checking group_rekey time for enabled GTK. Expect time: 86400s")
        self.check_rekey_time(expected_time=86400)

    @allure.title("Changing group rekey time")
    def test_04_change_group_rekey_time(self):
        log.info("Changing group rekey time to 30s")
        self.change_rekey_time(time_rekey=30)
        log.info("Checking if group_rekey time has been changed to 30s")
        self.check_rekey_time(expected_time=30)

    @allure.title("Check gtk rekeying occurs in logs")
    def test_05_check_gtk_rekeying_occurs(self):
        log.info("Checking if gtk rekey-ing occurs in logs on the client every 30 sec")
        rekey_cmd = (
            'expect -c \'spawn wpa_cli -i %s; set timeout 60; expect "Group rekeying" {exit 0} default'
            " {exit 1}'" % self.wifi_iface
        )

        out = self.client.wifi.run_raw(rekey_cmd, timeout=65)
        assert out[0] == 0, f"Not able to get rekey log from wpa_cli\n{out}"
        log.info("Caught first rekey, checking time delta between next rekey")
        stime = time.time()

        log.info("Waiting for next gtk rekeying occurs")
        out = self.client.wifi.run_raw(rekey_cmd, timeout=65)
        assert out[0] == 0, f"Not able to get rekey log from wpa_cli\n{out}"
        assert 25 < time.time() - stime < 40, f"GTK rekey-ing occurred after: {time.time() - stime}, expected ~30 sec"
        log.info("Next successful wpa rekey after ~30 sec")

    def check_rekey_time(self, expected_time):
        timeout = time.time() + 30
        success = False
        home_ap = list()
        while timeout > time.time() and not success:
            ovsh_table = json.loads(self.pod.gw.get_ovsh_table("Wifi_VIF_State"))
            success = True
            for item in ovsh_table:
                if item["bridge"] == self.br_home:
                    home_ap.append(item["if_name"])
                    if item["group_rekey"] == expected_time:
                        log.info(f'Group rekey for {item["if_name"]} is set correctly: {item["group_rekey"]}')
                    else:
                        log.warn(
                            f'Group rekey for {item["if_name"]} is set incorrectly: {item["group_rekey"]},'
                            f" expected result: {expected_time}"
                        )
                        log.info("Rechecking in 5s...")
                        time.sleep(5)
                        home_ap = list()
                        success = False
                        break

        assert success, "Group rekey was set incorrectly"
        self.home_ap["homeAp"] = home_ap

    @classmethod
    def change_rekey_time(cls, time_rekey):
        home_ap = cls.home_ap.get("homeAp")
        for home_ap in home_ap:
            cls.pod.gw.run(f"ovsh u Wifi_VIF_Config --where if_name=={home_ap} " f"group_rekey:={time_rekey}")
            time.sleep(5)
