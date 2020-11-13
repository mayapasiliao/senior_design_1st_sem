from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3, ether
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
from ryu.lib import hub
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib.packet import packet, ethernet, arp, lldp, icmpv6
#
# NetworkX
# <Add code here>

class NetworkX(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    ##############################################################
    #
    def __init__(self, *args, **kwargs):
        super(NetworkX, self).__init__(*args, **kwargs)
        self.network_changed_thread = hub.spawn_after(1,None)
        #
        # NetworkX
        # <Add code here>

    ##############################################################
    # Handle PACKET-IN message
    #
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp  = msg.datapath

        pkt = packet.Packet(msg.data)
        etherh = pkt.get_protocol(ethernet.ethernet)    # Ethernet header
        smac = etherh.src                               # source MAC address
        dmac = etherh.dst                               # destination MAC address
        pin  = msg.match['in_port']                     # port in
        dpid = dp.id                                    # datapath id
        
        # ****
        # Ignore LLDP, ICMPv6 packets
        if pkt.get_protocol(lldp.lldp) or pkt.get_protocol(icmpv6.icmpv6):
            return
        
        print("\nOFC receives Packet-In message from Datapath ID of {}".format(dpid))

        # Learn source MAC address and port
        # NetworkX
        # <Add code here>
        
        print("\n   - DATA info: packet from {} to {}".format(smac,dmac))

        # Find best route
        # NetworkX
        # <Add code here>



    ##############################################################
    # Network Changed:
    #######################################
    # Switch is added
    @set_ev_cls(event.EventSwitchEnter)
    def handler_switch_enter(self, ev):
        print("Switch entering (Datapath ID = {}) ---------------".format(ev.switch.dp.id))
        hub.kill(self.network_changed_thread)
        self.network_changed_thread = hub.spawn_after(1,self.network_changed)
        
    #######################################
    # Switch is removed/unavailable
    @set_ev_cls(event.EventSwitchLeave)
    def handler_switch_leave(self, ev):
        print("Switch leaving (Datapath ID = {}) ---------------".format(ev.switch.dp.id))
        hub.kill(self.network_changed_thread)
        self.network_changed_thread = hub.spawn_after(1,self.network_changed)

    #######################################
    # Update the topology
    def network_changed(self):
        print("\nNetwork is changed-------------------------------")
        self.topo_raw_links = get_link(self, None)
        self.BuildTopology()

    def BuildTopology(self):
        # NetworkX
        # <Add code here>

        for l in self.topo_raw_links:
            _dpid_src = l.src.dpid
            _dpid_dst = l.dst.dpid
            _port_src = l.src.port_no
            _port_dst = l.dst.port_no
            
            # NetworkX
            # <Add code here>







    ##############################################################
    # Add action for "missing flow"
    #
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def action_for_missing_flow(self, ev):
        msg        = ev.msg
        dp         = msg.datapath
        ofp        = dp.ofproto
        ofp_parser = dp.ofproto_parser

        actions      = [ofp_parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        instructions = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        self.flow_add(dp, 0, 0, None, instructions)


    ##############################################################
    # Flow add/remove functions
    def flow_add(self, dp, idle_timeout, priority, match, instructions):
        ofp        = dp.ofproto
        ofp_parser = dp.ofproto_parser
        mod        = ofp_parser.OFPFlowMod(datapath=dp, command=ofp.OFPFC_ADD, 
                                            idle_timeout=idle_timeout, priority=priority, 
                                            
                                            match=match, instructions=instructions)
        if priority==0:
            in_port = "Any"
            eth_dst = "Any"
        else:
            in_port = match["in_port"]
            eth_dst = match["eth_dst"]
        #
        print("      + FlowMod (ADD) of Datapath ID={}, Match: (Dst. MAC={}, PortIn={}), Action: (PortOut={})".format(
            dp.id, eth_dst, in_port, instructions[0].actions[0].port))

        dp.send_msg(mod)

    def flow_rem(self, dp, match):
        ofp        = dp.ofproto
        ofp_parser = dp.ofproto_parser
        mod        = ofp_parser.OFPFlowMod(datapath=dp, command=ofp.OFPFC_DELETE, out_port=ofp.OFPP_ANY, out_group=ofp.OFPP_ANY, match=match)
        print("      + FlowMod (REMOVE) of Datapath ID={}, Match: (Dst. MAC={})".format(dp.id, match["eth_dst"]))
        dp.send_msg(mod)