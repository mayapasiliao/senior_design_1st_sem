# Network Simulation, Akira Kawaguchi (C) September 2020.
import random as rnd
import matplotlib.pyplot as plt
import networkx as nx

def merge_disconnected_components(G):
    ''' If G has separated connected components, they must be merged to avoid
    gaining an incorrect result from shortest path computations. '''
    ccs = list(nx.connected_components(G))
    for i in range(len(ccs)):       # visit each connected component
        if i is 0: continue
        cc1 = list(ccs[i - 1])
        cc2 = list(ccs[i])
        rnd.shuffle(cc1)            # shuffle nodes in the current component
        rnd.shuffle(cc2)            # shuffle nodes in the previous component
        G.add_edge(cc1[-1], cc2[0]) # add an edge to connect two.
        print("   DEBUG: merging two isolated connected components...")
    assert nx.number_connected_components(G) is 1, "<FATAL> merge_disconnected_components()"
    return G

def generate_graph(N, M, D):
    ''' G is generated of a collection of nodes of N in x-pos in [0, 1.0)
    and y-pos [0, 1.0) in which N is a total number of nodes, M is a
    total number of servers, and D is a distance of connecting two
    nodes. This returns a weighted version of a generated graph that
    must have paths among M-nodes; each node has a pos-attirbute for a
    node genmetric location and svc-attribute for the role of a node
    where the value should be either of 'd' for a data holder, 'd-ctr' for
    a data hoder center, 's' for a server, 's-ctr' for a server center, and
    for a server ceter, and 'r-ctr' for a reduced graph for data servers. '''
    G = merge_disconnected_components(nx.random_geometric_graph(N, D))
    wrks = {}  # node work status
    for i in range(N):
        wrks[i] = 's' if i < M else 'd'
    nx.set_node_attributes(G, wrks, 'wrk')
    # for i in range(G.order()): print(G.nodes[i])
    return G

def find_center_node(G):
    ''' Given undirected graph G, apply Floyd Warshall for all nodes to find a
    center node which has the smallest maximum distance. '''
    assert nx.number_connected_components(G) is 1, "<FATAL> find_center_node()"
    paths = nx.floyd_warshall(G)
    matrx = {src:dict(tgt) for src, tgt in paths.items()}
    # print("   DEBUG:", matrx)
    center = [-1, -1]
    for src, tgt in matrx.items():
        cn = src               # pick a candidate node
        md = max(tgt.values()) # max distance in the dict
        if md <= 0: continue
        if md <= center[1] or center[1] < 0: center = [cn, md]
    assert(center[0] != -1 and center[1] !=-1), "<FATAL> find_center_node()"
    # print("   DEBUG: center(node, max-distance) = :", center)
    return center

def set_node_colors(G):
    ''' Among the ncount of nodes, hcount hosts are colored red, center is
    colored gold and others are colored white, and returns the color list. '''
    colors = []
    for i in range(G.order()):
        role = G.nodes[i]['wrk']
        if   role == 'd': colors.append('white')         # no data node
        elif role == 'd-ctr': colors.append('yellow')    # graph center 
        elif role == 's': colors.append('red')           # data node
        elif role == 's-ctr': colors.append('skyblue')   # subgraph center
        elif role == 'r-ctr': colors.append('blue')      # reduced graph center
        else: assert(False), "<FATAL> node role attribute not found!"
    # print("Length =", len(colors), colors)
    return colors

def testremoval(G,M,X,Y):
    G.remove_edge(X,Y)
    print(str(X)+" "+str(Y) + "removed")
    print("reachable by 0: "+str(nx.algorithms.dag.descendants(G,0)))
    container = list(nx.algorithms.dag.descendants(G,0))
    for x in range(1, M):
        if not x in container:
            return False
    else:
        return True

def checkconnection(G,M):
    print("reachable by 0: "+str(nx.algorithms.dag.descendants(G,0)))
    container = list(nx.algorithms.dag.descendants(G,0))
    for x in range(1, M):
        if not x in container:
            return False
    else:
        return True

def furthestfromMnodes(G,M,arr):
    nodedict = {}
    for x in range(M, len(G)):
        sum = 0
        for y in arr:
            sum +=nx.shortest_path_length(G,x,y)
        nodedict[x] = sum
    highest = M
    for x in range(M, len(G)):
        if nodedict[x]>nodedict[highest]:
            highest = x
    return highest

def distancefromnodes(G,x,arr):
    nodedict = {}
    for y in arr:
        nodedict[y]=nx.shortest_path_length(G,x,y)
    return nodedict

def randomMtoMdistance(G,M,arr):
    sourcenode = rnd.randrange(0,M)
    distance = 0
    for y in arr:
        if y != sourcenode:
            distance+=nx.shortest_path_length(G,sourcenode,y)
    return distance

def closestMtoMdistance(G,M,arr):
    nodedict = {}
    for x in range(0,M):
        sum = 0
        for y in arr:
            sum +=nx.shortest_path_length(G,x,y)
        nodedict[x] = sum
    lowest = M
    for x in range(0,M):
        if nodedict[x]<nodedict[lowest]:
            lowest = x
    return distancefromnodes(G,lowest,arr)


def reduce_graph(G, M, draw = True):
    ''' G will be reduced to M-node,data server only, graph '''
    G = nx.minimum_spanning_tree(G)
    ctr = find_center_node(G)[0]
    G.nodes[ctr]['wrk'] = 'd-ctr'
    pos = nx.get_node_attributes(G, 'pos')

    if draw:  # draw an original graph with a network center
        plt1 = plt.figure(figsize=(15, 15))
        colors = set_node_colors(G)
        nx.draw_networkx_nodes(G, pos, node_size = 160,
                               node_color = colors, edgecolors = 'gray',
                               cmap = plt.cm.Reds_r)
        nx.draw_networkx_edges(G, pos, alpha = 0.2)
        labels = {}
        for n in range(G.order()): labels[n] = str(n)
        nx.draw_networkx_labels(G, pos, labels, font_size = 10)

    # realize a logic to reduce the network based on find MST
    
    if draw:
        plt.xlim(-0.05, 1.05)
        plt.ylim(-0.05, 1.05)
        # plt.axis('off')
        plt.show(block = False)
    return G 


def simulation(N, M, D, d_min, d_max, d_M, round_per_graph, draw = False):
    ''' N is a total number of node, M is a server node, D is a RGG's distance
    parameter, a uniform [d_max, d_min] is a generated data size to exchange, 
    d_M is the number of data generating servres, round_per_graph is the 
    number of iterations per a generated graph, and drwa is to decide if the 
    graph is gerated or not. ''' 
    print("-- (N, M) = (" + str(N) + ", " + str(M) + ")", "D =", D,
          "data =[" + str(d_min) + " ," + str(d_max) + "]",
          "Data Senders =", d_M, "Per Graph =", round_per_graph)
    # rnd.seed(999)
    G = generate_graph(N, M, D)
    G = reduce_graph(G, M, draw)
    # rest is your work...
    
def iteration(N, M, D, d_min, d_max, d_M, round_per_graph, draw = False):
    ''' N is a total number of node, M is a server node, D is a RGG's distance
    parameter, a uniform [d_max, d_min] is a generated data size to exchange, 
    d_M is the number of data generating servres, round_per_graph is the 
    number of iterations per a generated graph, and drwa is to decide if the 
    graph is gerated or not. ''' 
    print("-- (N, M) = (" + str(N) + ", " + str(M) + ")", "D =", D,
          "data =[" + str(d_min) + " ," + str(d_max) + "]",
          "Data Senders =", d_M, "Per Graph =", round_per_graph)
    answerlist = [[0 for i in range(5)] for j in range(10)]
    G = generate_graph(N, M, D)
    G = reduce_graph(G, M)
    for i in range(10):
        arr = list(range(M))
        arr = rnd.sample(arr,int(d_M))
        answerlist[i][4] = M
        print("Furthest node from M nodes total distance: " + str(distancefromMnodes(G,furthestfromMnodes(G,M,arr),arr)))
        answerlist[i][0] = distancefromMnodes(G,furthestfromMnodes(G,M,arr),arr) * 10
        print("Random M node from other M nodes total distance: "+str(randomMtoMdistance(G,M,arr)))
        answerlist[i][1] = randomMtoMdistance(G,M,arr) * 10
        print("Central node from other M node total distance: "+str(distancefromMnodes(G,find_center_node(G)[0],arr)))
        answerlist[i][2] = distancefromnodes(G,find_center_node(G)[0],arr))
        print("Closest M node from other M nodes total distance: "+str(closestMtoMdistance(G,M,arr)))
        answerlist[i][3] = closestMtoMdistance(G,M,arr))
    return answerlist
        
def assignment(draw):
    answerlist = [[0 for col in range(10)] for row in range(4)]
    for x in range(0,10):
        M = rnd.randrange(1,11)*10
        answerlist[0]=iteration(200, M, 0.125, 10, 100, M, 10, True)
    for x in range(10,20):
        M = rnd.randrange(1,11)*10
        answerlist[1]=iteration(200, M, 0.125, 10, 100, M/2, 10, True)
    for x in range(20,30):
        M = rnd.randrange(1,6)*50
        answerlist[2]=iteration(500, M, 0.125, 10, 100, M/4, 10, True)
    for x in range(30,40):
        M = rnd.randrange(1,10)*5
        answerlist[3]=iteration(200, M, 0.125, 10, 100, M, 10, True)
    if draw:  # draw an original graph with a network center
        plt1 = plt.figure(figsize=(15, 15))
        colors = set_node_colors(G)
        nx.draw_networkx_nodes(G, pos, node_size = 160,
                               node_color = colors, edgecolors = 'gray',
                               cmap = plt.cm.Reds_r)
        nx.draw_networkx_edges(G, pos, alpha = 0.2)
        labels = {}
        for n in range(G.order()): labels[n] = str(n)
        nx.draw_networkx_labels(G, pos, labels, font_size = 10)

    # realize a logic to reduce the network based on find MST
    
    if draw:
        plt.xlim(-0.05, 1.05)
        plt.ylim(-0.05, 1.05)
        # plt.axis('off')
        plt.show(block = False)
simulation(200, 20, 0.125, 10, 100, 20, 10, True)
plt.show()


