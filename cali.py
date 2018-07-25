# -*- coding: utf-8 -*-
# @Time    : 2018/6/4 14:11
# @Author  : 
# @简介    : calibration
# @File    : cali.py

import json
import urllib2
import geo
import math
import matplotlib.pyplot as plt
rem_dic = {'秋石快速路南': [41, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69], '秋石快速路出口南': [28, 29, 30, 31],
           '秋涛北路南': [46, 47, 63, 64, 70, 71], '秋石快速路出口东': [20, 21, 22], '新天地街东': [26, 29],
           '德胜快速路出口南': [33, 34, 41 ,44],
           '新天地街隧道东': [8], '新业路西': [10, 11], '新天地街西': [14, 15], '秋石快速路入口南': [39]}
idx = 0
last_point = None
new_point = None
line_point = {}
line_line = {}


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
    global idx
    for step in steps:
        try:
            print idx, step['road'], step['orientation']
        except KeyError:
            print idx, '无名'
        idx += 1
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


def draw_1(trace, index):
    if len(trace) == 0:
        return
    x, y = zip(*trace)
    plt.plot(x, y, color='k')
    cnt = 0
    for i in range(0, len(x)):
        cnt += 1
        print index, cnt
        plt.text(x[i], y[i], '{0},{1}'.format(index, cnt))


def draw(trace, index, name):
    global new_point, last_point
    if len(trace) == 0:
        return
    x, y = zip(*trace)
    if index == 1:
        plt.plot(x[:len(x)-1], y[:len(x)-1], color='k')
    else:
        plt.plot(x[1:len(x)-1], y[1:len(x)-1], color='k')
    cnt = 0
    if index == 1:
        for i in range(0, len(x)-1):
            cnt += 1
            print index, cnt
            plt.text(x[i], y[i], '{0},{1}'.format(index, cnt))
    else:
        for i in range(1, len(x)-1):
            cnt += 1
            print index, cnt
            plt.text(x[i], y[i], '{0},{1}'.format(index, cnt))
    if index > 1 and last_point == [x[0], y[0]] and len(x) > 2:
        plt.plot([new_point[0], x[1]], [new_point[1], y[1]], color='k')
        plt.text(new_point[0], new_point[1], 'ooo')
        plt.text(x[1], y[1], 'ooo')
    last_point = [x[-1], y[-1]]
    if index == 1:
        new_point = [x[-2], y[-2]]
    else:
        if len(x) > 2:
            new_point = [x[-2], y[-2]]


def get_new_point(x, y, name):
    global line_point, line_line
    p_l = line_point[name]
    new_x = []
    new_y = []
    for i in range(0, len(x)):
        if [x[i], y[i]] not in p_l:
            new_x.append(x[i])
            new_y.append(y[i])
            line_point[name].append([x[i], y[i]])
    lines = line_line[name]
    if len(new_x) >= 2:
        for i in range(0, len(new_x)-1):
            p1 = [new_x[i], new_y[i]]
            p2 = [new_x[i+1], new_y[i+1]]
            if [p1, p2] not in lines:
                line_line[name].append([p1, p2])
    return tuple(new_x), tuple(new_y)


def draw_new(trace, index, name):
    global new_point, last_point
    if len(trace) == 0:
        return
    x, y = zip(*trace)
    # if len(x) <= 2:
    #     plt.plot(x, y, color='r')
    # else:
    if index == 1:
        new_x, new_y = get_new_point(x[:len(x) - 1], y[:len(x) - 1], name)
    else:
        new_x, new_y = get_new_point(x[1:len(x) - 1], y[1:len(x) - 1], name)
    print len(new_x)
    plt.plot(new_x, new_y, color='k')
    cnt = 0
    for i in range(0, len(new_x)):
        cnt += 1
        # print index, cnt
        plt.text(new_x[i], new_y[i], '{0},{1}'.format(index, cnt))

    global line_line
    lines = line_line[name]
    if index > 1 and last_point == [x[0], y[0]] and len(x) > 2:
        if [new_point, [x[1], y[1]]] not in lines:
            plt.plot([new_point[0], x[1]], [new_point[1], y[1]], color='k')
            # plt.text(new_point[0], new_point[1], 'ooo')
            # plt.text(x[1], y[1], 'ooo')
            line_line[name].append([new_point, [x[1], y[1]]])
    last_point = [x[-1], y[-1]]
    if index == 1:
        new_point = [x[-2], y[-2]]
    else:
        if len(x) > 2:
            new_point = [x[-2], y[-2]]


def get_new_trace(trace, list):
    new_trace = []
    for i in trace:
        if i not in list:
            new_trace.append(i)
    return new_trace


def draw1(trace, index, name):
    global line_point
    p_list = line_point[name]
    if len(trace) == 0:
        return
    new_trace = get_new_trace(trace, p_list)
    if len(new_trace) == 0:
        return
    x, y = zip(*new_trace)
    plt.plot(x, y, color='k')
    cnt = 0
    for i in range(0, len(x)):
        cnt += 1
        print index, cnt
        plt.text(x[i], y[i], '{0},{1}'.format(index, cnt))
    for i in new_trace:
        line_point[name].append(i)


def get_name(s):
    items = s.strip('\n').split(' ')
    try:
        name = items[1] + items[2]
    except IndexError:
        return ""
    return name


def draw_repeat(trace, name):
    global line_line
    segments = line_line[name]
    for i in range(0, len(trace)-1):
        seg = (trace[i], trace[i+1])
        if seg not in segments:
            line_line[name].append(seg)


def line_dict_pro(dic):
    for i in dic:
        lines = dic[i]
        for line in lines:
            draw_repeat(line, i)


def show_amap():
    fig1 = plt.figure(figsize=(12, 6))
    ax = fig1.add_subplot(111)
    line_dic = {}
    fp = open('./2.txt')
    fp_lines = fp.readlines()
    global line_point, line_line
    for i, line in enumerate(fp_lines[1:len(fp_lines):2]):
        name = get_name(fp_lines[i * 2])
        # if name != '新天地街东':
        #     continue
        line_point[name] = []
        line_line[name] = []
        pts = line.strip('\n').split(';')
        pt_list = []
        for pt in pts:
            lng, lat = pt.split(',')[0:2]
            px, py = geo.bl2xy(lat, lng)
            pt_list.append([px, py])
        if name not in line_dic:
            line_dic[name] = []
        line_dic[name].append(pt_list)

    line_dict_pro(line_dic)

    for name in line_line:
        segs = line_line[name]
        cnt = 0
        print name
        if name in rem_dic:
            rem_num = rem_dic[name]
            for i in segs:
                cnt += 1
                if cnt in rem_num:
                    continue
                plt.plot([i[0][0], i[1][0]], [i[0][1], i[1][1]], color='k')
                plt.text(i[0][0], i[0][1], '{0}'.format(cnt))
            plt.subplots_adjust(left=0.06, right=0.98, bottom=0.05, top=0.96)
            plt.show()
        else:
            for i in segs:
                cnt += 1
                plt.plot([i[0][0], i[1][0]], [i[0][1], i[1][1]], color='k')
                plt.text(i[0][0], i[0][1], '{0}'.format(cnt))
            plt.subplots_adjust(left=0.06, right=0.98, bottom=0.05, top=0.96)
            plt.show()


show_amap()


