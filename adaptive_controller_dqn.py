import os
import numpy as np
import torch

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import (
    CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
)
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet, ether_types
from os_ken.lib import hub
from main import DQN


class AdaptiveController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    PATH_PORTS = (2, 3, 4)
    S2_HOST_PORT = 1
    CAPACITIES = np.array([100.0, 140.0, 120.0])
    BASE_DELAYS = np.array([10.0, 18.0, 14.0])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.datapaths = {}
        self.port_bytes = {}
        self.port_rates = {}
        self.selected_path = None

        self.model = DQN(state_size=6, action_size=3)
        model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "dqn_model.pth"
        )
        self.model.load_state_dict(
            torch.load(model_path, map_location="cpu", weights_only=True)
        )
        self.model.eval()
        self.logger.info("DQN model loaded from %s", model_path)

        self.monitor_thread = hub.spawn(self._monitor)

    def add_flow(self, dp, priority, match, actions,
                 idle_timeout=0, hard_timeout=0):
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

        self.add_flow(
            dp, 0, parser.OFPMatch(),
            [parser.OFPActionOutput(
                ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER
            )]
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
        # Port rates are live measurements. Convert them into a
        # relative-load proxy for the simulator-trained DQN.
        rates = np.array([
            self.port_rates.get((1, p), 0.0)
            for p in self.PATH_PORTS
        ], dtype=np.float32)

        max_rate = max(float(np.max(rates)), 1.0)
        utilization = np.clip(
            (rates / max_rate) * 0.8, 0.0, 1.2
        )

        delays = self.BASE_DELAYS * (
            1.0 + 3.0 * np.maximum(utilization - 0.5, 0.0)
        )

        state = np.concatenate([
            utilization,
            delays / 50.0
        ]).astype(np.float32)

        with torch.no_grad():
            q_values = self.model(
                torch.from_numpy(state).unsqueeze(0)
            )
            action = int(torch.argmax(q_values, dim=1).item())

        port = self.PATH_PORTS[action]
        self.selected_path = port
        self.logger.info(
            "DQN chose port %s; Q=%s; rates=%s; state=%s",
            port,
            q_values.numpy().round(3).tolist()[0],
            rates.round(1).tolist(),
            state.round(3).tolist()
        )
        return port

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match["in_port"]
        self.logger.info("PACKET IN: switch=%s port=%s", dpid, in_port)

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        out_port = None

        if dpid == 1:
            if in_port == 1:
                out_port = self._choose_path()
            elif in_port in self.PATH_PORTS:
                out_port = 1

        elif dpid == 2:
            if in_port == self.S2_HOST_PORT:
                out_port = self.selected_path or self.PATH_PORTS[0]
            elif in_port in self.PATH_PORTS:
                out_port = self.S2_HOST_PORT

        if out_port is None or out_port == in_port:
            return

        actions = [parser.OFPActionOutput(out_port)]
        match = parser.OFPMatch(
            in_port=in_port,
            eth_src=eth.src,
            eth_dst=eth.dst
        )

        self.add_flow(dp, 10, match, actions, idle_timeout=60, hard_timeout=120)
        self.logger.info("FLOW REQUEST: switch=%s in_port=%s out_port=%s", dpid, in_port, out_port)

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
