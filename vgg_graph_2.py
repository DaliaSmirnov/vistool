import pandas as pd
import json
import community as community_louvain
import networkx as nx
import random

# sample graph
def subgraph_sample(partition_df, count, graph):
    view_partition = partition_df.copy()
    sub_graph = graph.copy()
    if count > len(sub_graph.nodes()):
        return sub_graph
    sub_degree = pd.DataFrame(nx.degree(sub_graph), columns=['node', 'degree'])
    view_partition = view_partition.merge(sub_degree, on='node')

    for i in range(9):
        view_partition = view_partition[view_partition['node'].isin(sub_graph.nodes)]
        for part, grp in view_partition.sort_values('degree', ascending=False).groupby('part'):
            grp['odd'] = grp.reset_index(drop=True).index // 2
            grp = grp[:grp.shape[0]-(grp.shape[0] % 2)] # select frac & trim odd counts need pairs 
            for odd, pair in grp.groupby('odd'):  # trim odd counts need pairs
                nx.contracted_nodes(sub_graph, pair.node.values[0], pair.node.values[1], copy=False, self_loops=False)
        print(len(sub_graph.nodes), 'nodes')
        if count > len(sub_graph.nodes()):
            break

    print('shape:', len(sub_graph.nodes), 'nodes')
    return sub_graph


def calculate_nodes_degree(edges_list):
    # count how many "neighbors" = degrees has each node
    metadata_df = pd.DataFrame(edges_list)
    degree_source = metadata_df.groupby('source').target.count()
    degree_target = metadata_df.groupby('target').source.count()
    degree = degree_target.append(degree_source)
    degree = degree.reset_index(level=0)
    return degree.groupby('index').sum()[0].to_dict()


def create_nodes_df(partition_df,sub_graph, edges_df):
    nodes_df = pd.DataFrame(sub_graph.nodes()).rename(columns={0: 'id'})
    nodes_df = nodes_df.merge(partition_df, left_on='id', right_on='node', how='left')
    nodes_df = nodes_df.merge(edges_df, left_on='id', right_on='source', how='left')
    nodes_df = nodes_df.drop_duplicates('id')
    nodes_df['label'] = nodes_df['label'].fillna('other')
    nodes_df = nodes_df.fillna('')
    nodes_dict = nodes_df[['id', 'part','label']].to_dict(orient='index')
    nodes_list = list(nodes_dict.values())
    return nodes_df, nodes_list



def create_links_df(sub_graph):
    # convert the *links* of the graph into list, will be represented later as JSONS
    links_df = pd.DataFrame([sub_graph.edges()]).T
    links_df = links_df.reset_index().drop(0, axis=1)
    links_df = pd.concat([links_df, links_df['index'].apply(lambda x:pd.Series(x))], axis=1).drop(['index'], axis=1)
    print('links_df created !', links_df.shape[0])
    edges_dict = links_df.rename(columns={0: 'source', 1: 'target', 'weight': 'value'}).to_dict(orient='index')
    edges_list = list(edges_dict.values())
    return edges_list



def create_jsons(nodes_list, nodes_df, edges_list, data_type, part_num, thr):
    # create json file
    degree = calculate_nodes_degree(edges_list)
    store_json = {'nodes':nodes_list, 'links':edges_list,'degree': degree}
    with open("./js/" + data_type + "_thr_" + str(thr) + '_p' + str(part_num) + ".json" , "w") as outfile:
        json.dump(store_json, outfile)

    # create *image* json file
    # nodes_df['img_name'] = '/img/' + nodes_df['id'] + '.jpeg'
    # nodes_df['img_name'] = 'http://localhost:8001/api/v1/namespaces/default/services/imaginary:http/proxy/api/exposed/v1.0/asset/' + nodes_df['id'].astype(str)
    # store_json = nodes_df[['img_name', 'id']].set_index('id')['img_name'].to_dict()
    # with open("./js/" + data_type + "_thr_" + str(thr) + '_p' + str(part_num) + "_img.json" , "w") as outfile:
    #     json.dump(store_json, outfile)

    print('part', part_num, 'is ready!')
    print('path:',data_type + "_thr_" + str(thr) + '_p' + str(part_num))


def generate_tree(graph, part_num, nodes, edges_df, data_type, thr, all_links):
    print('generate_tree: nodes', len(nodes))

    # divide nodes into partitions
    part_graph = nx.subgraph(graph, nodes).copy() # Take the nodes of the current cluster from the full graph.
    partition = community_louvain.best_partition(part_graph, weight = 'weight', random_state = 42) # Divide the nodes of the current cluster into sub-clusters. Note: the "random_state = 42" is supposed to make the partiioning more consistent.
    sub_partition_df = pd.DataFrame([partition]).T.reset_index().rename(columns={'index': 'node', 0: 'part'}) # Convert the resulting dict into a Dataframe.
    print('generate_tree: parts', sub_partition_df['part'].nunique())

    # create representing sub-graph, limit to 500 nodes in a subgraph
    sub_graph = subgraph_sample(sub_partition_df, 500, part_graph)
    nodes_df, nodes_list = create_nodes_df(sub_partition_df, sub_graph,edges_df)
    edges_list = create_links_df(sub_graph)
    sub_partition_df['part_num'] = part_num
    create_jsons(nodes_list, nodes_df, edges_list, data_type, part_num, thr)

    # the stop condition of this recursive function,
    # when there won't be more than 1 part is it a sign that we in the deepest part
    if (sub_partition_df['part'].nunique() < 2):  # done...
        for sub_part_num, part_df in sub_partition_df.groupby('part'):
            part_df['sub_part_num'] = str(part_num) + 'p' + str(sub_part_num)
            all_links.append(part_df)
            return

    # If we got here, there are more than one sub-cluster in the current cluster.
    for sub_part_num, part_df in sub_partition_df.groupby('part'): # Go through the sub-clusters:
        part_df['sub_part_num'] = str(part_num) + 'p' + str(sub_part_num) # Create the full path of this sub-cluster.
        all_links.append(part_df)
        generate_tree(graph, str(part_num) + 'p' + str(sub_part_num), part_df['node'],edges_df, data_type, thr, all_links) # Pass only the nodes of this sub-cluster.

    return all_links


def links4tree(all_links, data_type):
    links_df = pd.concat(all_links)
    links_df['count'] = links_df['sub_part_num'].map(links_df['sub_part_num'].value_counts())
    links_df.columns = [str(x) for x in links_df.columns]
    output_path = './data/' + data_type + '_tree.parq'
    links_df.to_parquet(output_path)
    print(output_path, 'created!')
    return links_df


def generate_random_color():
    random_number = random.randint(0, 16777215)
    hex_number = str(hex(random_number))
    hex_number = '#' + hex_number[2:]
    return hex_number


def create_metadata(links_df,edges_df,data_type):
    parts = links_df.groupby('node').sub_part_num.count().to_dict()
    labels = edges_df.groupby('label').source.apply(set).apply(list).to_dict()
    remaining_nodes = set(edges_df['target']) - set(edges_df['source'])
    labels['other'] = list(remaining_nodes)

    list_of_labels_keys=labels.keys()
    dict_labels_and_colors={}
    for lab in list_of_labels_keys:
        dict_labels_and_colors[lab]=generate_random_color()
    metadata = {'parts': parts, 'labels': labels,'dict_labels_and_colors':dict_labels_and_colors}
    with open("./js/" + data_type + "_metadata.json", "w") as outfile:
        json.dump(metadata, outfile)


def main(data_type,thr,edges_df_path):
    all_links = []
    # read the edges file and convert to graph
    edges_df = pd.read_parquet(edges_df_path)
    edges_df = edges_df.dropna()
    graph = nx.from_pandas_edgelist(edges_df)
    # the algo.
    generate_tree(graph, '-1', graph.nodes(),edges_df, data_type, thr, all_links)
    links_df = links4tree(all_links, data_type)
    # create metadata file
    create_metadata(links_df,edges_df, data_type)
