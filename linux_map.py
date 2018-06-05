# -*- coding: utf-8 -*-
# @Time    : 2018/3/20 16:25
# @Author  : C.D.
# @简介    : show map
# @File    : linux_map.py

import matplotlib.pyplot as plt
from map_struct import MapNode, MapEdge
from geo import bl2xy


def edge2xy(e):
    x0, y0 = e.node0.point[0:2]
    x1, y1 = e.node1.point[0:2]
    nid0 = e.node0.nodeid
    nid1 = e.node1.nodeid
    return x0, y0, x1, y1, nid0, nid1


def draw_edge(e, c):
    x0, y0, x1, y1, nid0, nid1 = edge2xy(e)
    x, y = [x0, x1], [y0, y1]
    plt.plot(x, y, c, linewidth=1)
    plt.text((x[0] + x[-1]) / 2, (y[0] + y[-1]) / 2, '{0}'.format(e.edge_index))
    plt.text(x0, y0, '{0}'.format(nid0), color='m')
    plt.text(x1, y1, '{0}'.format(nid1), color='m')


def draw_node(n, c, pos, marker='o'):
    x = n.point[0]
    y = n.point[1]
    plt.plot(x, y, marker=marker, color=c)


def add_draw_node(node, edge_set):
    for e, _ in node.link_list:
        edge_set.add(e.edge_index)


fp_node = open('./map/node.csv')
fp_edge = open('./map/edge.csv')
fp = open('./data/point.txt')

node_list = [None]
edge_list = [None]

for line in fp_node.readlines():
    items = line.strip('\n').split(',')
    nid = items[0]
    lng, lat = map(float, items[1:3])
    px, py = bl2xy(lat, lng)
    node = MapNode([px, py], nid)
    node_list.append(node)

for line in fp_edge.readlines():
    items = line.strip('\n').split(',')
    eid = items[0]
    nid0, nid1 = map(int, items[1:3])
    node0, node1 = node_list[nid0], node_list[nid1]
    edge = MapEdge(node0, node1, True, int(eid), 0, 0)
    edge_list.append(edge)
    node0.add_link(edge, node1)
    node1.add_link(edge, node0)


edge_set = set()
idx = 0
for line in fp.readlines():
    items = line.strip('\n').split(',')
    px, py = map(float, items[0:2])
    eid = int(items[2])
    node = MapNode([px, py], idx)
    draw_node(node, 'r', idx)

    cx, cy = map(float, items[3:5])
    node1 = MapNode([cx, cy], idx)
    draw_node(node1, 'k', idx, '+')
    dist = float(items[5])
    plt.text(px + 0.5, py + 0.5, '{0},{1:.2f}'.format(idx, dist), color='r')
    idx += 1
    edge_set.add(eid)

add_draw_node(node_list[4693], edge_set)
for eid in edge_set:
    draw_edge(edge_list[eid], 'b')

plt.show()
