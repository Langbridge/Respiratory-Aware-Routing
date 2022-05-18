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
import time

from rdd import *

import warnings
warnings.filterwarnings("ignore")

G = ox.load_graphml('../Mapping/data/London.graphml')
nodes, edges = ox.graph_to_gdfs(G)
projection = CRS.from_epsg(3067)
nodes = nodes.to_crs(projection)
edges = edges.to_crs(projection)

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
        TOTAL POLLUTION INHALATION (ROUTE, ASSISTANCE)
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

def hr_ss(hr_0, power):
    hr = hr_0 + c*power
    if hr > hr_max:
        return hr_max
    return hr

def segment_hr(cyclist_power, hr_0, power_history=[]):
    # TODO: split this into some sort of time segmented thing
    # right now I think it's doing some weird shit lumping the whole power output as one HR step?
    percieved_power = cyclist_power + kf * sum(power_history)
    return hr_ss(hr_0, percieved_power)

def segment_pm(assistance, v, d_height, l, hr_0, ambient_pm, power_history=[]):
    cyclist_power = (1-assistance) * segment_power(v, d_height, l) / n_mech
    hr = segment_hr(cyclist_power, hr_0, power_history)
    # print(f"\tHeart Rate: {hr:.2f} bpm")
    return calc_rdd(sex, hr, l/v, ambient_pm), cyclist_power

def route_pm(route, assistance, v):
    power_history = []
    assist_power = []
    route_rdd = []
    total_assistance = 0

    # route = node list [(u, v, key), (u, v, key), ...]
    for i in range(len(route)):
        print(f"Leg {i+1}:")
        l = random.randint(20,100) #edges.loc[route[i], 'length']
        d_height = (random.randint(1,60) - 30)/1000 #edges.loc[route[i], 'grade'] * l
        print(f"\t{l}m at {d_height*100:.2f}% grade with {assistance[i]*100:.2f}% assistance")
        rdd, cycle_power = segment_pm(assistance[i], v[i], d_height, l, hr_0, ambient_pm, power_history)
        assist_power.append(cycle_power/(1-assistance[i]) * assistance[i] / n_elec)
        power_history.append(cycle_power)
        route_rdd.append(rdd)
    print(f"Total assistance: {sum(assist_power):.2f}W, {sum(assist_power)/(sum(assist_power)+sum(power_history))*100:.2f}%")
    print(f"Total RDD: {sum(route_rdd):.2f} ug")
    return route_rdd

# # USER PARAMS
# m = 90
# Tr = 24/60 # between 24 and 30s
# hr_0 = 80 # between 60 and 100
# hr_max = 180 # usually calculated 220 - age
# c = 0.15 # between 0.15 and 0.45
# kf = 3e-5 # between 1 and 6 e-5
# sex = 'M'

ambient_pm = 10 # ug/m3
subjects = {'a': {'hr_0': 60, 'm': 90, 'Tr': 30/60, 'hr_max': 180, 'c': 0.15, 'kf': 1e-5, 'sex': 'M', 'v': 20},
            'b': {'hr_0': 100, 'm': 100, 'Tr': 22/60, 'hr_max': 180, 'c': 0.45, 'kf': 6e-5, 'sex': 'M', 'v':15}}

for source, sink, _, data in G.edges(keys=True, data=True):
    # print(source['elevation'])
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
        data['rdd_'+subject] = segment_pm(0, kph_to_mps(v), d_height, data['length'], hr_0, ambient_pm, [])[0]

        data['speed_kph_'+subject] = v
        data['travel_time_'+subject] = data['length'] / kph_to_mps(data['speed_kph']) / 60
        data['cost_'+subject] = 0.75*data['rdd_'+subject] + 0.25*data['travel_time_'+subject]

ox.save_graphml(G, '../Mapping/data/London_pm.graphml')

# CHECK NEGATIVE GRADE EFFECTS
# GET CHRIS TO REMIND ME HOW TO GITHUB THIS

# print(f"To ascend {d_height}m over {length}m at {v}km/h, it takes {segment_power(kph_to_mps(v), d_height, length):.2f} W")
# print(f"To ascend {-d_height}m over {length}m at {v}km/h, it takes {segment_power(kph_to_mps(v), -d_height, length):.2f} W")
# print(f"If ambient PM is {ambient_pm}ug/m3, {assistance*100}% assistance results in {segment_pm(assistance, kmh_to_mps(v), d_height, length, hr_0, ambient_pm, power_history=[]):.2f} ug of deposited PM2.5")
# assistance = 0
# print(f"If ambient PM is {ambient_pm}ug/m3, {assistance*100}% assistance results in {segment_pm(assistance, kmh_to_mps(v), d_height, length, hr_0, ambient_pm, power_history=[]):.2f} ug of deposited PM2.5")

# print(route_pm([1, 2, 4, 3, 5], [random.randint(1,50)/100 for x in range(5)], [kph_to_mps(15)]*5))
# print(route_pm([1, 2, 4, 3, 5], [0.25]*5, [kph_to_mps(20)]*5))