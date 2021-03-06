# pylint: disable=no-self-use # pyATS-related exclusion
# pylint: disable=attribute-defined-outside-init # pyATS-related exclusion
import os
import logging
from pprint import pformat


from pyats import aetest


from src.classes.remote_tools import SeleniumGrid
from src.classes.tshark_pcap import TsharkPcap
from src.classes.utils import _temp_files_dir
from src.classes.clients import Chrome
from src.classes.analyse import BrowserResponseAnalyzer


_log = logging.getLogger(__name__)


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def update_testscript_parameters(self, testbed):
        user_device = testbed.devices["user-2"]
        proxy_device = testbed.devices["proxy-vm"]
        self.parent.parameters.update(
            {
                "user": user_device,
                "proxy": proxy_device,
            }
        )

    @aetest.subsection
    def start_selenium(self, user):
        grid = SeleniumGrid(user)
        grid.start()


class BrockenCerts(aetest.Testcase):
    @aetest.test
    def brocken_certs_test(self, user, proxy, host):

        with Chrome(grid_server=user, proxy_server=proxy) as chrome:
            chrome.get(host)
            stats = chrome.get_stats()

        data = BrowserResponseAnalyzer(stats)
        errors = data.get_browser_errors()
        pass_condition = len(errors) >= 1 and "ERR_CERT_AUTHORITY_INVALID" in errors[0]
        if not pass_condition:
            _log.info(f"Web Brower logs:\n{pformat(stats)}")
            self.failed("Invalod response, no `ERR_CERT_AUTHORITY_INVALID` occured!")


class ObsoleteTLS(aetest.Testcase):
    @aetest.test
    def obsolete_tls_test(self, user, proxy, host):

        with Chrome(grid_server=user, proxy_server=proxy) as chrome:
            chrome.get(host)
            stats = chrome.get_stats()

        data = BrowserResponseAnalyzer(stats)
        errors = data.get_browser_errors()
        expected_message = (
            f"The connection used to load resources from {host}"
            " used TLS 1.0 or TLS 1.1, which are deprecated and will be disabled"
            " in the future."
        )
        pass_condition = False
        if errors:
            for error in errors:
                if expected_message in error:
                    pass_condition = True
        if not pass_condition:
            _log.info(f"Web Brower logs:\n{pformat(stats)}")
            self.failed("Invalod response, no `ERR_SSL_OBSOLETE_VERSION` occured!")


class TLSHandshake12(aetest.Testcase):
    @aetest.test
    def tls_1_2_handshake_test(self, user, proxy, host):

        with Chrome(
            grid_server=user,
            proxy_server=proxy,
            chrome_arguments=[
                "--ssl-version-max=tls1.2",
            ],
            traffic_dump=True,
        ) as chrome:
            chrome.get(host)

        pcap_file = f"{user.name}_tshark.pcap"
        pcap_file = os.path.join(_temp_files_dir, pcap_file)
        pcap_obj = TsharkPcap(pcap_file)

        if pcap_obj.find_packets_in_stream(packet_type="tls1.2")[0] is False:
            self.failed("TLS handshake sequence not found")


class TLSHandshake13(aetest.Testcase):
    @aetest.test
    def tls_1_3_handshake_test(self, user, proxy, host):

        with Chrome(
            grid_server=user,
            proxy_server=proxy,
            chrome_arguments=[
                "--ssl-version-max=tls1.3",
            ],
            traffic_dump=True,
        ) as chrome:
            chrome.get(host)

        pcap_file = f"{user.name}_tshark.pcap"
        pcap_file = os.path.join(_temp_files_dir, pcap_file)
        pcap_obj = TsharkPcap(pcap_file)

        if pcap_obj.find_packets_in_stream(packet_type="tls1.3")[0] is False:
            self.failed("TLS handshake sequence not found")


class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def stop_selenium(self, user):
        grid = SeleniumGrid(user)
        grid.stop()


if __name__ == "__main__":
    import sys
    import argparse

    from pyats import topology

    _log.setLevel(logging.DEBUG)
    logging.getLogger("unicon").setLevel(logging.INFO)

    parser = argparse.ArgumentParser(description="standalone parser")
    parser.add_argument("--testbed", dest="testbed", type=topology.loader.load)

    args, sys.argv[1:] = parser.parse_known_args(sys.argv[1:])
    aetest.main(testbed=args.testbed)
