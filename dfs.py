import os
import json
import numpy as np 
import time
import datetime
import random
from collections import defaultdict
from scipy.stats import norm
from logger_config import logger
import multiprocessing as mp 

def make_graph(train_file_path):
    start = time.time()
    graph = defaultdict(list)
    directed_graph = defaultdict(list)
    examples = json.load(open(train_file_path, 'r', encoding='utf-8'))
    #entity_dict = get_entity_dict()
    train_len = len(examples)    
    for ex in examples:
        head_id, relation, tail_id = ex['head_id'], ex['relation'], ex['tail_id']
        triple = (head_id, relation, tail_id)
        inv_triple = (tail_id, relation, head_id)
        if triple not in graph[head_id]:
            graph[head_id].append(triple)
        if inv_triple not in graph[tail_id]:
            graph[tail_id].append(inv_triple)
        if triple not in directed_graph[head_id]:
            directed_graph[head_id].append(triple)
    end = time.time()
    logger.info('time to make graph: {}'.format(datetime.timedelta(seconds=end-start))) 
    return graph, directed_graph, train_len   



class DFS_PATH:
    def __init__(self, graph, directed_graph, walks_num):
        self.walks_num = walks_num
        self.graph = graph
        self.directed_graph = directed_graph
        self.num_process = 10

    def dfs_triplet(self, start_node, walks_num):
        stack = []
        stack.append(start_node)
        seen = set()
        seen.add(start_node)
        walk = []  
        walk_nodes = []
        i=0
        while len(stack) > 0:            
            vertex = stack[-1]  
            unvisited_triplets = [triplet for triplet in self.graph[vertex] if triplet[2] not in seen]

            if unvisited_triplets:
                next_triplet = random.choice(unvisited_triplets)
                next_node = next_triplet[2]
                stack.append(next_node)
                seen.add(next_node)  
                walk_nodes.append(next_node)

                #to except duplicate entity in each triplet
                if i%2 == 0:
                    if vertex in self.directed_graph.keys() and next_triplet in self.directed_graph[vertex]:
                        walk.append(next_triplet)
                    else:
                        tail, rel, head = next_triplet[0], next_triplet[1], next_triplet[2]
                        reverse = [head, rel, tail]
                        walk.append(reverse)
                i+=1   
                
                if len(walk_nodes) >= walks_num:
                    break
            else:
                # If there are no unvisited triplets, backtrack
                stack.pop()
        
        return walk, walk_nodes

    
    def process_chunk(self, chunk):
        pathes_dict = defaultdict(list)
        pathes = []
        for node in chunk:
            dfs_path = []
            walk, walk_nodes = self.dfs_triplet(node, self.walks_num)
            pathes_dict[node] = walk_nodes
            if len(walk_nodes) < self.walks_num:
                while len(walk_nodes) < self.walks_num:
                    random_entity = random.sample(self.graph.keys(), 1)[0]
                    walk2, walk_nodes2 = self.dfs_triplet(random_entity, self.walks_num - len(walk_nodes))
                    walk.extend(walk2)
                    walk_nodes.extend(walk_nodes2)

            if len(walk) != self.walks_num//2 :
                walk = walk[:self.walks_num//2]
                
            for triple in walk:
                assert len(walk) == self.walks_num//2
                head_id, relation, tail_id = triple[0], triple[1], triple[2]
                ex = {'head_id': head_id,'relation': relation,'tail_id': tail_id}
                dfs_path.append(ex)
                
            pathes.append(dfs_path)
     
        return pathes, pathes_dict
    
    def intermediate(self):
        all_pathes = []
        all_pathes_dict = {}
        #for multiprocessing
        keys = list(self.graph.keys())
        chunk_size = len(keys)%self.num_process
        chunks = [keys[i:i+chunk_size] for i in range(0, len(keys), chunk_size)]
        
        with mp.Pool(self.num_process) as pool:
            pathes, pathes_dict = pool.starmap(self.process_chunk, [(chunk,) for chunk in chunks])
        
        all_pathes.extend(path for path in pathes)
        all_pathes_dict.update(path for path in pathes_dict)
        '''
        for node in self.graph.keys():
            dfs_path = []
            walk, walk_nodes = self.dfs_triplet(node, self.walks_num)
            pathes_dict[node] = walk_nodes
            if len(walk_nodes) < self.walks_num:
                count +=1
                #count_dict[node] = len(walk)
                while len(walk_nodes) < self.walks_num:
                    random_entity = random.sample(self.graph.keys(), 1)[0]
                    walk2, walk_nodes2 = self.dfs_triplet(random_entity, self.walks_num - len(walk_nodes))
                    walk.extend(walk2)
                    walk_nodes.extend(walk_nodes2)

            if len(walk) != self.walks_num//2 :
                walk = walk[:self.walks_num//2]
                
            for triple in walk:
                assert len(walk) == self.walks_num//2
                head_id, relation, tail_id = triple[0], triple[1], triple[2]
                ex = {'head_id': head_id,'relation': relation,'tail_id': tail_id}
                dfs_path.append(ex)
                
            all_pathes.append(dfs_path)
        
        logger.info(f'cannot make {self.walks_num} path : {count}')
        '''
        return all_pathes, all_pathes_dict
    