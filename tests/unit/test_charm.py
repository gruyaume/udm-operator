# Copyright 2022 Guillaume Belanger
# See LICENSE file for licensing details.

import unittest
from unittest.mock import Mock, patch

from ops import testing
from ops.model import ActiveStatus

from charm import UDMOperatorCharm


class TestCharm(unittest.TestCase):
    @patch(
        "charm.KubernetesServicePatch",
        lambda charm, ports: None,
    )
    def setUp(self):
        self.namespace = "whatever"
        self.harness = testing.Harness(UDMOperatorCharm)
        self.harness.set_model_name(name=self.namespace)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def _nrf_is_available(self) -> str:
        nrf_url = "http://1.1.1.1"
        nrf_relation_id = self.harness.add_relation("nrf", "nrf-operator")
        self.harness.add_relation_unit(
            relation_id=nrf_relation_id, remote_unit_name="nrf-operator/0"
        )
        self.harness.update_relation_data(
            relation_id=nrf_relation_id, app_or_unit="nrf-operator", key_values={"url": nrf_url}
        )
        return nrf_url

    @patch("ops.model.Container.push")
    def test_given_can_connect_to_worload_when_nrf_is_available_then_config_file_is_written(
        self,
        patch_push,
    ):
        nrf_url = "2.2.2.2"
        udm_hostname = f"udm-operator.{self.namespace}.svc.cluster.local"
        self.harness.set_can_connect(container="udm", val=True)

        self.harness.charm._on_nrf_available(event=Mock(url=nrf_url))

        patch_push.assert_called_with(
            path="/etc/udm/udmcfg.conf",
            source=f'configuration:\n  keys:\n    udmProfileAHNPrivateKey: c53c22208b61860b06c62e5406a7b330c2b577aa5558981510d128247d38bd1d\n    udmProfileAHNPublicKey: 5a8d38864820197c3394b92613b20b91633cbd897119273bf8e4a6f4eec0a650\n    udmProfileBHNPrivateKey: F1AB1074477EBCC7F554EA1C5FC368B1616730155E0041AC447D6301975FECDA\n    udmProfileBHNPublicKey: 0472DA71976234CE833A6907425867B82E074D44EF907DFB4B3E21C1C2256EBCD15A7DED52FCBB097A4ED250E036C7B9C8C7004C4EEDC4F068CD7BF8D3F900E3B4\n  nrfUri: {nrf_url}\n  plmnList:\n  - plmnId:\n      mcc: "208"\n      mnc: "93"\n  - plmnId:\n      mcc: "222"\n      mnc: "88"\n  sbi:\n    bindingIPv4: 0.0.0.0\n    port: 29503\n    registerIPv4: {udm_hostname}\n    scheme: http\n    tls:\n      key: free5gc/support/TLS/udm.key\n      log: free5gc/udmsslkey.log\n      pem: free5gc/support/TLS/udm.pem\n  serviceNameList:\n  - nudm-sdm\n  - nudm-uecm\n  - nudm-ueau\n  - nudm-ee\n  - nudm-pp\ninfo:\n  description: UDM initial local configuration\n  version: 1.0.0\nlogger:\n  AMF:\n    ReportCaller: false\n    debugLevel: info\n  AUSF:\n    ReportCaller: false\n    debugLevel: info\n  Aper:\n    ReportCaller: false\n    debugLevel: info\n  CommonConsumerTest:\n    ReportCaller: false\n    debugLevel: info\n  FSM:\n    ReportCaller: false\n    debugLevel: info\n  MongoDBLibrary:\n    ReportCaller: false\n    debugLevel: info\n  N3IWF:\n    ReportCaller: false\n    debugLevel: info\n  NAS:\n    ReportCaller: false\n    debugLevel: info\n  NGAP:\n    ReportCaller: false\n    debugLevel: info\n  NRF:\n    ReportCaller: false\n    debugLevel: info\n  NamfComm:\n    ReportCaller: false\n    debugLevel: info\n  NamfEventExposure:\n    ReportCaller: false\n    debugLevel: info\n  NsmfPDUSession:\n    ReportCaller: false\n    debugLevel: info\n  NudrDataRepository:\n    ReportCaller: false\n    debugLevel: info\n  OpenApi:\n    ReportCaller: false\n    debugLevel: info\n  PCF:\n    ReportCaller: false\n    debugLevel: info\n  PFCP:\n    ReportCaller: false\n    debugLevel: info\n  PathUtil:\n    ReportCaller: false\n    debugLevel: info\n  SMF:\n    ReportCaller: false\n    debugLevel: info\n  UDM:\n    ReportCaller: false\n    debugLevel: info\n  UDR:\n    ReportCaller: false\n    debugLevel: info\n  WEBUI:\n    ReportCaller: false\n    debugLevel: info',  # noqa: E501
        )

    @patch("charm.check_output")
    @patch("ops.model.Container.exists")
    def test_given_config_file_is_written_when_pebble_ready_then_pebble_plan_is_applied(
        self,
        patch_exists,
        patch_check_output,
    ):
        pod_ip = "1.1.1.1"
        patch_exists.return_value = True
        patch_check_output.return_value = pod_ip.encode()

        self._nrf_is_available()

        self.harness.container_pebble_ready(container_name="udm")

        expected_plan = {
            "services": {
                "udm": {
                    "override": "replace",
                    "command": "./udm --udmcfg /etc/udm/udmcfg.conf",
                    "startup": "enabled",
                    "environment": {
                        "GRPC_GO_LOG_VERBOSITY_LEVEL": "99",
                        "GRPC_GO_LOG_SEVERITY_LEVEL": "info",
                        "GRPC_TRACE": "all",
                        "GRPC_VERBOSITY": "debug",
                        "POD_IP": pod_ip,
                        "MANAGED_BY_CONFIG_POD": "true",
                    },
                }
            },
        }

        updated_plan = self.harness.get_container_pebble_plan("udm").to_dict()

        self.assertEqual(expected_plan, updated_plan)

    @patch("charm.check_output")
    @patch("ops.model.Container.exists")
    def test_given_config_file_is_written_when_pebble_ready_then_status_is_active(
        self, patch_exists, patch_check_output
    ):
        patch_exists.return_value = True
        patch_check_output.return_value = b"1.2.3.4"

        self._nrf_is_available()

        self.harness.container_pebble_ready("udm")

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())
