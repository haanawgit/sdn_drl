from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import (
    CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
)
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet, ether_types
from os_ken.lib import hub


class AdaptiveController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # s1: port 1 -> h1; ports 2, 3, 4 -> parallel links
    PATH_PORTS = (2, 3, 4)
    S2_HOST_PORT = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datapaths = {}
        self.port_bytes = {}
        self.port_rates = {}
        self.selected_path = None
        self.monitor_thread = hub.spawn(self._monitor)

    def add_flow(self, dp, priority, match, actions,
                 idle_timeout=3, hard_timeout=10):
        parser = dp.ofproto_parser
        ofp = dp.ofproto
        dp.send_msg(parser.OFPFlowMod(
            datapath=dp,
            priority=priority,
            match=match,
            instructions=[
                parser.OFPInstructionActions(
                    ofp.OFPIT_APPLY_ACTIONS, actions
                )
            ],
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout
        ))

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_ready(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        parser = dp.ofproto_parser
        ofp = dp.ofproto

        # Send unknown packets to the controller; forwarding is decided here.
        self.add_flow(
            dp, 0, parser.OFPMatch(),
            [parser.OFPActionOutput(
                ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER
            )],
            idle_timeout=0, hard_timeout=0
        )
        self.logger.info("Switch connected: %s", dp.id)

    def _monitor(self):
        while True:
            for dp in list(self.datapaths.values()):
                dp.send_msg(
                    dp.ofproto_parser.OFPPortStatsRequest(dp, 0)
                )
            hub.sleep(2)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply(self, ev):
        dp = ev.msg.datapath
        for stat in ev.msg.body:
            key = (dp.id, stat.port_no)
            current = stat.tx_bytes + stat.rx_bytes
            previous = self.port_bytes.get(key)
            if previous is not None:
                self.port_rates[key] = max(
                    0, current - previous
                ) / 2.0
            self.port_bytes[key] = current

    def _choose_path(self):
        measured = [
            (self.port_rates[(1, port)], port)
            for port in self.PATH_PORTS
            if (1, port) in self.port_rates
        ]
        if not measured:
            return self.PATH_PORTS[0]
        return min(measured)[1]

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        out_port = None

        if dpid == 1:
            if in_port == 1:
                # Host h1 -> select one s1-to-s2 link.
                out_port = self._choose_path()
                if self.selected_path != out_port:
                    self.selected_path = out_port
                    self.logger.info(
                        "Selected s1 path port %s; rates=%s",
                        out_port,
                        {
                            p: round(self.port_rates.get((1, p), 0), 1)
                            for p in self.PATH_PORTS
                        }
                    )
            elif in_port in self.PATH_PORTS:
                # Return traffic from s2 goes to h1.
                out_port = 1

        elif dpid == 2:
            if in_port == self.S2_HOST_PORT:
                # Host h2 -> s1 through one selected link.
                out_port = self._choose_path()
            elif in_port in (1, 2, 3):
                # Traffic from s1 -> host h2.
                out_port = self.S2_HOST_PORT

        if out_port is None or out_port == in_port:
            return

        actions = [parser.OFPActionOutput(out_port)]
        match = parser.OFPMatch(
            in_port=in_port,
            eth_src=eth.src,
            eth_dst=eth.dst
        )

        self.add_flow(dp, 10, match, actions,idle_timeout=0,hard_timeout=0)

        data = (
            None if msg.buffer_id != ofp.OFP_NO_BUFFER
            else msg.data
        )
        dp.send_msg(parser.OFPPacketOut(
            datapath=dp,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        ))
