import numpy as np
import math
import random
import pandas as pd
import geopandas
import matplotlib.pyplot as plt

import osmnx as ox
import networkx as nx
from pyproj import CRS
from shapely.strtree import STRtree
from shapely.geometry import Point

import requests
from time import perf_counter

from rdd import *

import warnings
warnings.filterwarnings("ignore")

mode = "random"

G = ox.load_graphml('../Mapping/data/London.graphml')
nodes, edges = ox.graph_to_gdfs(G)
projection = CRS.from_epsg(3067)
nodes = nodes.to_crs(projection)
edges = edges.to_crs(projection)
print(f"London travel graph has {len(edges)} edges connecting {len(nodes)} nodes.")

# BIKE PARAMS
g = 9.81
Cd = 0.7
A = 0.5
Cr = 0.001
ro = 1.225
n_mech = 0.97
n_elec = 0.72

"""
OPTIMISATION THOUGHTS:
    MINIMISE:
        TOTAL POLLUTION INHALATION (ROUTE, SPEED, ASSISTANCE) + TIME (ROUTE, SPEED)
    SUBJECT TO:
        TOTAL POWER <= ENERGY BUDGET

"""

def segment_power(v, d_height, l):
    # sin theta = O/H = (H2 - H1)/l
    P_g = g * m * d_height/l * v
    P_a = 0.5 * Cd * ro * A * v**3
    P_f = Cr * m * g * v
    return max(P_g + P_a + P_f, 0) # avoid flooring effects with downhill slopes

def kph_to_mps(kmh):
    return kmh/3600 * 1000

def hr_ss(hr_0, power, t):
    hr_ss = hr_0 + c*power
    if hr_ss > hr_max:
        return hr_max
    hr = hr_ss + (hr_0 - hr_ss) * pow(math.e, -t)
    if hr < hr_ss:
        return hr
    return hr_ss

def segment_hr(cyclist_power, hr_0, t=10, power_history=[]):
    percieved_power = cyclist_power + kf * sum(power_history)
    return hr_ss(hr_0, percieved_power, t)

def segment_pm(assistance, v, d_height, l, hr_0, Tr, ambient_pm, power_history=[]):
    cyclist_power = (1-assistance) * segment_power(v, d_height, l) / n_mech
    hr = segment_hr(cyclist_power, hr_0, (v/l)/Tr, power_history)
    return calc_rdd(sex, hr, l/v, ambient_pm), cyclist_power


def cost_fn(rdd, time):
    return 0.05*rdd**2 + 0.5*(time/60)


# # USER PARAMS
# m = 90
# Tr = 24/60 # between 24 and 30s
# hr_0 = 80 # between 60 and 100
# hr_max = 180 # usually calculated 220 - age
# c = 0.15 # between 0.15 and 0.45
# kf = 3e-5 # between 1 and 6 e-5
# sex = 'M'

ambient_pm = 10 # ug/m3
# subjects = {'a': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 20},
#             'b': {'hr_0': 100, 'm': 100, 'Tr': 30, 'hr_max': 180, 'c': 0.45, 'kf': 6e-5, 'sex': 'M', 'v': 20}}
# subjects = {'a': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 25},
#             'b': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 15}}
subjects = {'a': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 20},
            'b': {'hr_0': 100, 'm': 100, 'Tr': 30, 'hr_max': 180, 'c': 0.45, 'kf': 6e-5, 'sex': 'M', 'v': 20},
            'c': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 15}}


t0 = perf_counter()
for source, sink, _, data in G.edges(keys=True, data=True):
    d_height = nodes.loc[sink]['elevation'] - nodes.loc[source]['elevation']
    for subject in subjects.keys():
        m = subjects[subject]['m']
        Tr = subjects[subject]['Tr']
        hr_0 = subjects[subject]['hr_0']
        hr_max = subjects[subject]['hr_max']
        c = subjects[subject]['c']
        kf = subjects[subject]['kf']
        sex = subjects[subject]['sex']
        v = subjects[subject]['v']

        data['energy_'+subject] = segment_power(kph_to_mps(v), d_height, data['length']) * (data['length'] / kph_to_mps(v))
        data['rdd_'+subject] = segment_pm(0, kph_to_mps(v), d_height, data['length'], hr_0, Tr, ambient_pm, [])[0]

        data['speed_kph_'+subject] = v
        distance_km = data['length'] / 1000
        speed_km_sec = data['speed_kph_'+subject] / (60 * 60)
        data['travel_time_'+subject] = distance_km / speed_km_sec

        data['cost_'+subject] = cost_fn(data['rdd_'+subject], data['travel_time_'+subject])
print(f"Time elapsed to calculate graph weights:\t{perf_counter()-t0} s")


# ox.save_graphml(G, '../Mapping/data/London_pm.graphml')

if mode == "random":
    for j in range(10):
        print(f"JOURNEY {j}:")
        orig = list(G)[np.random.randint(len(list(G)))]
        dest = orig
        while dest == orig:
            dest = list(G)[np.random.randint(len(list(G)))]

        # short = ox.shortest_path(G, orig, dest, weight='travel_time_a')
        pma = ox.shortest_path(G, orig, dest, weight='cost_a')
        pmb = ox.shortest_path(G, orig, dest, weight='cost_b')
        routes = [pma, pmb]

        for i, route in enumerate(routes):
            if route is None: continue

            rdd = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "rdd_a")))
            distance = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "length")))
            if i == 1:
                energy = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "energy_b")))
                traveltime = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "travel_time_b")))
            else:
                energy = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "energy_a")))
                traveltime = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "travel_time_a")))

            print(f"\tRoute {i} corresponds to inhaling {rdd:.2f} ug of PM2.5, exerting {energy:.2f} J over {traveltime/60:.2f} minutes, covering {distance:.2f} m")

        fig, ax = ox.plot_graph_routes(G, routes=routes, route_colors=['g','b'], node_size=0, figsize=(24,16), show=False)
        ax.set_axis_off()

        fig.savefig('img_fit/route_'+str(j)+'.png', dpi=300, bbox_inches='tight', transparent=True)

elif mode == "commute":
    subjects = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}
    origins = {'A': {'lat': 51.51789, 'lng': -0.08308}, 'B': {'lat': 51.45396, 'lng': -0.17366},  'C': {'lat': 51.517333, 'lng': -0.250967}}
    destination = {'lat': 51.499824, 'lng': -0.174377}
    G2 = ox.project_graph(G, to_crs='4326') 

    point = (destination['lat'], destination['lng'])
    dest_node = ox.get_nearest_node(G2, point, return_dist=False)

    routes = []

    for pt in origins.values():
        point = (pt['lat'], pt['lng'])
        node = ox.get_nearest_node(G2, point, return_dist=False)
        
        routes.append(ox.shortest_path(G, node, dest_node, weight='rdd_a'))
        # routes.append(ox.shortest_path(G, node, dest_node, weight='travel_time_a'))

    for i, route in enumerate(routes):
        if route is None: continue

        rdd = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "rdd_a")))
        distance = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "length")))
        energy = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "energy_a")))
        traveltime = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "travel_time_a")))

        print(f"\tRoute {subjects[i]} corresponds to inhaling {rdd:.2f} ug of PM2.5, exerting {energy:.2f} J over {traveltime/60:.2f} minutes, covering {distance:.2f} m")

    fig, ax = ox.plot_graph_routes(G, routes=routes, route_colors=['r','g','b'], node_size=0, figsize=(24,16), show=False)
    ax.set_axis_off()

    fig.savefig('commute_routes.png', dpi=300, bbox_inches='tight', transparent=True)

else:
    origins = {'lat': 51.51789, 'lng': -0.08308}
    destination = {'lat': 51.499824, 'lng': -0.174377}
    G2 = ox.project_graph(G, to_crs='4326') 

    point = (destination['lat'], destination['lng'])
    dest_node = ox.get_nearest_node(G2, point, return_dist=False)

    point = (origins['lat'], origins['lng'])
    orig_node = ox.get_nearest_node(G2, point, return_dist=False)

    routes = []

    for subject in subjects.keys():
        weight_attr = 'rdd_'+subject
        route = ox.shortest_path(G, orig_node, dest_node, weight=weight_attr)
        routes.append(route)

        rdd = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "rdd_a")))
        distance = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "length")))
        energy = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "energy_a")))
        traveltime = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, "travel_time_a")))

        print(f"\tRoute {subjects} corresponds to inhaling {rdd:.2f} ug of PM2.5, exerting {energy:.2f} J over {traveltime/60:.2f} minutes, covering {distance:.2f} m")

    fig, ax = ox.plot_graph_routes(G, routes=routes, route_colors=['r','g','b'], node_size=0, figsize=(24,16), show=False)
    ax.set_axis_off()

    fig.savefig('fit_unfit_slow.png', dpi=300, bbox_inches='tight', transparent=True)



# print(f"To ascend {d_height}m over {length}m at {v}km/h, it takes {segment_power(kph_to_mps(v), d_height, length):.2f} W")
# print(f"To ascend {-d_height}m over {length}m at {v}km/h, it takes {segment_power(kph_to_mps(v), -d_height, length):.2f} W")
# print(f"If ambient PM is {ambient_pm}ug/m3, {assistance*100}% assistance results in {segment_pm(assistance, kmh_to_mps(v), d_height, length, hr_0, ambient_pm, power_history=[]):.2f} ug of deposited PM2.5")
# assistance = 0
# print(f"If ambient PM is {ambient_pm}ug/m3, {assistance*100}% assistance results in {segment_pm(assistance, kmh_to_mps(v), d_height, length, hr_0, ambient_pm, power_history=[]):.2f} ug of deposited PM2.5")

# print(route_pm([1, 2, 4, 3, 5], [random.randint(1,50)/100 for x in range(5)], [kph_to_mps(15)]*5))
# print(route_pm([1, 2, 4, 3, 5], [0.25]*5, [kph_to_mps(20)]*5))