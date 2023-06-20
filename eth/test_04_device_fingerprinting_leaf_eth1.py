import pytest
import allure
from tests.client_connectivity.eth.test_04_device_fingerprinting_leaf_eth import (
    DeviceFingerprintingEthLeafRoot,
)
from lib.util.testrail.plugin import pytestrail


@pytest.mark.opensync_pod(role="leaf", switch=".*", mgmt="optional")
@pytest.mark.wan(port="secondary")
@pytest.mark.network_mode(target="router")
@pytest.mark.tag_frv
@pytest.mark.tag_crv
@pytest.mark.tag_wan_eth1
@pytest.mark.duration(seconds=700)
@pytest.mark.TC_ConnectivityEth_10008
@pytestrail.case("C231041", "C396941", "C571858", "C566150")
@allure.title("Device fingerprinting leaf router eth1")
class Test04DeviceFingerprintingLeafEth1Router(DeviceFingerprintingEthLeafRoot):
    pass
