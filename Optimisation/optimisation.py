import numpy as np
import math
import pandas as pd
import matplotlib.pyplot as plt

import osmnx as ox
import networkx as nx
from pyproj import CRS
from shapely.strtree import STRtree
from shapely.geometry import Point

from time import perf_counter
from scipy.stats import ttest_ind

from rdd import *

import warnings
warnings.filterwarnings("ignore")

# set process mode
mode = "stats"

# import and pre-process travel graph
G = ox.load_graphml('../Mapping/data/London.graphml')
nodes, edges = ox.graph_to_gdfs(G)
projection = CRS.from_epsg(3067)
nodes = nodes.to_crs(projection)
edges = edges.to_crs(projection)
# print(f"London travel graph has {len(edges)} edges connecting {len(nodes)} nodes.")

# BIKE PARAMS
g = 9.81
Cd = 0.7
A = 0.5
Cr = 0.001
ro = 1.225
n_mech = 0.97
n_elec = 0.72

def segment_power(v, d_height, l):
    '''
    Returns the power required to traverse a given road segment.

            Parameters:
                    v (float): The travel velocity, m/s
                    d_height (float): The change of height over the road segment, m
                    l (float): The length of the road segment, m

            Returns:
                    power (float): Total required power to traverse the segment, W
    '''
    P_g = g * m * d_height/l * v
    P_a = 0.5 * Cd * ro * A * v**3
    P_f = Cr * m * g * v
    return max(P_g + P_a + P_f, 0) # avoid flooring effects with downhill slopes

def kph_to_mps(kmh):
    '''
    Returns the velocity in m/s.

            Parameters:
                    v (float): The travel velocity, km/h

            Returns:
                    v (float): The travel velocity, m/s
    '''
    return kmh/3600 * 1000

def hr_ss(hr_0, power, t, c):
    '''
    Returns the individual's heart rate at the end of the road segment.

            Parameters:
                    hr_0 (float): The heart rate at the start of the segment, bpm
                    power (float): The power exerted, W
                    t (float): The length of the road segment, seconds
                    c (float): Rise parameter for HR with power, bpm/W

            Returns:
                    hr (float): Estimated HR at the end of the road segment, bpm
    '''

    hr_ss = hr_0 + c*power
    if hr_ss > hr_max:
        return hr_max

    hr = hr_ss + (hr_0 - hr_ss) * pow(math.e, -t)
    if hr < hr_ss:
        return hr

    return hr_ss

def segment_hr(cyclist_power, hr_0, c, t=10, power_history=[]):
    '''
    Returns the HR at the end of a road segment.

            Parameters:
                    cyclist_power (float): The power required to traverse the segment, W
                    hr_0 (float): The heart rate at the beginning of the segment, bpm
                    c (float): Rise parameter for HR with power, bpm/W
                    t (float): The length of the road segment, seconds
                    power_history (list of floats): A list of any previous segments' power outputs

            Returns:
                    hr (float): Estimated HR at the end of the road segment, bpm
    '''

    percieved_power = cyclist_power + kf * sum(power_history)
    return hr_ss(hr_0, percieved_power, t, c)

def segment_pm(v, d_height, l, hr_0, Tr, c, sex, ambient_pm, power_history=[]):
    '''
    Returns the RDD experienced the road segment. Wrapper for rdd.py/calc_rdd()

            Parameters:
                    v (float): The travel velocity, m/s
                    d_height (float): The change of height over the road segment, m
                    l (float): The length of the road segment, m
                    hr_0 (float): The heart rate at the beginning of the segment, bpm
                    Tr (float): The rise time of the individual's HR with step change in power, s
                    c (float): Rise parameter for HR with power, bpm/W
                    sex (float): Individual's sex 'M' or 'F'
                    ambient_pm (float): The concentration of PM2.5 on the segment, ug/m3
                    power_history (list of floats): A list of any previous segments' power outputs


            Returns:
                    RDD (float): Recieved deposition dose over the period of interest, ug
    '''

    cyclist_power = segment_power(v, d_height, l) / n_mech
    hr = segment_hr(cyclist_power, hr_0, c, (v/l)/Tr, power_history)
    return calc_rdd(sex, hr, l/v, ambient_pm)


ambient_pm = 10 # ug/m3
# SUBJECT
# subjects = {'a': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 20, 'color': 'g'},
#             'b': {'hr_0': 100, 'm': 100, 'Tr': 30, 'hr_max': 180, 'c': 0.45, 'kf': 6e-5, 'sex': 'M', 'v': 20, 'color': 'b'}}

# VELOCITY
subjects = {'a_slow': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 15, 'color': 'g'},
            'a_fast': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 25, 'color': 'r'}}

# THREE-FOLD COMPARISON
# subjects = {'a': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 15, 'color': 'g'},
#             'b': {'hr_0': 100, 'm': 100, 'Tr': 30, 'hr_max': 180, 'c': 0.45, 'kf': 6e-5, 'sex': 'M', 'v': 15, 'color': 'b'},
#             'c': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 25, 'color': 'r'}}

t0 = perf_counter()
# iterate through every node to calculate the weights for each subject
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
        data['rdd_'+subject] = segment_pm(kph_to_mps(v), d_height, data['length'], hr_0, Tr, c, sex, ambient_pm, [])

        data['speed_kph_'+subject] = v
        distance_km = data['length'] / 1000
        speed_km_sec = data['speed_kph_'+subject] / (60 * 60)
        data['travel_time_'+subject] = distance_km / speed_km_sec
print(f"Time elapsed to calculate graph weights:\t{perf_counter()-t0} s")

# save graph weights
# ox.save_graphml(G, '../Mapping/data/London_pm.graphml')

# randomly generate and plot ten routes for each subject
if mode == "random":
    for j in range(10):
        print(f"JOURNEY {j}:")
        if j == -1:
            G2 = ox.project_graph(G, to_crs='4326') 
            orig = ox.get_nearest_node(G2, (51.51789, -0.08308), return_dist=False)
            dest = ox.get_nearest_node(G2, (51.499824,-0.174377), return_dist=False)
        
        else:
            orig = list(G)[np.random.randint(len(list(G)))]
            dest = orig
            while dest == orig:
                dest = list(G)[np.random.randint(len(list(G)))]

        routes = []
        colors = []
        # short = ox.shortest_path(G, orig, dest, weight='travel_time_a')
        for subject in subjects.keys():
            weight = 'rdd_'+subject
            route = ox.shortest_path(G, orig, dest, weight=weight)

            if route is None: continue
            routes.append(route)
            colors.append(subjects[subject]['color'])

            rdd = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, 'rdd_'+subject)))
            distance = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, 'length')))
            energy = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, 'energy_'+subject)))
            traveltime = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, 'travel_time_'+subject)))

            print(f"\tRoute {subject} corresponds to inhaling {rdd:.2f} ug of PM2.5, exerting {energy:.2f} J over {traveltime/60:.2f} minutes, covering {distance:.2f} m")

        fig, ax = ox.plot_graph_routes(G, routes=routes, route_colors=colors, node_size=0, figsize=(24,16), show=False)
        ax.set_axis_off()

        fig.savefig('img_fit/route_'+str(j)+'.png', dpi=300, bbox_inches='tight', transparent=True)

# generate and plot routes for each subject in the commute monitoring study's commute
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

# conduct statistical analysis of the routes for each subject
elif mode == "stats":
    rdd_dict = {'rdd_a_slow': [], 'rdd_a_fast': []}

    for j in range(500):
        orig = list(G)[np.random.randint(len(list(G)))]
        dest = orig
        while dest == orig:
            dest = list(G)[np.random.randint(len(list(G)))]

        for subject in subjects.keys():
            weight = 'rdd_'+subject
            route = ox.shortest_path(G, orig, dest, weight=weight)
            
            if route is None: continue

            rdd = (np.sum(ox.utils_graph.get_route_edge_attributes(G, route, weight)))
            rdd_dict[weight].append(rdd)

    print(f"A: {np.mean(rdd_dict['rdd_a_slow'])} ug m-3\tB: {np.mean(rdd_dict['rdd_a_fast'])} ug m-3")
    print(ttest_ind(rdd_dict['rdd_a_slow'], rdd_dict['rdd_a_fast'], alternative='greater'))
