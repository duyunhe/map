# -*- coding: utf-8 -*-
# @Time    : 2018/2/27 14:36
# @Author  : wf
# @简介    : 最短路径
# @File    : route.py
import urllib2
import json
import ctypes as c


class BLH(c.Structure):
    _fields_ = [
        ("b", c.c_double),
        ("l", c.c_double),
        ("h", c.c_double),
    ]


class xyH(c.Structure):
    _fields_ = [
        ("x", c.c_double),
        ("y", c.c_double),
        ("h", c.c_double),
    ]


def coordtran(Lat, Long):

    # load dll and get the function object
    dll = c.windll.LoadLibrary('D:/map/CoordTransDLL.dll')  # dll path
    WGS84_BLH_2_HZ_xyH = dll.WGS84_BLH_2_HZ_xyH
    # set the return type
    WGS84_BLH_2_HZ_xyH.restype = c.c_int
    # set the argtypes
    WGS84_BLH_2_HZ_xyH.argtypes = [BLH, c.POINTER(xyH)]
    objectStruct = BLH(Lat, Long, 0.0)
    result = xyH()
    # invoke api GetStructInfo
    retStr = WGS84_BLH_2_HZ_xyH(objectStruct, c.byref(result))
    x = result.x
    y = result.y
    h = result.h
    return x, y, h


def coord_xy_to_bl(x, y):
    dll = c.windll.LoadLibrary('CoordTransDLL.dll')
    HZ_xyH_2_WGS84_BLH = dll.HZ_xyH_2_WGS84_BLH
    HZ_xyH_2_WGS84_BLH.restype = c.c_int
    HZ_xyH_2_WGS84_BLH.argtypes = [xyH, c.POINTER(BLH)]
    objectStruct = xyH(x, y, 0.0)
    result = BLH()
    retStr = HZ_xyH_2_WGS84_BLH(objectStruct, c.byref(result))
    B = result.b
    L = result.l
    H = result.h
    return B, L, H


def get_route(p1, p2, pp):
    # u = 'http://restapi.amap.com/v3/direction/driving?' \
    #     'origin=116.481028,39.989643&destination=116.465302,40.004717&extensions=all&output=xml&key=<用户的key>'
    url = 'http://restapi.amap.com/v3/direction/driving?'
    key = '0a54a59bdc431189d9405b3f2937921a'
    uri = url + 'origin=' + p1 + '&destination=' + p2 + '&waypoints=' + pp + '&strategy=2' + '&extensions=all' + '&output=JSON' + '&key=' + key
    # + '&waypoints=' + pp
    temp = urllib2.urlopen(uri)
    temp = json.loads(temp.read())
    list0 = temp['route']['paths'][0]['distance']
    return list0


def get_route1(p1, p2):
    # u = 'http://restapi.amap.com/v3/direction/driving?' \
    #     'origin=116.481028,39.989643&destination=116.465302,40.004717&extensions=all&output=xml&key=<用户的key>'
    url = 'http://restapi.amap.com/v3/direction/driving?'
    key = '0a54a59bdc431189d9405b3f2937921a'
    uri = url + 'origin=' + p1 + '&destination=' + p2 + '&strategy=2' + '&extensions=all' + '&output=JSON' + '&key=' + key
    temp = urllib2.urlopen(uri)
    temp = json.loads(temp.read())
    list0 = temp['route']['paths'][0]['distance']
    return list0


def dis_measure(p1, p2):
    url = 'http://restapi.amap.com/v3/distance?'
    key = '0a54a59bdc431189d9405b3f2937921a'
    uri = url + 'origins=' + p1 + '&destination=' + p2 + '&type=0' + '&output=JSON' + '&key=' + key
    temp = urllib2.urlopen(uri)
    temp = json.loads(temp.read())
    list0 = temp['results'][0]['distance']
    return list0
# B, L, H = coord_xy_to_bl(-117587.379655, 58313.7994092)  # 143
# B1, L1, H1 = coord_xy_to_bl(-117714.236518, 58363.237168)  # 144
fp = open('point.txt')
cnt = 0
star = 0
d = 0
pp = 0
for line in fp.readlines():
    items = line.strip('\n').split(',')
    # _, px, py, speed, azi, state, speed_time = new_items
    longi, lati= map(float, items)
    B, L, H = coord_xy_to_bl(lati, longi)
    if cnt == 0:
        star = '%.6f' % L+','+'%.6f' % B
        print 'star', (L, B)
        pp = star
        cnt += 1
        continue
    else:
        p = '%.6f' % L+','+'%.6f' % B
        cnt += 1
    print cnt, star, pp, p
    if cnt == 33 or cnt == 34 or cnt == 35:
        print
    dis = get_route(star, p, pp)
    dis1 = get_route1(pp, p)
    dis2 = dis_measure(pp, p)
    pp = p
    cd = int(dis) - d
    d = int(dis)
    if cd != int(dis1) and abs(cd - int(dis1)) > 5 and (abs(cd)-int(dis2)) > 10:
    # if cd != int(dis1) and abs(cd - int(dis1)) > 5:
        print cd, int(dis1), dis2
