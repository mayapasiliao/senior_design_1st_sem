# RYU stuff:  
======  
## Need to have 3 ssh sessions open to code/debug in RYU:  
======  
#### terminal 1:  
`sudo mn --topo linear,3,1 --switch ovsk --controller remote --mac`  
our basic mininet command to create a "virtual", "pseudo", "mock" network, whatever is easier to visualize  
  
`h1 ifconfig h1-eth0 down`  
for exercise 1a, we want to bring one of the host computers down  
our switch.py file will catch any changes + react accordingly (change MAC addr tables)  
  
#### terminal 2:  
`sudo ryu-manager ~/hw3/switch_ofp1_3.py --observe-links`  
basically just runs our switch.py file.  
this switch.py file will be able to hook onto the mininet application running on terminal 1,  
and be able to modify/have access to the virtual mininet network by coding in python + ryu.  
any `print()` statements from python will log to this console, as well as any ryu output  

#### terminal 3:  
`sudo ovs-ofctl dump-flows s1`  
this tells s1(switch1) to dump all of the network packets in the flow table into the console.  
basically the switch in mininet network will have logged the entire history of network packets  
going through the switch (unless specified idle timeout).  
  
#### terminology:  
OF, openflow  
OFS, openflow switch  
flow/flow entry/flow match, just a packet in the mininet/OF network  
flow table,  just a table mininet/openflow has to keep track of all the packets  
host, some designated computer  
switch, a computer/access point in the network that reads the flow of the packets (with ryu/python)  
controller, a computer/access point that works with the switch to modify the flow of packets  
  
  
link to API documentation:  
https://ryu.readthedocs.io/en/latest/ofproto_v1_3_ref.html#port-structures  
basically ctrl+f anything that seems to be an object of ofp class  
i.e OFPFlow_Mod, OFPMatch, OFPFC_DELETE, etc  
  
generally the pattern of ryu is:  
`dp = msg.datapath #basically the object/reference of the switch/host/cpu that it refers to`  
`match = OFPMatch(...) #if we want to query/match certain items `  
`mod = OFPFlowMod(...) #any modifications to do `  
`dp.send_msg(mod) #this tells the switch/host/cpu that dp refers to, to make modifications`  