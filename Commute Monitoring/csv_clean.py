import pandas as pd
import datetime as dt
import numpy as np

import gpxpy
import gpxpy.gpx

# ----- PARAMS
subject = 'A'
raw_data_file = 'input.csv'
gpx_name = '2305PM.gpx'
true_time = dt.datetime(2022, 5, 23, 17, 5, 0) # can be found from Strava log - for subject B add 1H for BST

# ----- CODE
df = pd.read_csv(subject+'/'+raw_data_file)

date = pd.to_datetime(df.iloc[0]['WriteTime'], format="%d/%m/%Y", exact='False').date()
df.drop(index=0, inplace=True)
start_len = len(df)

df['WriteTime'] = pd.to_datetime(str(date) + ' ' + df['WriteTime'])
# df['WriteTime'] = pd.to_datetime(df['WriteTime'], format="%H:%M:%S")
for i in range(1, len(df)):
    if df.loc[len(df)-i, 'WriteTime'] == dt.datetime(year=date.year, month=date.month, day=date.day, hour=0, minute=0, second=0):
        df.loc[len(df)-i, 'WriteTime'] = df.loc[len(df)-i+1, 'WriteTime'] - dt.timedelta(seconds=3)

df['WriteTime'] = df['WriteTime'].apply(lambda x: x + dt.timedelta(hours=1)) # adjust for BST

df.drop_duplicates(subset='WriteTime', inplace=True)
df.set_index('WriteTime', inplace=True)

df.loc[df['Temp'] >= 50, 'Temp'] = np.nan
df.loc[df['RH'] >= 0.999, 'RH'] = np.nan
df.fillna(method='ffill', inplace=True)
df.fillna(method='bfill', inplace=True) # fill first value in case of NaN row 0

df['1000Lat'] = df['1000Lat']/1000
df['1000Lng'] = df['1000Lng']/1000
df.rename(columns={'1000Lat': 'Lat', '1000Lng': 'Lng'}, inplace=True)

df = df.sort_index()

# if available, missing GPS data can be populated using Strava information
gpx_file = open(subject+'/'+gpx_name, 'r')
gpx = gpxpy.parse(gpx_file)
start_time = None
for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            if start_time == None:
                start_time = point.time.replace(tzinfo=None)
                t_offset = start_time-true_time
            point.time = point.time - t_offset

            idx = df.index.get_loc(point.time.replace(tzinfo=None), method='nearest')
            idx = df.iloc[idx].name
            if df.loc[idx, 'Lat'] == 0.0:
                df.loc[idx, 'Lat'] = point.latitude
                df.loc[idx, 'Lng'] = point.longitude

df = df.drop(df[df['Lat'] == 0.0].index)
df.to_csv(subject+"/Cleaned/"+gpx_name[:-4]+".csv")

with open(subject+"/log.txt", "a+") as f:
    f.write(f"{df.index[0]}, {len(df)} of {start_len} valid measurements, mean PM2.5 {df['PM2.5'].mean():.4f} ug/m3\n")

