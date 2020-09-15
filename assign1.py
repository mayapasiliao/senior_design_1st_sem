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
    container = list(nx.algorithms.dag.descendants(G,0))
    for x in range(1, M):
        if not x in container:
            return False
    else:
        return True

def checkconnection(G,M):
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

def distancefromMnodes(G,x,arr):
    nodedict = {}
    for y in arr:
        nodedict[y]=nx.shortest_path_length(G,x,y)
    return nodedict

def randomMtoMdistance(G,M,arr):
    sourcenode = rnd.randrange(0,M)
    print("M node:"+str(sourcenode))
    nodedict = {}
    for y in arr:
        if y != sourcenode:
            nodedict[y]=nx.shortest_path_length(G,sourcenode,y)
    print(nodedict)
    return nodedict
    return nodedict

def reduce_graph(G, M, draw = True):
    ''' G will be reduced to M-node,data server only, graph '''
    G = nx.minimum_spanning_tree(G) 
    pos = nx.get_node_attributes(G, 'pos')
    ctr = find_center_node(G)[0]
    G.nodes[ctr]['wrk'] = 'd-ctr'
    

    if draw:  # draw an original graph with a network center
        plt1 = plt.figure(figsize=(15, 15))
        colors = set_node_colors(G)

        # Check if node only occurs once in list of edges. If yes, remove edge
        node_count = len(G.nodes)
        edges = G.edges()
        connection_counts = {}

        # Creates a dictionary that lists all the nodes a node is connected to (no duplicates)
        for node in range(0, node_count):
            for edge in edges:
                if node == edge[0] and edge[0] not in range(0, M):
                    if node in connection_counts:
                        connection_counts[node] += [edge[1]]
                    else:
                        connection_counts[node] = [edge[1]]

        for elem in connection_counts.keys():
            if len(connection_counts[elem]) == 1:
                G.remove_edge(elem, connection_counts[elem][0])

        # for edge in edges:
        #     if edge[0] or edge[1] not in range(0, M):
        #         if edge[0] in connection_counts:
        #             connection_counts[edge[0]] += [edge[1]]
        #         else:
        #             connection_counts[edge[0]] = [edge[1]]
        
        # for elem in connection_counts.keys():
        #     if len(connection_counts[elem]) == 1:
        #         G.remove_edge(elem, connection_counts[elem][0])


                # if not checkconnection(G, M):
                #     G.add_edge(elem, connection_counts[elem])

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

simulation(200, 20, 0.125, 10, 100, 10, 10, True)
plt.show()
