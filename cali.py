# -*- coding: utf-8 -*-
# @Time    : 2018/6/4 14:11
# @Author  : 
# @简介    : calibration
# @File    : cali.py

import json
import urllib2
import geo
import math


def point_to_addr(tr):
    url = "http://restapi.amap.com/v3/direction/driving?" \
          "origin={0},{1}&destination={2},{3}&strategy=2" \
          "&output=json&key=0a54a59bdc431189d9405b3f2937921a".format(tr[0][0], tr[0][1],
                                                                     tr[-1][0], tr[-1][1])
    # url += "&waypoints="
    # for i, data in enumerate(tr[1:-1]):
    #     if i == 0:
    #         s = "{0},{1}".format(data[0], data[1])
    #     else:
    #         s = ";{0},{1}".format(data[0], data[1])
    #     url += s

    temp = urllib2.urlopen(url)
    temp = json.loads(temp.read())
    route = temp['route']
    path = route['paths'][0]
    dist = int(path['distance'])
    steps = path['steps']
    for step in steps:
        print step['instruction']
        print step['polyline']
    return dist


def load_trace():
    fp = open('./data/1.txt')
    lx, ly, dist = -1, -1, 0
    trace_list = []
    for line in fp.readlines():
        item = line.strip('\n').split(',')
        px, py = map(float, item[0:2])
        lng, lat = map(float, item[2:4])
        lng, lat = round(lng, 6), round(lat, 6)
        if lx != -1:
            d = geo.calc_dist([px, py], [lx, ly])
            dist += d
        lx, ly = px, py
        trace_list.append([lng, lat])
    split_len = int(math.ceil(len(trace_list) / 16.0))
    t_list = [trace_list[0]]
    sp_list = trace_list[1:-1:split_len]
    t_list.extend(sp_list)
    t_list.append(trace_list[-1])
    return trace_list, dist


def amap():
    trace, total_dist = load_trace()
    print total_dist
    dist2 = 0
    for i, data in enumerate(trace[:-1]):
        od = [data, trace[i + 1]]
        dist2 += point_to_addr(od)
    print dist2


def show_amap():


