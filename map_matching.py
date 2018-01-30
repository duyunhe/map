# coding=utf-8
from xml.etree import ElementTree as ET
import matplotlib.pyplot as plt
from traj import load_traj, load_trace
from sklearn.neighbors import KDTree
import math
import Queue
from geo import point2segment, point_project, calc_dist, bl2xy, is_near_segment, calc_included_angle
from time import clock
import traj
import numpy as np

color = ['r-', 'b-', 'g-', 'c-', 'm-', 'y-', 'c-', 'r-', 'b-', 'orchid', 'm--', 'y--', 'c--', 'k--', 'r:']
region = {'primary': 0, 'secondary': 1, 'tertiary': 2,
          'unclassified': 5, 'trunk': 3, 'service': 4, 'trunk_link': 6,
          'primary_link': 7, 'secondary_link': 8, 'residential': 9}

EDGE_ONEWAY = 3
EDGES = 2
EDGE_INDEX = 4
EDGE_LENGTH = 5
NODE_EDGELIST = 2

map_node_dict = {}
map_edge_list = []
map_way = {}
# global data structure
nodeid_list = []


class DistNode(object):
    def __init__(self, nodeid, dist):
        self.nodeid = nodeid
        self.dist = dist

    def __lt__(self, other):
        return self.dist < other.dist


class MapNode(object):
    """
    点表示
    point([px,py]), nodeid, link_list, rlink_list, dist_dict
    在全局维护dict, key=nodeid, value=MapNode
    """
    def __init__(self, point, nodeid):
        self.point, self.nodeid = point, nodeid
        self.link_list = []         # 连接到其他点的列表, [[edge0, node0], [edge1, node1]....]
        self.rlink_list = []
        self.dist_dict = {}         # 距离字典，存储500m之内的点的道路距离
        self.reach_set = None       # 可访问的边index列表

    def add_link(self, edge, node):
        self.link_list.append([edge, node])

    def add_rlink(self, edge, node):
        self.rlink_list.append([edge, node])


class MapEdge(object):
    """
    线段表示
    nodeid_0, nodeid_1,
    oneway(true or false), edge_index, edge_length
    维护list[MapEdge]
    """
    def __init__(self, nodeid0, nodeid1, oneway, edge_index, edge_length):
        self.nodeid0, self.nodeid1 = nodeid0, nodeid1
        self.oneway = oneway
        self.edge_index = edge_index
        self.edge_length = edge_length


def load_write():
    traj_order = load_traj("./data/test.csv")
    cnt = 0
    pos = 6
    fp = open("traj_sample.txt", "w")
    for order, traj in traj_order.items():
        # traj is list
        if len(traj) < 10:
            continue
        x, y, z = [], [], []
        for lon, lat, _ in traj:
            tx, ty = bl2xy(lat, lon)
            x.append(tx)
            y.append(ty)
        if cnt == pos:
            plt.plot(x, y, 'k--', marker='x')
            for line in zip(x, y):
                fp.write(str(line))
                fp.write('\n')
        cnt += 1
        if cnt > pos:
            break
    fp.close()


def edge2xy(e):
    x0, y0 = map_node_dict[e.nodeid0].point[0:2]
    x1, y1 = map_node_dict[e.nodeid1].point[0:2]
    return x0, y0, x1, y1


def cal_max_way(way):
    max_dist = 0
    for w in way:
        lx, ly = 0, 0
        pl = way[w]
        for t in pl['node']:
            x, y = t[0], t[1]
            if lx != 0:
                dist = math.sqrt((lx - x) ** 2 + (ly - y) ** 2)
                if max_dist < dist:
                    max_dist = dist
            lx, ly = x, y
    return max_dist


def draw_map():
    for i in map_way:
        pl = map_way[i]
        node_list = pl['node']
        x, y = [], []
        for nodeid in node_list:
            x.append(map_node_dict[nodeid].point[0])
            y.append(map_node_dict[nodeid].point[1])

        c = color[region[pl['highway']]]
        plt.plot(x, y, c, alpha=0.3)
        # if 'name' in pl:
        #     name = pl['name']
        #     plt.text(x[0] + 10, y[0] + 10, name)


def draw_seg(seg, c):
    x, y = zip(*seg)
    plt.plot(x, y, c, linewidth=2)


def draw_edge_set(edge, edge_set, node):
    for i in edge_set:
        draw_edge(edge[i], 'b', node)


def draw_edge(e, c):
    x0, y0, x1, y1 = edge2xy(e)
    x, y = [x0, x1], [y0, y1]
    plt.plot(x, y, c, linewidth=2)


def draw_edge_list(edge_list):
    for edge in edge_list:
        draw_edge(edge, 'b')


def draw_nodes(node_list):
    x, y = [], []
    for node in node_list:
        x.append(node[0])
        y.append(node[1])
    plt.plot(x, y, 'mo', markersize=5)


def draw_points(points):
    x, y = zip(*points)
    plt.plot(x, y, 'ro', markersize=4)


def draw_point(point, c):
    """
    :param point: [x, y]
    :return: 
    """
    plt.plot([point[0]], [point[1]], c, markersize=6)


def calc_link():
    for edge in map_edge_list:
        n0, n1 = edge.nodeid0, edge.nodeid1
        if edge.oneway is True:
            map_node_dict[n0].add_link(edge, n1)
            map_node_dict[n1].add_rlink(edge, n0)
        else:
            map_node_dict[n0].add_link(edge, n1)
            map_node_dict[n1].add_link(edge, n0)
            map_node_dict[n0].add_rlink(edge, n1)
            map_node_dict[n1].add_rlink(edge, n0)


def calc_node_dict(node):
    """
    dijkstra算法计算最短路径
    保存在node中dist字典内
    :param node: MapNode
    :return: null
    """
    T = 80000 / 3600 * 10   # dist_thread
    node_set = set()        # node_set用于判断是否访问过
    edge_set = set()        # edge_set用于记录能够访问到的边
    q = Queue.PriorityQueue(maxsize=-1)     # 优先队列优化
    # initialize
    init_node = DistNode(node.nodeid, 0)
    node_set.add(node.nodeid)
    q.put(init_node)
    # best first search
    while not q.empty():
        cur_node = q.get()
        if cur_node.dist > T:
            break
        for edge, nextid in map_node_dict[cur_node.nodeid].link_list:
            edge_set.add(edge.edge_index)
            if nextid in node_set:
                continue
            node_set.add(nextid)
            new_node = DistNode(nextid, cur_node.dist + edge.edge_length)
            node.dist_dict[nextid] = new_node.dist
            q.put(new_node)

    # store edge indexes which can reach
    node.reach_set = edge_set


def calc_dist_for_each():
    bt = clock()
    for nodeid, node in map_node_dict.items():
        calc_node_dict(node)
    print clock() - bt


def read_xml(filename):
    tree = ET.parse(filename)
    p = tree.find('meta')
    nds = p.findall('node')
    for x in nds:
        node_dic = x.attrib
        nodeid = node_dic['id']
        dx, dy = bl2xy(float(node_dic['lat']), float(node_dic['lon']))
        node = MapNode([dx, dy], nodeid)
        map_node_dict[nodeid] = node
    wys = p.findall('way')
    for w in wys:
        way_dic = w.attrib
        wid = way_dic['id']
        node_list = w.findall('nd')
        map_way[wid] = {}
        oneway = False
        ref = map_way[wid]
        tag_list = w.findall('tag')
        for tag in tag_list:
            tag_dic = tag.attrib
            ref[tag_dic['k']] = tag_dic['v']
        if 'oneway' in ref:
            oneway = ref['oneway'] == 'yes'

        node_in_way = []
        for nd in node_list:
            node_dic = nd.attrib
            node_in_way.append(node_dic['ref'])
        ref['node'] = node_in_way
        last_nd = ''
        ref['edge'] = []
        for nd in node_in_way:
            if last_nd != '':
                edge_index = len(map_edge_list)
                ref['edge'].append(edge_index)
                p0, p1 = map_node_dict[last_nd].point, map_node_dict[nd].point
                edge_length = calc_dist(p0, p1)
                edge = MapEdge(last_nd, nd, oneway, edge_index, edge_length)
                map_edge_list.append(edge)
            last_nd = nd

    calc_link()

    calc_dist_for_each()


def get_trace_from_project(node, last_point, last_edge, cur_point, cur_edge, cnt):
    pq = Queue.PriorityQueue(maxsize=-1)
    x0, y0, x1, y1 = edge2xy(last_edge, node)
    rx, ry, _ = point_project(last_point[0], last_point[1], x0, y0, x1, y1)
    dist0, dist1 = calc_dist([rx, ry], [x0, y0]), calc_dist([rx, ry], [x1, y1])
    # 短路径优先，因此每个点只会访问一次
    # 在出队列时加入访问set中
    vis_set = set()
    if last_edge[EDGE_ONEWAY] is True:
        pq.put(DistNode(last_edge[1], dist1))
    else:
        pq.put(DistNode(last_edge[0], dist0))
        pq.put(DistNode(last_edge[1], dist1))

    x0, y0, x1, y1 = edge2xy(cur_edge, node)
    sx, sy, _ = point_project(cur_point[0], cur_point[1], x0, y0, x1, y1)
    dist0, dist1 = calc_dist([sx, sy], [x0, y0]), calc_dist([sx, sy], [x1, y1])
    obj0, obj1 = None, None
    if cur_edge[EDGE_ONEWAY] is True:
        obj0 = cur_edge[0]
    else:
        obj0, obj1 = cur_edge[0], cur_edge[1]

    if last_edge == cur_edge:
        # 就是同一条边
        return [[rx, ry], [sx, sy]]

    print_node = []
    # 维护一个反向链表last_node, ndn->...->nd3->nd2->nd1->nd0
    last_node = {}
    final_dist = 1e20
    while not pq.empty():
        cur_node = pq.get()
        cur_id, cur_dist = cur_node.ndid, cur_node.dist
        vis_set.add(cur_id)
        if cur_id == 'final':
            break
        print_node.append(node[cur_id])
        # 到达终点
        if cur_id == obj0:
            next_dist = cur_dist + dist0
            pq.put(DistNode('final', next_dist))
            if next_dist < final_dist:
                last_node['final'], final_dist = obj0, next_dist
            continue
        elif cur_id == obj1:
            next_dist = cur_dist + dist1
            pq.put(DistNode('final', next_dist))
            if next_dist < final_dist:
                last_node['final'], final_dist = obj1, next_dist
            continue
        edge_list = node[cur_id][EDGES]
        for e, nd in edge_list:
            next_dist = cur_dist + e[EDGE_LENGTH]
            if nd in vis_set:
                continue
            pq.put(DistNode(nd, next_dist))
            last_node[nd] = cur_id

    path = []
    cur_id = 'final'
    while cur_id in last_node:
        cur_id = last_node[cur_id]
        path.append(cur_id)
    path.reverse()
    trace = []
    trace.append([rx, ry])
    for nd in path:
        trace.append([node[nd][0], node[nd][1]])
    trace.append([sx, sy])
    return trace


def make_kdtree():
    nd_list = []
    for key, item in map_node_dict.items():
        nodeid_list.append(key)
        nd_list.append(item.point)
    X = np.array(nd_list)
    return KDTree(X, leaf_size=2, metric="euclidean"), X


def get_candidate_first(taxi_data, cnt=-1):
    """
    get candidate edges from road network which fit point 
    :param taxi_data: Taxi_Data  .px, .py, .speed, .stime
    :return: edge candidate list  list[edge0, edge1, edge...]
    """
    kdt, X = make_kdtree()
    dist, ind = kdt.query([[taxi_data.px, taxi_data.py]], k=50)

    pts = []
    seg_set = set()
    # fetch nearest map nodes in network around point, then check their linked edges
    for i in ind[0]:
        pts.append([X[i][0], X[i][1]])
        node_id = nodeid_list[i]
        edge_list = map_node_dict[node_id].link_list
        for e, nd in edge_list:
            seg_set.add(e.edge_index)
        # here, need reverse link,
        # for its first node can be far far away, then this edge will not be included
        edge_list = map_node_dict[node_id].rlink_list
        for e, nd in edge_list:
            seg_set.add(e.edge_index)

    edge_can_list = []
    for i in seg_set:
        edge_can_list.append(map_edge_list[i])

    return edge_can_list


def get_candidate_later(last_point, last_edge):
    """
    :param last_point: [px, py]
    :param last_edge: MapEdge
    :return: edge_can_list [edge0, edge1....]
    """
    edge_can_list = []
    edge_set = set()
    # r_point, ac = point_project(last_point, map_node_dict[last_edge.nodeid0].point,
    #                             map_node_dict[last_edge.nodeid1].point)
    # 简略版
    if last_edge.oneway:
        nodeid = last_edge.nodeid1
        edge_set = edge_set | map_node_dict[nodeid].reach_set

    else:
        nodeid0 = last_edge.nodeid0
        edge_set = edge_set | map_node_dict[nodeid0].reach_set
        nodeid1 = last_edge.nodeid1
        edge_set = edge_set | map_node_dict[nodeid1].reach_set
    for i in edge_set:
        edge_can_list.append(map_edge_list[i])

    return edge_can_list


def get_mod_point(taxi_data, candidate, last_point, cnt=-1):
    """
    get best fit point matched with candidate edges
    :param taxi_data: Taxi_Data
    :param candidate: list[edge0, edge1, edge...]
    :param last_point: last matched point 
    :return: matched point, matched edge
    """
    min_dist, sel_edge = 1e20, None
    point = [taxi_data.px, taxi_data.py]
    if last_point is None:      # first point
        for edge in candidate:
            n0, n1 = edge.nodeid0, edge.nodeid1
            p0, p1 = map_node_dict[n0].point, map_node_dict[n1].point
            dist = point2segment(point, p0, p1)
            if min_dist > dist:
                min_dist, sel_edge = dist, edge
    else:
        min_score = 1e20
        # print "new {0}, len={1}".format(cnt, len(candidate))
        if cnt == 60:
            draw_point(point, 'b')
            draw_point(last_point, 'm')
            draw_edge_list(candidate)
            return None, None

        for edge in candidate:
            n0, n1 = edge.nodeid0, edge.nodeid1
            p0, p1 = map_node_dict[n0].point, map_node_dict[n1].point
            if edge.oneway is True and not is_near_segment(last_point, point, p0, p1):
                # 角度过大
                continue
            w0, w1 = 1.0, 10.0
            # 加权计算分数，考虑夹角的影响
            dist = point2segment(point, p0, p1)
            score = w0 * dist + w1 * (1 - calc_included_angle(last_point, point, p0, p1))
            if score < min_score:
                min_score, sel_edge = score, edge

    try:
        sel_node0, sel_node1 = sel_edge.nodeid0, sel_edge.nodeid1
        project_point, _ = point_project(point, map_node_dict[sel_node0].point,
                                     map_node_dict[sel_node1].point)
    except AttributeError:
        print cnt
    return project_point, sel_edge


def get_first_point(point, kdt, X):
    """
    match point to nearest segment
    :param point: point to be matched
    :param kdt: kdtree
    :param X: 
    :return: 
    """
    dist, ind = kdt.query([point], k=30)

    pts = []
    seg_set = set()
    for i in ind[0]:
        pts.append([X[i][0], X[i][1]])
        node_id = nodeid_list[i]
        edge_list = map_node_dict[node_id].link_list
        for e, nd in edge_list:
            seg_set.add(e.edge_index)

    min_dist, sel = 1e20, -1
    for idx in seg_set:
        n0, n1 = map_edge_list[idx].nodeid0, map_edge_list[idx].nodeid1
        p0, p1 = map_node_dict[n0].point, map_node_dict[n1].point
        dist = point2segment(point, p0, p1)
        if min_dist > dist:
            min_dist, sel = dist, idx

    sel_edge = map_edge_list[sel]
    sel_node0, sel_node1 = sel_edge.nodeid0, sel_edge.nodeid1
    x0, y0 = map_node_dict[sel_node0].point[0:2]
    x1, y1 = map_node_dict[sel_node1].point[0:2]
    x, y = point[0:2]
    rx, ry, _ = point_project(x, y, x0, y0, x1, y1)
    return rx, ry, sel_edge


def get_mod_points0(traj_order):
    """
    White00 algorithm 1, basic algorithm point to point
    """
    kdt, X = make_kdtree()
    traj_mod = []
    # traj_point: [x, y]
    for taxi_data in traj_order:
        px, py, last_edge = get_first_point([taxi_data.px, taxi_data.py], kdt=kdt, X=X)
        traj_mod.append([px, py])

    return traj_mod


def POINT_MATCH(traj_order):
    """
    using segments sim dynamic comparation, 
    :param traj_order: list of Taxi_Data 
    :return: 
    """
    first_point = True
    last_point, last_edge = None, None
    cnt = 0
    traj_mod = []
    for data in traj_order:
        if first_point:
            candidate_edges = get_candidate_first(data, cnt)
            # Taxi_Data .px .py .stime .speed
            first_point = False
            point, last_edge = get_mod_point(data, candidate_edges, last_point, cnt)
            traj_mod.append(point)
            last_point = point
        else:
            # 首先判断两个点是否离得足够远
            if calc_dist([data.px, data.py], last_point) < 10:
                continue
            candidate_edges = get_candidate_later(last_point, last_edge)
            point, last_edge = get_mod_point(data, candidate_edges, last_point, cnt)
            traj_mod.append(point)
            last_point = point
            plt.text(data.px, data.py, '{0}'.format(cnt))
        cnt += 1
        if cnt == 61:
            break

    return traj_mod


def draw_trace(traj):
    x, y = [], []
    for data in traj:
        x.append(data.px)
        y.append(data.py)
    minx, maxx, miny, maxy = min(x), max(x), min(y), max(y)
    plt.xlim(minx, maxx)
    plt.ylim(miny, maxy)
    plt.plot(x, y, 'k--', marker='+')


def matching():
    read_xml('ls.xml')
    draw_map()
    traj_order = traj.load_lishui_taxi('traj1.txt')
    draw_trace(traj_order)

    traj_mod = POINT_MATCH(traj_order)
    # draw_points(traj_mod)


fig = plt.figure(figsize=(16, 8))
ax = fig.add_subplot(111)
matching()
plt.show()
