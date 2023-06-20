import pytest
import allure
from tests.client_connectivity.eth.test_03_device_fingerprinting_eth_sp import (
    DeviceFingerprintingEthRoot,
)
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_pod(role="gw", switch=".*", mgmt="optional")
@pytest.mark.wan(port="secondary")
@pytest.mark.network_mode(target="router")
@pytest.mark.tag_crv
@pytest.mark.tag_frv
@pytest.mark.tag_wan_eth1
@pytest.mark.duration(seconds=784)
@pytestrail.case("C231035", "C396940", "C270124", "C571852", "C566144")
@allure.title("Device fingerprinting eth secondary wan port - router SuperPod")
class Test03DeviceFingerprintingEthSecondaryWanRouterSuperPod(DeviceFingerprintingEthRoot):
    pass
