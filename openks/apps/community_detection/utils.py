'''Citation
@inproceedings{rozemberczki2019gemsec,
                title={{GEMSEC: Graph Embedding with Self Clustering}},
                author={Rozemberczki, Benedek and Davies, Ryan and Sarkar, Rik and Sutton, Charles},
                booktitle={Proceedings of the 2019 IEEE/ACM International Conference on Advances in Social Networks Analysis and Mining 2019},
                pages={65-72},
                year={2019},
                organization={ACM}
                }
'''

import pandas as pd
import networkx as nx
import numpy as np
import random
import community
from collections import Counter
from tqdm import tqdm
from sklearn.cluster import KMeans
from texttable import Texttable
import json
from community.community_louvain import modularity as Cmodularity


def json_read(schema_path):
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    return schema


def normalized_overlap(g, node_1, node_2):
    """
    Function to calculate the normalized neighborhood overlap.
    :param g: NX graph.
    :param node_1: Node 1. of a pair.
    :param node_2: Node 2. of a pair.
    :return: normalized neighborhood overlap
    """

    inter = len(set(nx.neighbors(g, node_1)).intersection(set(nx.neighbors(g, node_2))))
    unio = len(set(nx.neighbors(g, node_1)).union(set(nx.neighbors(g, node_2))))
    return float(inter) / float(unio)


def overlap(g, node_1, node_2):
    """
    Function to calculate the neighborhood overlap.
    :param g: NX graph.
    :param node_1: Node 1. of a pair.
    :param node_2: Node 2. of a pair.
    :return: neighborhood overlap
    """

    inter = len(set(nx.neighbors(g, node_1)).intersection(set(nx.neighbors(g, node_2))))
    return float(inter)


def unit(g, node_1, node_2):
    """
    Function to calculate the 'unit' weight.
    :param g: NX graph.
    :param node_1: Node 1. of a pair.
    :param node_2: Node 2. of a pair.
    :return: 'unit' weight
    """
    return 1


def min_norm(g, node_1, node_2):
    """
    Function to calculate the minimum normalized neighborhood overlap.
    :param g: NX graph.
    :param node_1: Node 1. of a pair.
    :param node_2: Node 2. of a pair.
    :return: minimum normalized neighborhood overlap
    """

    inter = len(set(nx.neighbors(g, node_1)).intersection(set(nx.neighbors(g, node_2))))
    min_norm = min(len(set(nx.neighbors(g, node_1))), len(set(nx.neighbors(g, node_2))))
    return float(inter) / float(min_norm)


def overlap_generator(config, graph):
    """
    Function to generate weight for all of the edges.
    :param config: configuration
    :param graph: graph
    :return: weight
    """

    if config['overlap_weighting'] == "normalized_overlap":
        overlap_weighter = normalized_overlap
    elif config['overlap_weighting'] == "overlap":
        overlap_weighter = overlap
    elif config['overlap_weighting'] == "min_norm":
        overlap_weighter = min_norm
    else:
        overlap_weighter = unit
    print(" ")
    print("Weight calculation started.")
    print(" ")
    edges = nx.edges(graph)
    weights = {edge: overlap_weighter(graph, edge[0], edge[1]) for edge in tqdm(edges)}
    weights_prime = {(edge[1], edge[0]): value for edge, value in weights.items()}
    weights.update(weights_prime)
    print(" ")
    return weights


def index_generation(weights, a_random_walk):
    """
    Function to generate overlaps and indices.
    :param weights: weights
    :param a_random_walk: a_random_walk
    :return: edge_set_1, edge_set_2, overlaps
    """

    edges = [(a_random_walk[i], a_random_walk[i + 1]) for i in range(0, len(a_random_walk) - 1)]
    edge_set_1 = np.array(range(0, len(a_random_walk) - 1))
    edge_set_2 = np.array(range(1, len(a_random_walk)))
    overlaps = np.array(list(map(lambda x: weights[x], edges))).reshape((-1, 1))
    return edge_set_1, edge_set_2, overlaps


def batch_input_generator(a_random_walk, random_walk_length, window_size):
    """
    Function to generate features from a node sequence.
    :param a_random_walk: a_random_walk
    :param random_walk_length: random_walk_length
    :param window_size: window_size
    :return: features
    """

    seq_1 = [a_random_walk[j] for j in range(random_walk_length - window_size)]
    seq_2 = [a_random_walk[j] for j in range(window_size, random_walk_length)]
    return np.array(seq_1 + seq_2)


def batch_label_generator(a_random_walk, random_walk_length, window_size):
    """
    Function to generate labels from a node sequence.
    :param a_random_walk: a_random_walk
    :param random_walk_length: random_walk_length
    :param window_size: window_size
    :return: labels
    """

    grams_1 = [a_random_walk[j + 1:j + 1 + window_size] for j in range(random_walk_length - window_size)]
    grams_2 = [a_random_walk[j - window_size:j] for j in range(window_size, random_walk_length)]
    return np.array(grams_1 + grams_2)


def gamma_incrementer(step, gamma_0, current_gamma, num_steps):
    """
    gamma incrementer
    """
    if step > 1:
        exponent = (0 - np.log10(gamma_0)) / float(num_steps)
        current_gamma = current_gamma * (10 ** exponent)
    return current_gamma


def neural_modularity_calculator(graph, embedding, means):
    """
    Function to calculate the GEMSEC cluster assignments.
    :param graph: graph
    :param embedding: embedding
    :param means: means
    :return: modularity, assignments
    """

    assignments = {}
    for node in graph.nodes():
        positions = means - embedding[node, :]
        values = np.sum(np.square(positions), axis=1)
        index = np.argmin(values)
        assignments[int(node)] = int(index)

    modularity = Cmodularity(assignments, graph)
    return modularity, assignments


def classical_modularity_calculator(graph, embedding, config):
    """
    Function to calculate the DeepWalk cluster centers and assignments.
    :param graph: graph
    :param embedding: embedding
    :param config: config
    :return: DeepWalk cluster centers and assignments
    """

    kmeans = KMeans(n_clusters=config['cluster_number'], random_state=0, n_init=1).fit(embedding)
    assignments = {str(i): int(kmeans.labels_[i]) for i in range(0, embedding.shape[0])}
    modularity = community.modularity(assignments, graph)
    return modularity, assignments


class RandomWalker:
    """
    Class to generate vertex sequences.
    """

    def __init__(self, graph, nodes, repetitions, length):
        print("Model initialization started.")
        self.graph = graph
        self.nodes = list(nodes)
        self.repetitions = repetitions
        self.length = length

    def small_walk(self, start_node):
        """
        Generate a node sequence from a start node.
        """
        walk = [start_node]
        while len(walk) != self.length:
            end_point = walk[-1]
            neighbors = list(nx.neighbors(self.graph, end_point))
            if len(neighbors) > 0:
                walk = walk + random.sample(neighbors, 1)
            else:
                break
        return walk

    def count_frequency_values(self):
        """
        Calculate the co-occurence frequencies.
        """
        raw_counts = [node for walk in self.walks for node in walk]
        counts = Counter(raw_counts)
        self.degrees = [counts[i] for i in range(0, len(self.nodes))]

    def do_walks(self):
        """
        Do a series of random walks.
        """
        self.walks = []
        for rep in range(0, self.repetitions):
            random.shuffle(self.nodes)
            print(" ")
            print("Random walk series " + str(rep + 1) + ". initiated.")
            print(" ")
            for node in tqdm(self.nodes):
                walk = self.small_walk(node)
                self.walks.append(walk)
        self.count_frequency_values()
        return self.degrees, self.walks


class SecondOrderRandomWalker:

    def __init__(self, nx_G, is_directed, p, q):
        self.G = nx_G
        self.nodes = nx.nodes(self.G)
        print("Edge weighting.\n")
        for edge in tqdm(self.G.edges()):
            self.G[edge[0]][edge[1]]['weight'] = 1.0
            self.G[edge[1]][edge[0]]['weight'] = 1.0
        self.is_directed = is_directed
        self.p = p
        self.q = q

    def node2vec_walk(self, walk_length, start_node):
        """
        Simulate a random walk starting from start node.
        """
        G = self.G
        alias_nodes = self.alias_nodes
        alias_edges = self.alias_edges

        walk = [start_node]

        while len(walk) < walk_length:
            cur = walk[-1]
            cur_nbrs = sorted(G.neighbors(cur))
            if len(cur_nbrs) > 0:
                if len(walk) == 1:
                    walk.append(cur_nbrs[alias_draw(alias_nodes[cur][0], alias_nodes[cur][1])])
                else:
                    prev = walk[-2]
                    next = cur_nbrs[alias_draw(alias_edges[(prev, cur)][0], alias_edges[(prev, cur)][1])]
                    walk.append(next)
            else:
                break

        return walk

    def count_frequency_values(self, walks):
        """
        Calculate the co-occurence frequencies.
        """
        raw_counts = [node for walk in walks for node in walk]
        counts = Counter(raw_counts)
        self.degrees = [counts[i] for i in range(0, len(self.nodes))]
        return self.degrees

    def simulate_walks(self, num_walks, walk_length):
        """
        Repeatedly simulate random walks from each node.
        """
        G = self.G
        walks = []
        nodes = list(G.nodes())
        for walk_iter in range(num_walks):
            print(" ")
            print("Random walk series " + str(walk_iter + 1) + ". initiated.")
            print(" ")
            random.shuffle(nodes)
            for node in tqdm(nodes):
                walks.append(self.node2vec_walk(walk_length=walk_length, start_node=node))

        return walks, self.count_frequency_values(walks)

    def get_alias_edge(self, src, dst):
        """
        Get the alias edge setup lists for a given edge.
        """
        G = self.G
        p = self.p
        q = self.q

        unnormalized_probs = []
        for dst_nbr in sorted(G.neighbors(dst)):
            if dst_nbr == src:
                unnormalized_probs.append(G[dst][dst_nbr]['weight'] / p)
            elif G.has_edge(dst_nbr, src):
                unnormalized_probs.append(G[dst][dst_nbr]['weight'])
            else:
                unnormalized_probs.append(G[dst][dst_nbr]['weight'] / q)
        norm_const = sum(unnormalized_probs)
        normalized_probs = [float(u_prob) / norm_const for u_prob in unnormalized_probs]

        return alias_setup(normalized_probs)

    def preprocess_transition_probs(self):
        """
        Preprocessing of transition probabilities for guiding the random walks.
        """
        G = self.G
        is_directed = self.is_directed

        alias_nodes = {}
        print("")
        print("Preprocesing.\n")
        for node in tqdm(G.nodes()):
            unnormalized_probs = [G[node][nbr]['weight'] for nbr in sorted(G.neighbors(node))]
            norm_const = sum(unnormalized_probs)
            normalized_probs = [float(u_prob) / norm_const for u_prob in unnormalized_probs]
            alias_nodes[node] = alias_setup(normalized_probs)

        alias_edges = {}
        triads = {}

        if is_directed:
            for edge in G.edges():
                alias_edges[edge] = self.get_alias_edge(edge[0], edge[1])
        else:
            for edge in tqdm(G.edges()):
                alias_edges[edge] = self.get_alias_edge(edge[0], edge[1])
                alias_edges[(edge[1], edge[0])] = self.get_alias_edge(edge[1], edge[0])

        self.alias_nodes = alias_nodes
        self.alias_edges = alias_edges

        return


def alias_setup(probs):
    """
    Compute utility lists for non-uniform sampling from discrete distributions.
    Refer to https://hips.seas.harvard.edu/blog/2013/03/03/the-alias-method-efficient-sampling-with-many-discrete-outcomes/
    for details
    :param probs: probabilities
    :return: utility lists
    """

    K = len(probs)
    q = np.zeros(K)
    J = np.zeros(K, dtype=np.int)
    smaller = []
    larger = []

    for kk, prob in enumerate(probs):
        q[kk] = K * prob
    if q[kk] < 1.0:
        smaller.append(kk)
    else:
        larger.append(kk)

    while len(smaller) > 0 and len(larger) > 0:
        small = smaller.pop()
        large = larger.pop()

        J[small] = large
        q[large] = q[large] + q[small] - 1.0
        if q[large] < 1.0:
            smaller.append(large)
        else:
            larger.append(large)

    return J, q


def alias_draw(J, q):
    """
    Draw sample from a non-uniform discrete distribution using alias sampling.
    """
    K = len(J)

    kk = int(np.floor(np.random.rand() * K))
    if np.random.rand() < q[kk]:
        return kk
    else:
        return J[kk]


def graph_reader(input_path):
    """
    Function to read a csv edge list and transform it to a networkx graph object.
    :param input_path: the path of input
    :return: networkx graph
    """
    edges = pd.read_csv(input_path)
    graph = nx.from_edgelist(edges.values.tolist())
    return graph


def log_setup(args_in):
    """
    Function to setup the logging hash table.
    :param args_in: input args
    :return: logging hash table
    """
    log = dict()
    log["times"] = []
    log["losses"] = []
    log["cluster_quality"] = []
    log["params"] = args_in
    return log


def json_dumper(data, path):
    """
    Function to dump the logs and assignments.
    :param data: data
    :param path: dump path
    :return:
    """
    with open(path, 'w') as outfile:
        json.dump(data, outfile)


def initiate_dump_gemsec(log, assignments, config, final_embeddings, c_means):
    """
    Function to dump the logs and assignments for GEMSEC. If the matrix saving boolean is true the embedding is also saved.
    :param log: log
    :param assignments: assignments
    :param config: configuration
    :param final_embeddings: final_embeddings result
    :param c_means: cluster means
    :return:
    """

    json_dumper(log, config['log_output'])
    json_dumper(assignments, config['assignment_output'])
    print()
    if config['dump_matrices']:
        final_embeddings = pd.DataFrame(final_embeddings)
        final_embeddings.to_csv(config['embedding_output'], index=None)
        c_means = pd.DataFrame(c_means)
        c_means.to_csv(config['cluster_mean_output'], index=None)


def initiate_dump_dw(log, assignments, config, final_embeddings):
    """
    Function to dump the logs and assignments for DeepWalk. If the matrix saving boolean is true the embedding is also saved.
    :param log: log
    :param assignments: assignments
    :param config: configuration
    :param final_embeddings: final_embeddings results
    :return:
    """

    json_dumper(log, config['log_output'])
    json_dumper(assignments, config['assignment_output'])
    if config['dump_matrices']:
        final_embeddings = pd.DataFrame(final_embeddings)
        final_embeddings.to_csv(config['embedding_output'], index=None)


def tab_printer(log):
    """
    Function to print the logs in a nice tabular format.
    :param log: log
    :return: print the logs
    """

    t = Texttable()
    t.add_rows([['Epoch', log["losses"][-1][0]]])
    print(t.draw())

    t = Texttable()
    t.add_rows([['Loss', round(log["losses"][-1][1], 3)]])
    print(t.draw())

    t = Texttable()
    t.add_rows([['Modularity', round(log["cluster_quality"][-1][1], 3)]])
    print(t.draw())


def epoch_printer(repetition):
    """
    Function to print the epoch number.
    :param repetition: repetition information
    :return: print the epoch number
    """

    print("")
    print("Epoch " + str(repetition + 1) + ". initiated.")
    print("")


def log_updater(log, repetition, average_loss, optimization_time, modularity_score):
    """
    Function to update the log object.
    :param log: log
    :param repetition: repetition
    :param average_loss: average loss
    :param optimization_time: optimization time
    :param modularity_score: modularity score
    :return: log object
    """

    index = repetition + 1
    log["losses"] = log["losses"] + [[int(index), float(average_loss)]]
    log["times"] = log["times"] + [[int(index), float(optimization_time)]]
    log["cluster_quality"] = log["cluster_quality"] + [[int(index), float(modularity_score)]]
    return log
