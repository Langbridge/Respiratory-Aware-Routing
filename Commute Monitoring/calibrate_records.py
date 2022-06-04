import pandas as pd
import geopandas
import datetime as dt
import numpy as np
import os
from tensorflow import keras
import matplotlib.pyplot as plt

import osmnx as ox
import networkx as nx
from shapely.geometry import Point

import warnings
warnings.filterwarnings("ignore")

subject_list = ['A', 'B', 'C', 'D']
model = keras.models.load_model('../MY Monitoring/deep_model2')

G = ox.load_graphml('../Mapping/data/London.graphml')
nodes, edges = ox.graph_to_gdfs(G)
edges['Mean PM2.5'] = np.nan
edges['PM2.5 Count'] = 0
G = ox.project_graph(G, to_crs='4326') 
print(f'Loaded graph success.')

log = pd.DataFrame(columns=['subject', 'file', 'date', 'commute', 'min', 'Q25', 'mean', 'Q75', 'max'])

for subject in subject_list:
    print(subject)
    directory = os.path.join(subject+'/Cleaned/')
    for root,dirs,files in os.walk(directory):
        for file in files:
            if file.endswith(".csv"):
                raw_data = pd.read_csv(directory+file)

                model_df = raw_data.set_index('WriteTime')
                model_df.index = pd.to_datetime(model_df.index)
                model_df.rename(columns={'Temp': 'Temperature', 'RH': 'Relative Humidity'}, inplace=True)

                model_df['Delay'] = model_df['PM2.5'].shift(periods=1)
                model_df['Hour'] = model_df.index.hour
                model_df['Day'] = model_df.index.weekday
                model_df.dropna(inplace=True)

                lats = model_df['Lat'].to_list()
                lngs = model_df['Lng'].to_list()
                train_df = model_df[['Temperature','Relative Humidity','PM2.5','PM10', 'Delay', 'Hour', 'Day']]

                model_df['Calibrated PM2.5'] = model.predict(train_df)
                model_df.loc[model_df['Calibrated PM2.5'] > 85.0, 'Calibrated PM2.5'] = 85.0
                model_df.to_csv(subject+'/Calibrated/'+file)

                log_data = {'subject': subject, 'file': file, 'date': model_df.index[0], 'commute': file[4:6],
                            'min': model_df['Calibrated PM2.5'].min(), 'Q25': model_df['Calibrated PM2.5'].quantile(q=0.25),
                            'mean': model_df['Calibrated PM2.5'].mean(), 'Q75': model_df['Calibrated PM2.5'].quantile(q=0.75),
                            'max': model_df['Calibrated PM2.5'].max()}
                log = log.append(log_data, ignore_index=True)

                ax = model_df[['PM2.5', 'Calibrated PM2.5']].plot(ylabel='PM2.5, ug/m3', figsize=(18,12), color=['gray','blue'])
                fig = ax.get_figure()
                fig.savefig(subject+'/img/'+file[:-4]+'_calibrated.png', dpi=300, bbox_inches='tight')
                
                points_list = [Point((lng, lat)) for lat, lng in zip(lats, lngs)]
                points = geopandas.GeoSeries(points_list, crs='epsg:4326')
                nearest_edges = ox.nearest_edges(G, [pt.x for pt in points], [pt.y for pt in points])

                pts = geopandas.GeoDataFrame({'Geometry': points, 'Nearest Edge': nearest_edges, 'PM2.5': model_df['Calibrated PM2.5'].to_list()})

                edge_pollute = pts.groupby(['Nearest Edge']).first()
                edge_pollute['PM2.5'] = pts.groupby(['Nearest Edge']).mean()
                edge_pollute.index = pd.MultiIndex.from_tuples(edge_pollute.index, names=('u', 'v', 'key'))

                edges['PM2.5'] = np.nan
                edges.loc[edge_pollute.index, 'PM2.5'] = edge_pollute['PM2.5']
                for idx in edge_pollute.index:
                    if edges.loc[idx, 'PM2.5 Count'] != 0:
                        edges.loc[idx, 'Mean PM2.5'] = (edges.loc[idx, 'Mean PM2.5']*edges.loc[idx, 'PM2.5 Count'] + edge_pollute.loc[idx, 'PM2.5']) / (edges.loc[idx, 'PM2.5 Count'] + 1)
                    else:
                        edges.loc[idx, 'Mean PM2.5'] = edge_pollute.loc[idx, 'PM2.5']
                    edges.loc[idx, 'PM2.5 Count'] += 1

                fig, ax = plt.subplots(figsize=(24,16))
                ax.set_axis_off()
                edges.plot(ax=ax, linewidth=0.5, edgecolor='dimgray')
                edges.loc[pts['Nearest Edge']].plot(ax=ax, linewidth=1.5, column='PM2.5', cmap='inferno', legend=True, vmax=model_df['Calibrated PM2.5'].quantile(q=0.9),
                                                    legend_kwds={'label': "PM2.5 (ug / m3)", 'orientation': "vertical"})
                fig.savefig(subject+'/img/'+file[:-4]+'_calibrated_route.png', dpi=300, bbox_inches='tight', transparent=True)

edges['Mean PM2.5'] = edges['Mean PM2.5'].apply(lambda x: np.mean(x))

fig, ax = plt.subplots(figsize=(24,16))
ax.set_axis_off()
edges.plot(ax=ax, linewidth=0.5, edgecolor='dimgray')
edges[edges['Mean PM2.5'] != np.nan].plot(ax=ax, linewidth=1.5, column='Mean PM2.5', cmap='inferno', legend=True, vmax=17.5,
                                          legend_kwds={'label': "PM2.5 (ug / m3)", 'orientation': "vertical"})
fig.savefig('ldn_heatmap.png', dpi=300, bbox_inches='tight', transparent=True)

log.sort_values(by=['file'], inplace=True)
log.to_csv('calibration_log.csv')