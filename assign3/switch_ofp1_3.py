from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3, ether
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib.packet import packet, ethernet, arp
from ryu.app.ofctl.api import get_datapath
from ryu.topology.api import get_switch, get_link
from ryu.topology import event
from ryu.lib import hub, mac

class Switch(app_manager.RyuApp):
    OFP_VERSIONS =[ofproto_v1_3.OFP_VERSION]

    
    
    def __init__(self, *args, **kwargs):
        super(Switch, self).__init__(*args, **kwargs)
        self.MAC_table = {}
        # for assignment 2
        # ARP_table[IP] = MAC
        self.ARP_table = {}
        self.shortest_paths = {}
        self.switches = {}

    def remove_MAC(self, mac):
        for key in self.MAC_table:
            self.MAC_table.pop(mac)


        
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

        #Learn Src. MAC, avoid flood
        self.MAC_table[swid][smac] = pin

        # 2.2: For arp
        if (pkt.get_protocol(arp.arp)):
            # arptable[ip] = mac
            arp_pkt = pkt.get_protocol(arp.arp)
            #if arp_pkt.dst_mac == dmac:
            if arp_pkt.src_ip not in self.ARP_table:
                #print('Adding dest mac to arp table...', arp_pkt.dst_ip, dmac, smac, pin, swid)
                self.ARP_table[arp_pkt.src_ip] = smac


        # if dest MAC is already avail, figure out which port to output
        # otherwise flood, but dont flood?
        if dmac in self.MAC_table[swid]:
            port_out = self.MAC_table[swid][dmac]
        else:
            if self.arp_handler(msg):
                return
            else:
                # disabling flooding?
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

        if port_out != ofp.OFPP_FLOOD:
            dp.send_msg(out)

        # 1.1: idle_timeout: 10s for our flowmod
        inst = [ofp_parser.OFPInstructionActions(
            ofp.OFPIT_APPLY_ACTIONS, actions)]
        match = ofp_parser.OFPMatch(
            eth_dst=dmac, in_port=pin)
        
        mod = ofp_parser.OFPFlowMod(datapath=dp, idle_timeout=10,
        priority=1,match=match,instructions=inst)

        if port_out != ofp.OFPP_FLOOD:
            dp.send_msg(mod)


    def arp_handler(self, msg):
        dp = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        port_in = msg.match['in_port']
        swid = dp.id
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        arp_pkt = pkt.get_protocol(arp.arp)
        
        if eth:
            eth_dst = eth.dst
            eth_src = eth.src

        # avoid forward in network
        if eth_dst == mac.BROADCAST_STR and arp_pkt:
            arp_dst_ip = arp_pkt.dst_ip

            if (dp.id, eth_src, arp_dst_ip) in self.switches:
                if self.switches[(dp.id, eth_src, arp_dst_ip)] != port_in:
                    dp.send_packet_out(in_port=port_in, actions=[])
                    return True
            else:
                self.switches[(dp.id, eth_src, arp_dst_ip)] = port_in

        if arp_pkt:
            hwtype = arp_pkt.hwtype
            proto = arp_pkt.proto
            hlen = arp_pkt.hlen
            plen = arp_pkt.plen
            opcode = arp_pkt.opcode
            arp_src_ip = arp_pkt.src_ip
            arp_dst_ip = arp_pkt.dst_ip
            if opcode == arp.ARP_REQUEST:
                # print(arp_dst_ip, eth.dst)
                # print(self.ARP_table)
                if arp_dst_ip in self.ARP_table:
                    ARP_Reply = packet.Packet()
                    # print(eth_src, self.ARP_table[arp_dst_ip], arp_dst_ip, arp_src_ip)
                    ARP_Reply.add_protocol(ethernet.ethernet(
                        ethertype=ether.ETH_TYPE_ARP,
                        dst=eth_src,
                        src=self.ARP_table[arp_dst_ip]))
                    ARP_Reply.add_protocol(arp.arp(
                        hwtype=hwtype,
                        proto=proto,
                        hlen=hlen,
                        plen=plen,
                        opcode=arp.ARP_REPLY,
                        src_mac=self.ARP_table[arp_dst_ip],
                        src_ip=arp_dst_ip,
                        dst_mac=eth_src,
                        dst_ip=arp_src_ip))

                    ARP_Reply.serialize()
                    port_out = self.MAC_table[swid][eth_src]
                    
                    out = ofp_parser.OFPPacketOut(
                        datapath=dp,
                        buffer_id=0xffffffff,
                        in_port=ofp.OFPP_CONTROLLER,
                        actions=[ofp_parser.OFPActionOutput(port_out, 0)],
                        data=ARP_Reply.data)
                    dp.send_msg(out)
                    return True
                    
        return False

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

    def remove_flow(self, datapath, match):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        mod = ofp_parser.OFPFlowMod(datapath=datapath, command=ofp.OFPFC_DELETE, out_port=ofp.OFPP_ANY,
                                    out_group=ofp.OFPP_ANY, match=match)
        print('Removed flow of datapath id: {}, match: dest MAC: {}'.format(datapath.id, match['eth_dst']))
        datapath.send_msg(mod)
        
    # a simple get dict key by value function
    def get_MAC(self, table, port):
        for key in table:
            if table[key] == port:
                return key
        return None

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        swid = dp.id
        port = msg.desc
        
        if port.state == ofp.OFPPS_LINK_DOWN:
            # 1.2 : host removed from network; update mac table
            bad_MAC = self.get_MAC(self.MAC_table[swid], port.port_no)
            if bad_MAC != None:
                self.MAC_table[swid].pop(bad_MAC)
                print('Removed from MAC table: MAC: {}'.format(bad_MAC))
            
            # 1.3: all flow entries related to that host should be removed;
            match = ofp_parser.OFPMatch(eth_dst=bad_MAC)
            dp_list = get_datapath(self, None)
            for dp_item in dp_list:
                self.remove_flow(dp_item, match)
                
        # triggering the test with deleting a host
        # print('Shortest paths test: ', self.get_shortest_paths())
        
    # 2.1 : Find best routes between all pairs of OFS:
    def get_shortest_paths(self):
        topo_raw_switches = get_switch(self, None)
        topo_raw_links = get_link(self, None)

        links = {}
        for switch in topo_raw_switches:
            links[switch.dp.id] = []
        
        for link in topo_raw_links:
            # link.src.dpid, link.dst.dpid
            if link.dst.dpid not in links[link.src.dpid]:
                links[link.src.dpid].append(link.dst.dpid)
            if link.src.dpid not in links[link.dst.dpid]:
                links[link.dst.dpid].append(link.src.dpid)
        switches = [switch.dp.id for switch in topo_raw_switches]
        
        for i in switches: 
            self.shortest_paths[i] = {}
        for i in switches:
            for j in switches:
                if i != j:
                    self.get_shortest_path(i, j, links)

        return self.shortest_paths
        
          
    # 2.1 : Find best route between pair of OFS:
    def get_shortest_path(self, swid1, swid2, links):
        '''return the shortest path from swid1 to swid2. '''

        # exit early + get saved data if it already exists
        if swid2 in self.shortest_paths[swid1]:
            return self.shortest_paths[swid1][swid2]

        visited = []
        queue = [[swid1]]
        while len(queue) > 0:
            path = queue.pop(0)
            swid = path[-1]
            if swid not in visited:
                neighbors = links[swid]
                for neighbor in neighbors:
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)
                    if neighbor == swid2:
                        self.shortest_paths[swid1][swid2] = new_path
                        self.shortest_paths[swid2][swid1] = new_path[::-1]
                        return new_path
                visited.append(swid)
        print ('Unable to find path from swid {} to swid {}'.format(swid1, swid2))
        return None

        
        
