# Network Simulation, Akira Kawaguchi (C) September 2020.
import random as rnd
import matplotlib.pyplot as plt
import networkx as nx
import csv

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

def reduce_graph(G, M, N, draw = True):
    ''' G will be reduced to M-node,data server only, graph '''
    pos = nx.get_node_attributes(G, 'pos')
    ctr = find_center_node(G)[0]
    G.nodes[ctr]['wrk'] = 'd-ctr'

    # realize a logic to reduce the network based on find MST
    G = nx.minimum_spanning_tree(G)

    all_nodes_list = list(G.nodes.data('wrk'))
    all_data_nodes = list() # Get all the red nodes.
    for node in all_nodes_list:
        if node[1] == 's':
            all_data_nodes.append(node)
    # Since we already computed ctr (yellow) above, we can add that to the list
    all_data_nodes.append((ctr, 'd-ctr'))
    all_data_nodes_length = len(all_data_nodes)

    # NOTE, we might be able to use just this: multi_source_dijkstra_path(G, sources) Find shortest weighted paths in G from a given set of source nodes.
    # NOTE this might not work because its returning to all nodes. WE only care about red nodes.
    # all_shortest_paths = multi_source_dijkstra_path_length

    # Out of all the methods, dijsktra's path seems to be the one of most fit.

    #Once we connect i to j, we don't need to connect j to i (Its already there)
    all_shortest_paths = list()
    for i in range (0, all_data_nodes_length):
        for j in range(i, all_data_nodes_length):
            shortest_path_i_j = nx.dijkstra_path(G, all_data_nodes[i][0], all_data_nodes[j][0])
            all_shortest_paths.append(shortest_path_i_j)

    nodes_in_new_graph = set()
    new_graph = nx.Graph()
    for path_of_nodes in all_shortest_paths:
        for node in path_of_nodes:
            # NOTE -- might not need this code anymore, but keeping her just cause.
            # Insert code for any other centers added.
            new_graph.add_node(node, wrk=G.nodes[node]['wrk'])
            nodes_in_new_graph.add(node)
            # print(node)
            # print(G.nodes[node]['wrk'])

    #Generate all edge pairs between red + shortest paths.
    # remove all edge pairs from current graph
        # we can create a copy: nx.create_empty_copy(G, with_data=True)
    new_graph_2 = nx.create_empty_copy(G)
    # add in "new" edge pairs.
    for path_of_nodes in all_shortest_paths:
        if len(path_of_nodes) > 1: #ie only save pathed nodes, cause we have list of just single red.
            for i in range (0, len(path_of_nodes)-1): #Notice we stop one before because we are connecting i to i+1
                new_graph_2.add_edge(path_of_nodes[i], path_of_nodes[i+1])

    # Get center of reduced graph
    temp_graph = new_graph_2.copy()
    temp_nodes = list(temp_graph.nodes)

    # If node is not connected to any other node, remove it from graph
    # Need to do this to be able to use find_center_node
    for node in temp_nodes:
        if temp_graph.degree[node] == 0:
            temp_graph.remove_node(node)

    mst_ctr = find_center_node(temp_graph)[0]
    new_graph_2.nodes[mst_ctr]['wrk'] = 'r-ctr'

    # #nodes_in_new_graph.sort()
    # # ### NOTE, this changes the type to a list
    # # nodes_in_new_graph = sorted(nodes_in_new_graph)
    # print(nodes_in_new_graph)
    # for i in range (0, N):
    #     if i not in nodes_in_new_graph:
    #         new_graph.add_node(i, wrk=G.nodes[i]['wrk'])

    # # After adding the nodes, we must add the edges.
    # for path_of_nodes in all_shortest_paths:
    #     if len(path_of_nodes) > 1: #ie only save pathed nodes, cause we have list of just single red.
    #         for i in range (0, len(path_of_nodes)-1): #Notice we stop one before because we are connecting i to i+1
    #             new_graph.add_edge(path_of_nodes[i], path_of_nodes[i+1])

    # # We are still mising the white nodes not in the path, and thus need to figure out which those are and add them.
    # G=new_graph

    G = new_graph_2

    weighted_edge_M_pairs = list()
    for shortest_path_i in all_shortest_paths:
        if len(shortest_path_i) > 1:
            i = 1
            red_found = False
            while not red_found:
                ## Insert logic for any center nodes added.  
                if G.nodes[shortest_path_i[i]]['wrk'] == 's' or G.nodes[shortest_path_i[i]]['wrk'] == 'd-ctr' or G.nodes[shortest_path_i[i]]['wrk'] == 'r-ctr':
                    red_found = True
                    # print(i)
                    # print(shortest_path_i[i])
                else:
                    i += 1
            weighted_edge_M_pairs.append((shortest_path_i[0], shortest_path_i[i], i))
     
    print(weighted_edge_M_pairs)

    # New graph with M connected nodes only, as well as weights added in.
    m_node_graph = nx.create_empty_copy(G)
    for weighted_edge_M_pair in weighted_edge_M_pairs:
        m_node_graph.add_edge(weighted_edge_M_pair[0], weighted_edge_M_pair[1], weight=weighted_edge_M_pair[2])
    # Added this as a policy to ensure we always get MST
    m_node_graph = nx.minimum_spanning_tree(m_node_graph)
    
    

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

        plt2 = plt.figure(figsize=(15, 15))
        colors = set_node_colors(m_node_graph)
        nx.draw_networkx_nodes(m_node_graph, pos, node_size = 160,
                               node_color = colors, edgecolors = 'gray',
                               cmap = plt.cm.Reds_r)
        labels = nx.get_edge_attributes(m_node_graph,'weight')
        # formatted_labels = {}
        # for label in labels:
        #     formatted_labels[label]=  "weight: "+str(label[1])
        nx.draw_networkx_edge_labels(m_node_graph,pos,edge_labels=labels)
        nx.draw_networkx_edges(m_node_graph,pos)
        labels = {}
        for n in range(m_node_graph.order()): labels[n] = str(n)
        nx.draw_networkx_labels(m_node_graph, pos, labels, font_size = 10)
    
    if draw:
        plt.xlim(-0.05, 1.05)
        plt.ylim(-0.05, 1.05)
        # plt.axis('off')
        plt.show(block = False)
    return G

def testremoval(G,M,X,Y):
    '''Tests to see if M nodes are reachable by node 0 after removing an edge.'''
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
    '''Checks if M nodes are reachable by node 0.'''
    print("reachable by 0: "+str(nx.algorithms.dag.descendants(G,0)))
    container = list(nx.algorithms.dag.descendants(G,0))
    for x in range(1, M):
        if not x in container:
            return False
    else:
        return True

def furthestfromMnodes(G,M,arr):
    '''Returns the sum of distances between the node furthest from all M nodes and the M nodes themselves.'''
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
    '''Returns the sum of distances between node x and all nodes in the array arr.'''
    distance = 0
    for y in arr:
        distance+=nx.shortest_path_length(G,x,y)
    return distance

def randomMtoMdistance(G,M,arr):
    '''Returns the sum of distances between a randomly selected M node and all other M nodes.'''
    sourcenode = rnd.randrange(0,M)
    distance = 0
    for y in arr:
        if y != sourcenode:
            distance+=nx.shortest_path_length(G,sourcenode,y)
    return distance

def closestMtoMdistance(G,M,arr):
    '''Returns the sum of distances between the closest M node to all other M nodes
    and all other M nodes.'''
    nodedict = {}
    for x in range(0,M):
        sum = 0
        for y in arr:
            sum +=nx.shortest_path_length(G,x,y)
        nodedict[x] = sum
    lowest = 0
    for x in range(0,M):
        if nodedict[x]<nodedict[lowest]:
            lowest = x
    return distancefromnodes(G,lowest,arr)

# def reduce_all_ones(G):
#     non_red_nodes = list(G.nodes.data('wrk'))
#     print(non_red_nodes)

def simulation(N, M, D, d_min, d_max, d_M, round_per_graph, draw = False):
    ''' N is a total number of node, M is a server node, D is a RGG's distance
    parameter, a uniform [d_max, d_min] is a generated data size to exchange,
    d_M is the number of data generating servres, round_per_graph is the
    number of iterations per a generated graph, and draw is to decide if the
    graph is gerated or not. '''
    print("-- (N, M) = (" + str(N) + ", " + str(M) + ")", "D =", D,
          "data =[" + str(d_min) + " ," + str(d_max) + "]",
          "Data Senders =", d_M, "Per Graph =", round_per_graph)
    # rnd.seed(999)
    G = generate_graph(N, M, D)
    G = reduce_graph(G, M, N, draw) ##NOTE added N parameter to help simplify adding missing white nodes.
    # rest is your work...

def iteration(N, M, D, d_min, d_max, d_M, round_per_graph):
    ''' N is a total number of node, M is a server node, D is a RGG's distance
    parameter, a uniform [d_max, d_min] is a generated data size to exchange, 
    d_M is the number of data generating servres, round_per_graph is the 
    number of iterations per a generated graph, and draw is to decide if the 
    graph is gerated or not. This is a variation of the above simulation meant 
    to analyze the graph created. Four analysis functions are used 10 times to gain
    the correct answer to the experimental set.''' 
    print("-- (N, M) = (" + str(N) + ", " + str(M) + ")", "D =", D,
          "data =[" + str(d_min) + " ," + str(d_max) + "]",
          "Data Senders =", d_M, "Per Graph =", round_per_graph)
    answerlist = [[0 for i in range(6)] for j in range(10)]
    G = generate_graph(N, M, D)
    G = reduce_graph(G, M, False)
    for i in range(10):
        arr = list(range(M))
        arr = rnd.sample(arr,int(d_M))
        answerlist[i][5] = N
        answerlist[i][4] = M
        answerlist[i][0] = distancefromnodes(G,furthestfromMnodes(G,M,arr),arr)
        answerlist[i][1] = randomMtoMdistance(G,M,arr)
        answerlist[i][2] = distancefromnodes(G,find_center_node(G)[0],arr)
        answerlist[i][3] = closestMtoMdistance(G,M,arr)
    return answerlist
        
def assignment():
    '''Runs the above iteration code 10 x 10 x 4 times of different variations. Answers returned are added to an array,
    which is then written to a csv as the answer.'''
    answerlist = [[0 for col in range(10)] for row in range(40)]
    for x in range(0,10):
        M = rnd.randrange(1,11)*10
        answerlist[x]=iteration(200, M, 0.125, 10, 100, M, 10)
    for x in range(10,20):
        M = rnd.randrange(1,11)*10
        answerlist[x]=iteration(200, M, 0.125, 10, 100, M/2, 10)
    for x in range(20,30):
        M = rnd.randrange(1,6)*50
        answerlist[x]=iteration(500, M, 0.125, 10, 100, M/4, 10)
    for x in range(30,40):
        M = rnd.randrange(1,6)*40
        answerlist[x]=iteration(400, M, 0.125, 10, 100, M, 10)
    with open('answerfile.csv', mode='w') as answer_file:
        answerwriter = csv.writer(answer_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for j in range(len(answerlist)):
            for k in range(len(answerlist[j])):
                answerwriter.writerow(answerlist[j][k])


    
simulation(200, 20, 0.125, 10, 100, 10, 10, True)
plt.show()

