import osmnx as ox
import pandas as pd
import geopandas as gpd
import os
import sys

# sys.path.append('../Optimisation/')
from rdd import *

# BIKE PARAMS
g = 9.81
Cd = 0.7
A = 0.5
Cr = 0.001
ro = 1.225
n_mech = 0.97
n_elec = 0.72

# SUBJECT PARAMS
# subjects = {
#             'A': {'hr_0': 70, 'm': 100, 'Tr': 24, 'hr_max': 180, 'c': 0.2, 'kf': 3e-5, 'sex': 'M'},
#             'B': {'hr_0': 70, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 2e-5, 'sex': 'M'},
#             'C': {'hr_0': 60, 'm': 80, 'Tr': 24, 'hr_max': 180, 'c': 0.2, 'kf': 2e-5, 'sex': 'F'},
#             # 'D': {'hr_0': 60, 'm': 90, 'Tr': 22, 'hr_max': 180, 'c': 0.15, 'kf': 4e-5, 'sex': 'F'}
#             }
subjects = {
            'A': {'hr_0': 70, 'm': 100, 'Tr': 24, 'hr_max': 180, 'c': 0.2, 'kf': 3e-5, 'sex': 'M'},
            'B': {'hr_0': 70, 'm': 100, 'Tr': 24, 'hr_max': 180, 'c': 0.2, 'kf': 3e-5, 'sex': 'M'},
            'C': {'hr_0': 70, 'm': 100, 'Tr': 24, 'hr_max': 180, 'c': 0.2, 'kf': 3e-5, 'sex': 'M'},
            'D': {'hr_0': 70, 'm': 100, 'Tr': 24, 'hr_max': 180, 'c': 0.2, 'kf': 3e-5, 'sex': 'M'},
            'E': {'hr_0': 70, 'm': 100, 'Tr': 24, 'hr_max': 180, 'c': 0.2, 'kf': 3e-5, 'sex': 'M'}
            }

def gps_dist(row1, row2):
    '''
    Returns the great circle distance between two points.

            Parameters:
                    row1 (pd.Series): The row relating to the first point
                    row2 (pd.Series): The row relating to the second point


            Returns:
                    distance (float): Distance between the two GPS points, m
    '''
    return ox.distance.great_circle_vec(row2['Lat'], row2['Lng'], row1['Lat'], row1['Lng'])

def calc_velocity(row):
    '''
    Returns the differential velocity.

            Parameters:
                    row (pd.Series): A row from a differential DataFrame

            Returns:
                    velocity (float): Differential velocity, m/s
    '''
    return row['distance'] / row['dt']

def segment_power(v, d_height, l, m):
    '''
    Returns the power required to traverse a given road segment.

            Parameters:
                    v (float): The travel velocity, m/s
                    d_height (float): The change of height over the road segment, m
                    l (float): The length of the road segment, m

            Returns:
                    power (float): Total required power to traverse the segment, W
    '''
    # sin theta = O/H = (H2 - H1)/l
    try:
        P_g = g * m * d_height/l * v
        P_a = 0.5 * Cd * ro * A * v**3
        P_f = Cr * m * g * v
        return max(P_g + P_a + P_f, 0) # avoid flooring effects with downhill slopes
    except RuntimeWarning:
        return 0

def hr_ss(hr_0, power, t, hr_max, c):
    '''
    Returns the individual's heart rate at the end of the road segment.

            Parameters:
                    hr_0 (float): The heart rate at the start of the segment, bpm
                    power (float): The power exerted, W
                    t (float): The length of the road segment, seconds
                    hr_max (float): The individual's maximum heart rate, bpm
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

def segment_hr(cyclist_power, hr_0, kf, t, hr_max, c, power_history):
    '''
    Returns the HR at the end of a road segment.

            Parameters:
                    cyclist_power (float): The power required to traverse the segment, W
                    hr_0 (float): The heart rate at the beginning of the segment, bpm
                    kf (float): The weighting factor for historic power output
                    t (float): The length of the road segment, seconds
                    hr_max (float): The individual's maximum heart rate, bpm
                    c (float): Rise parameter for HR with power, bpm/W
                    power_history (list of floats): A list of any previous segments' power outputs

            Returns:
                    hr (float): Estimated HR at the end of the road segment, bpm
    '''
    percieved_power = cyclist_power + kf * power_history
    return hr_ss(hr_0, percieved_power, t, hr_max, c)

def segment_pm(cyclist_power, v, l, hr_0, Tr, ambient_pm, sex, kf, hr_max, c, power_history):
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
    hr = segment_hr(cyclist_power, hr_0, kf, (v/l)/Tr, hr_max, c, power_history)
    return calc_rdd(sex, hr, l/v, ambient_pm)

def row_pm(row, subject):
    '''
    Returns the RDD experienced on a given row. Wrapper for segment_pm().

            Parameters:
                    row(pd.Series): A row from a differential DataFrame
                    subject(dict): Dictionary containing subject's physiological attributes

            Returns:
                    RDD (float): Recieved deposition dose over the period of interest, ug
    '''
    return segment_pm(row['power'], row['velocity'], row['distance'], subject['hr_0'], subject['Tr'], row['PM2.5'], subject['sex'], subject['kf'], subject['hr_max'], subject['c'], row['power_history'])

def row_power(row, subject):
    '''
    Returns the power required to traverse a given row. Wrapper for segment_power().

            Parameters:
                    row(pd.Series): A row from a differential DataFrame
                    subject(dict): Dictionary containing subject's physiological attributes

            Returns:
                    power (float): Required power to traverse the length represented by the row, W
    '''
    return segment_power(row['velocity'], row['dh'], row['distance'], subject['m']) / n_mech

# open the commute calibration log & append en empty column
log = pd.read_csv('../Commute Monitoring/calibration_log.csv', index_col=0)
log = log.assign(rdd = 0.0)

# for every subject, calculate RDD for every recorded commute
for subject in subjects.keys():
    print(subject)
    directory = os.path.join('../Commute Monitoring/'+subject+'/Calibrated/')
    for root,dirs,files in os.walk(directory):
        for file in files:
            if file.endswith(".csv"):
                raw_data = pd.read_csv(directory+file)
                raw_data['WriteTime'] = pd.to_datetime(raw_data['WriteTime'])

                dists = []
                for x in range(len(raw_data)-1):
                    dists.append(gps_dist(raw_data.iloc[x], raw_data.iloc[x+1]))

                df = raw_data[['WriteTime', 'Alt']].diff()
                df['PM2.5'] = raw_data['Calibrated PM2.5'].shift(1)

                df = df.dropna().reset_index(drop=True)
                df = pd.concat([df, pd.Series(dists)], axis=1, ignore_index=True)
                df.rename(columns={0: 'dt', 1: 'dh', 2: 'PM2.5', 3: 'distance'}, inplace=True)
                df = df.loc[~(df==0).all(axis=1)]

                df['dt'] = df['dt'].dt.total_seconds()

                df['velocity'] = df.apply(calc_velocity, axis=1)

                df['power'] = df.apply(row_power, args=(subjects[subject],), axis=1)
                df['power_history'] = df['power'].rolling(20).sum()
                df['power_history'].fillna(df['power'].shift(1), inplace=True)
                df['power_history'].fillna(0.0, inplace=True)
                df.dropna(inplace=True)
                                                
                df['rdd'] = df.apply(row_pm, args=(subjects[subject],), axis=1)
                print(f"\t{file[:-4]}\t{sum(df['rdd']):.2f} ug")

                df['power_history'] = 0.0
                df['rdd_nohis'] = df.apply(row_pm, args=(subjects[subject],), axis=1)
                print(f"\t...\t{sum(df['rdd_nohis']):.2f} ug")
                diff = (sum(df['rdd_nohis']) - sum(df['rdd'])) / sum(df['rdd'])
                print(f"\t...\t{diff*100:.5f}% difference")

                idx = log[log['file']==file].index
                log.loc[idx, 'rdd'] = sum(df['rdd'])

# display and save the updated log file
print(log.sort_values(by=['rdd']))
log.to_csv('../Commute Monitoring/calibration_log.csv')