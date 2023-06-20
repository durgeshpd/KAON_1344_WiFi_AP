import os
import uuid
import shutil
import allure
import pytest
import pyshark
from lib.util.base_case import BaseCase
from lib_testbed.generic.util.logger import log
from lib.util.testrail.plugin import pytestrail

LOCAL_SNIFF_PATH = "/tmp/automation/tcp_dump/"


@pytest.mark.opensync_util(lib_path="topologylib", name="topology_lib")
@pytest.mark.opensync_client(name="w2", wifi=True)
@pytest.mark.opensync_client(name="w1", wifi=True, type="linux")
@pytest.mark.opensync_pod(role="gw")
@pytest.mark.opensync_pods(name="all")
@pytest.mark.opensync_cloud()
@pytestrail.case("C1699171")
@allure.title("Gateway does not respond to probe requests when STA is not on the whitelist")
class Test07GwDoesNotRespondToProbeRequestsWhenStaIsNotOnTheWhitelist(BaseCase):
    @classmethod
    def setup_class(cls):
        with cls.SafeSetup(__class__, cls):
            cls.sniff_file = f"tcp_dump_{uuid.uuid4().hex}.pcap"
            cls.sniff_path = os.path.join(LOCAL_SNIFF_PATH, cls.sniff_file)
            cls.ssid, cls.psk = cls.get_onboard_credentials()

    @classmethod
    def teardown_class(cls):
        with cls.SafeTeardown(__class__, cls):
            cls.client.w2.disconnect(skip_exception=True)
            cls.clean_tcpdump_file()

    @allure.title("Set topology to 5G channels")
    def test_01_set_topology(self):
        log.info("Set topology to be sure bhaul connection is set to the same channel")
        current_topology = self.cloud.user.get_wifi_config()
        topology_to_set = self.util.topology_lib.form_star(top=current_topology, channel="44")
        assert self.util.topology_lib.set_topology(
            self.cloud.admin, topology_to_set, timeout=900
        ), "Cannot change topology to channel: 44"

    @allure.title("Run sniffer")
    def test_02_run_sniffer(self):
        self.start_sniffer(channel="44", ht_mode="HT20")

    @allure.title("Try connect a client to onboard network")
    def test_03_try_connect_client_to_onboard_network(self):
        response = self.client.w2.connect(ssid=self.ssid, psk=self.psk, skip_exception=True)
        assert not response, (
            f"{self.client.w2.nickname} has been connected to onboard network event though "
            f"doesnt appear on the whitelist"
        )
        log.info(f"{self.client.w2.nickname} has not been connected to onboard network as expected")

    @allure.title("Check sniffer capture to see if AP does not reply STA")
    def test_04_check_sniffer_capture(self):
        log.info("Check sniffer capture to see if AP does not reply STA's")
        self.client.w1.run("killall tcpdump", skip_exception=True)
        log.info(f"Download tcpdump from client to local machine: {self.sniff_path}")
        if not os.path.exists(LOCAL_SNIFF_PATH):
            os.makedirs(LOCAL_SNIFF_PATH)
        self.client.w1.get_file(f"/tmp/{self.sniff_file}", LOCAL_SNIFF_PATH, create_dir=False, timeout=120)
        onboard_mac_addresses = self.get_onboard_mac_addresses()
        location_onboard_macs = [f"wlan.addr == {mac}" for mac in onboard_mac_addresses]
        onboard_mac_filter = " || ".join(location_onboard_macs)
        # Filter for Probe Responses: wlan.fc.type_subtype == 5
        pyshark_filter = f"wlan.addr == {self.client.w2.mac} && wlan.fc.type_subtype == 5 " f"&& ({onboard_mac_filter})"
        log.info(f"Pyshark filter:\n{pyshark_filter}")
        packets = pyshark.FileCapture(self.sniff_path, display_filter=pyshark_filter, only_summaries=False)
        packets.load_packets()
        log.info("Check Probe Responses from the onboard network")
        assert not len(packets), "Found assoc responses from the onboard network"
        log.info("Not found any Probe Responses responses from the onboard network")

    @classmethod
    def get_onboard_credentials(cls):
        onboard_interfaces = cls.pod.gw.capabilities.get_onboard_ap_ifnames(return_type=list)
        assert onboard_interfaces, "Onboard interfaces does not specific on the capabilities config"
        onboard_interface = onboard_interfaces[0]
        onboard_cfg = cls.pod.gw.ovsdb.get_json_table(table="Wifi_VIF_State", where=f"if_name=={onboard_interface}")
        ssid = onboard_cfg.get("ssid")
        security_key = cls.get_security_key(onboard_cfg)
        assert ssid, f"Can not get SSID from onboard interface: {onboard_interface}"
        assert security_key, f"Can not get security key from onboard interface: {onboard_interface}"
        return ssid, security_key

    def start_sniffer(self, channel, ht_mode):
        log.info(f"Running sniffer on the {self.client.w1.nickname} client")
        self.client.w1.wifi_monitor(channel=channel, ht=ht_mode, ifname=self.client.w1.ifname)
        self.client.w1.run(
            f"tcpdump -U -i {self.client.w1.ifname} -w /tmp/{self.sniff_file}" f" > /tmp/tcp_dump_log.txt 2>&1 &"
        )

    def get_onboard_mac_addresses(self):
        mac_addresses = list()
        for device in self.pods.all.get_devices():
            table = device.ovsdb.get_json_table(table="Wifi_VIF_State", where=f"ssid=={self.ssid}", skip_exception=True)
            if not table:
                continue
            for onboard_network in table:
                mac_addresses.append(onboard_network["mac"])
        return mac_addresses

    @classmethod
    def get_security_key(cls, onboard_cfg):
        key = cls.pod.gw.ovsdb.ovsdb_map_to_python_dict(onboard_cfg.get("wpa_psks", ["map", []])).get("key--1")

        if key is None:
            key = cls.pod.gw.ovsdb.ovsdb_map_to_python_dict(onboard_cfg["security"]).get("key")

        return key

    @classmethod
    def clean_tcpdump_file(cls):
        cls.client.w1.run("killall tcpdump", skip_exception=True)
        cls.client.w1.run("rm /tmp/tcp_dump_*", skip_exception=True)
        try:
            os.remove(cls.sniff_path)
        except OSError:
            pass
