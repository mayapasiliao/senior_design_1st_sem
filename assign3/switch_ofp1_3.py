from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib.packet import packet, ethernet
from ryu.app.ofctl.api import get_datapath

class Switch(app_manager.RyuApp):
    OFP_VERSIONS =[ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Switch, self).__init__(*args, **kwargs)
        self.MAC_table = {}
        # for assignment 2
        self.ARP_table = {}
        self.shortest_paths = {}

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
        # 1.1: here is match, idle_timeout: 10s. (1/23 on ryudocs)
        # we put into mod=OFPFlowMod(..., idle_timeout=10, ...)
        inst = [ofp_parser.OFPInstructionActions(
            ofp.OFPIT_APPLY_ACTIONS, actions)]
        match = ofp_parser.OFPMatch(
            eth_dst=dmac, in_port=pin)
        
        mod = ofp_parser.OFPFlowMod(datapath=dp, idle_timeout=10,
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

    # a simple get dict key by value function
    def get_MAC(self, table, port):
        for key in table:
            if table[key] == port:
                return key
        return None

    # 1.2 : host removed from network; update mac table
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_hander(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        swid = dp.id
        port = msg.desc

        print('Port state: {}'.format(port.state))
        
        if port.state == ofp.OFPPS_LINK_DOWN:
            # remove invalid entries here from MAC address table
            bad_MAC = self.get_MAC(self.MAC_table[swid], port.port_no)
            if bad_MAC != None:
                self.MAC_table[swid].pop(bad_MAC)
                print('Removed from MAC table: DEST MAC: {}'.format(bad_MAC))
            
            # 1.3: 
            # all flow entries related to that host should be removed;
            # hint: OFPFC_DELETE
            match = ofp_parser.OFPMatch(eth_dst=bad_MAC)
            dp_list = get_datapath(self, None)
            for dp_item in dp_list:                
                mod = ofp_parser.OFPFlowMod(datapath=dp_item, command=ofp.OFPFC_DELETE, out_port=ofp.OFPP_ANY,
                                            out_group=ofp.OFPP_ANY, match=match)
                print('Removed flow of datapath id: {}, match: dest MAC: {}'.format(dp_item.id, match['eth_dst']))
                dp_item.send_msg(mod)
                
        # print('shortest path test: ', self.get_shortest_path(1,2))
                
    # 2.1 : Find best route between pair of OFS:
    def get_shortest_path(self, swid1, swid2):
        '''return the shortest path from swid1 to swid2. '''

        # we will probably want to use dynamic programming and save the shortest path.
        # note shortest_path of swid1 -> swid2 is the reverse of swid2 -> swid1

        # get saved shortest path. current commented out due to issues with integer keys for dict
        # if swid1 in self.shortest_paths and swid2 in self.shortest_paths[swid1]:
            # return self.shortest_paths[swid1][swid2]

        # apply BFS to determine shortest path
        end_MAC = self.get_MAC(self.MAC_table[swid2], 1)
        # queue contains all paths
        queue = [[swid1]]
        dp_list = get_datapath(self, None)
        # list of available swids in the network
        swids = [dp_item.id for dp_item in dp_list]
        # a dict to translate MACs->swids
        MACs = {}
        for swid in swids:
            MACs[self.get_MAC(self.MAC_table[swid], 1)] = swid
        visited = []
        while len(queue) > 0:
            path = queue.pop(0)
            swid = path[-1]
            if swid not in visited:
                neighbors = self.MAC_table[swid]
                for neighbor in neighbors:
                    # skip non-switch
                    if neighbor not in MACs:
                        continue
                    neighbor_id = MACs[neighbor]
                    new_path = list(path)
                    new_path.append(neighbor_id)
                    queue.append(new_path)
                    if neighbor_id == swid2:
                        # save shortest paths
                        # some issue with int key for dict, remove cache thing for now
                        # self.shortest_paths[swid1][swid2] = new_path
                        # self.shortest_paths[swid2][swid1] = list(new_path).reverse()
                        return new_path
                visited.append(swid)
        print('MAC table: ', self.MAC_table)
        print ('Unable to find path from swid {} to swid {}'.format(swid1, swid2))
        
