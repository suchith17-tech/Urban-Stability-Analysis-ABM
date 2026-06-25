import networkx as nx


def create_interaction_network(num_agents, avg_degree, seed=42):
    """
    Create Erdős–Rényi random graph.
    """
    probability = avg_degree / num_agents
    G = nx.erdos_renyi_graph(num_agents, probability, seed=seed)

    # Ensure graph is connected — extract largest component as a subgraph
    if not nx.is_connected(G):
        largest_cc = max(nx.connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()

    return G