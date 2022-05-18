import osmnx as ox
import matplotlib.pyplot as plt
from pyproj import CRS

place_name = "Westminster, London, England"
graph = ox.graph_from_place(place_name, network_type='bike')
# fig, ax = ox.plot_graph(graph)

nodes, edges = ox.graph_to_gdfs(graph)
print(edges['highway'].value_counts())
# print(edges.head())

parks = ox.geometries_from_place(place_name, {"leisure": "park"})
# print(parks.head())

water = ox.geometries_from_place(place_name, {"waterway": "river"})

projection = CRS.from_epsg(3067)
edges = edges.to_crs(projection)
parks = parks.to_crs(projection)
water = water.to_crs(projection)

fig, ax = plt.subplots(figsize=(12,8))
parks.plot(ax=ax, facecolor="green")
water.plot(ax=ax, facecolor="blue")
edges.plot(ax=ax, linewidth=1, edgecolor='dimgray')
plt.tight_layout()

plt.show()