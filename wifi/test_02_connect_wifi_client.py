#!/usr/bin/env python3

import pytest
import allure
from lib.util.base_case import BaseCase
from lib_testbed.generic.util.logger import log
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_cloud()
@pytest.mark.opensync_client(name="wifi", wifi=True)
@pytest.mark.incremental
@pytest.mark.tag_frv
@pytest.mark.tag_res_gw_frv
@pytest.mark.tag_client_connectivity
class ConnectWifiClientRoot(BaseCase):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(ConnectWifiClientRoot, cls):
            cls.short_type_test = False
            for mark in cls.all_markers:
                if mark.name == "wifi_test":
                    if mark.kwargs.get("short"):
                        cls.short_type_test = True
                        break
            cls.pods_bssid = cls.get_pods_bssid()
            cls.ssid = cls.tb_config.get("Networks")[0]["ssid"]
            cls.password = cls.tb_config.get("Networks")[0]["key"]

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(ConnectWifiClientRoot, cls):
            cls.client.wifi.disconnect(skip_exception=True)

    @allure.title("Connect wifi client")
    def test_01_connect_wifi_client(self):
        for bssid in self.pods_bssid:
            self.client.wifi.connect(ssid=self.ssid, psk=self.password, bssid=bssid)
            log.info("Check external ping on the client")
            assert self.client.wifi.ping_check(fqdn_check=True), "Client has no internet access"
            log.info("External ping check finished successfully")
            self.client.wifi.disconnect(skip_exception=True)

    @classmethod
    def get_pods_bssid(cls):
        pods_bssid = [None]
        if cls.short_type_test is False:
            all_bssid_api = cls.cloud.admin.get_home_ap_bssids_from_cloud()
            pods_bssid = []
            for node_serial in all_bssid_api.keys():
                for band_type, bssid in all_bssid_api[node_serial]:
                    pods_bssid.append(bssid)
        return pods_bssid


@pytest.mark.duration(seconds=93)
@pytest.mark.TC_ConnectivityWifi_10002
@pytestrail.case("C270227", "C396907", "C571844", "C565951")
@pytest.mark.wifi_test(short=False)
@pytest.mark.network_mode(target="bridge")
@allure.title("Connect WiFi Client Bridge")
class Test02ConnectWifiClientBridge(ConnectWifiClientRoot):
    pass


@pytest.mark.duration(seconds=93)
@pytestrail.case("C270228", "C396949", "C396973", "C571845", "C565952")
@pytest.mark.wifi_test(short=False)
@pytest.mark.network_mode(target="router")
@allure.title("Connect WiFi Client Router")
class Test02ConnectWifiClientRouter(ConnectWifiClientRoot):
    pass


@pytest.mark.duration(seconds=28)
@pytestrail.case("C270185", "C396848", "C565955")
@pytest.mark.wifi_test(short=True)
@allure.title("Connect WiFi Client Short")
class Test02ConnectWifiClientShort(ConnectWifiClientRoot):
    pass
