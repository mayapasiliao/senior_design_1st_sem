from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib.packet import packet, ethernet


class Switch(app_manager.RyuApp):
    OFP_VERSIONS =[ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Switch, self).__init__(*args, **kwargs)
        self.MAC_table = {}

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp  = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        pkt = packet.Packet(msg.data)
        etherh = pkt.get_protocol(ethernet.ethernet)
        smac = etherh.src
        dmac = etherh.dst
        pin  = msg.match['in_port']
        swid = dp.id
        
        #Create the MAC table for swid
        self.MAC_table.setdefault(swid,{})

        #Learn Src. MAC
        self.MAC_table[swid][smac] = pin

        # MAC table lookup process
        if dmac in self.MAC_table[swid]:
            port_out = self.MAC_table[swid][dmac]
        else:
            port_out = ofp.OFPP_FLOOD

        # prepare and send PACKET-OUT
        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            data = msg.data  

        actions = [ofp_parser.OFPActionOutput(port_out)]
        out = ofp_parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, 
            in_port=pin, actions=actions, 
            data=data)
        dp.send_msg(out)

        # prepare and send FLOW MOD (add new enty to the OFS)
        inst = [ofp_parser.OFPInstructionActions(
            ofp.OFPIT_APPLY_ACTIONS, actions)]
        match = ofp_parser.OFPMatch(
            eth_dst=dmac, in_port=pin)
        
        mod = ofp_parser.OFPFlowMod(datapath=dp, 
        priority=1,match=match,instructions=inst)

        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def install_table_miss_flow(self, ev):
        msg = ev.msg
        dp  = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        #Prepare the Flow mod message
        actions = [ofp_parser.OFPActionOutput(
            ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        inst = [ofp_parser.OFPInstructionActions(
            ofp.OFPIT_APPLY_ACTIONS, actions)]
        
        mod = ofp_parser.OFPFlowMod(datapath=dp, 
        priority=0,instructions=inst)

        dp.send_msg(mod)