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

    ## Generate the random M nodes.
    random_M_positions = rnd.sample(range(1, N), M) # https://stackoverflow.com/questions/22842289/generate-n-unique-random-numbers-within-a-range

    for i in range(N):
        wrks[i] = 's' if i in random_M_positions else 'd' ## This line of code places d if in random_M_positions
    nx.set_node_attributes(G, wrks, 'wrk')
    # for i in range(G.order()): print(G.nodes[i])

    
    # Originally was going to create a list using map and pull out G nodes to map, however lambda can be argumentally used!
    #Relabeling: https://networkx.org/documentation/stable/reference/generated/networkx.relabel.relabel_nodes.html
    #Converting to binary: https://stackoverflow.com/questions/10411085/converting-integer-to-binary-in-python
    #mapping: https://www.geeksforgeeks.org/python-map-function/
    nx.relabel_nodes(G, lambda x: f'{x:08b}', copy=False) 
    
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
    # print(G.nodes(data="wrk"))
    for node in (G.nodes(data=True)):
        role = node[1].get('wrk')
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

# Note in this assignment M only holds the number, however we must loop through all since the nodes are randomized.
def reduce_graph(G, M, draw = True):
    ''' G will be reduced to M-node,data server only, graph '''
    

    pos = nx.get_node_attributes(G, 'pos')
    empty_copy = nx.create_empty_copy(G)
    # print(empty_copy.nodes(data=True))
    G = empty_copy

    # Go through the nodes and save only the M nodes. 
    m_nodes = {}
    
    # Adding an integer as a key as easier to iterate when computing hamming distance
    index = 0
    for node in G.nodes(data=True):
        if node[1]['wrk'] == 's':
            m_nodes[index]=node
            index+=1
    # print(m_nodes)

    # ctr = find_center_node(G)[0]
    # G.nodes[ctr]['wrk'] = 'd-ctr'

    for i in range(len(m_nodes)):
        # NOTE this for loop should be simplified to i > j 
        for j in range(i+1, len(m_nodes)): 
            count_bit_difference = 0 #NOTE Should ALWAYS be at least 1. 
            # can covert this to its own function
            for bit_position in range(8):
                #print(m_nodes[i][0][bit_position])
                #print(m_nodes[j][0][bit_position])
                if m_nodes[i][0][bit_position] != m_nodes[j][0][bit_position]:
                   count_bit_difference += 1
            
            G.add_edge(m_nodes[i][0], m_nodes[j][0], weight=count_bit_difference)

    # Removes white nodes. Need to do this so find_center_node() sees one connected component
    copy = G.copy()
    copy.remove_nodes_from(list(nx.isolates(copy)))
    red_ctr = find_center_node(copy)[0]
    G.nodes[red_ctr]['wrk'] = 'r-ctr'
    G.remove_nodes_from(list(nx.isolates(G))) # remove white nodes


    # G.nodes[int(red_ctr, 2)]['wrk'] = 'r_ctr'

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
        for node in G.nodes(data=True): 
            labels[node[0]] = node[0]
        nx.draw_networkx_labels(G, pos, labels, font_size = 10)

        edge_labels = nx.get_edge_attributes(G,'weight')
        # formatted_labels = {}
        # for label in labels:
        #     formatted_labels[label]=  "weight: "+str(label[1])
        nx.draw_networkx_edge_labels(G,pos,edge_labels=edge_labels)

    # realize a logic to reduce the network based on find MST

    if draw:
        plt.xlim(-0.05, 1.05)
        plt.ylim(-0.05, 1.05)
        # plt.axis('off')
        plt.show(block = False)
    
    return G 

def distancefromnodes(G,x):
    #Returns the sum of distances between node x and all nodes in the array arr.
    distance = 0
    for y in list(G):
        distance+=nx.shortest_path_length(G,x,y)
    return distance
    
def furthestfromMnodes(G):
    #Returns the sum of distances between the node furthest from all M nodes and the M nodes themselves.
    nodedict = {}
    for x in list(G):
        sum = 0
        for y in list(G):
            sum +=nx.shortest_path_length(G,x,y)
        nodedict[x] = sum
    highest = list(G)[0]
    for x in list(G):
        if nodedict[x]>nodedict[highest]:
            highest = x
    return highest
    
def randomMtoMdistance(G):
    '''Returns the sum of distances between a randomly selected M node and all other M nodes.'''
    sourcenode = list(G)[rnd.randrange(0,len(list(G)))]
    distance = 0
    for y in list(G):
        if y != sourcenode:
            distance+=nx.shortest_path_length(G,sourcenode,y)
    return distance

def closestMtoMdistance(G):
    #Returns the sum of distances between the node closest from all M nodes and the M nodes themselves.
    nodedict = {}
    for x in list(G):
        sum = 0
        for y in list(G):
            sum +=nx.shortest_path_length(G,x,y)
        nodedict[x] = sum
    lowest = list(G)[0]
    for x in list(G):
        if nodedict[x]<nodedict[lowest]:
            lowest = x
    return lowest

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
        answerlist[i][0] = distancefromnodes(G,furthestfromMnodes(G))
        answerlist[i][1] = randomMtoMdistance(G)
        answerlist[i][2] = distancefromnodes(G,find_center_node(G)[0])
        answerlist[i][3] = closestMtoMdistance(G)
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

assignment()
#simulation(200, 20, 0.125, 10, 100, 10, 10, True)
#plt.show()