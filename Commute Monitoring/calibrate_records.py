import pandas as pd
import datetime as dt
import numpy as np
import os
from tensorflow import keras, optimizers

subject_list = ['A', 'B', 'C', 'D']
model = keras.models.load_model('../MY Monitoring/deep_model2')

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
                model_df.drop(columns=['Lat', 'Lng', 'Alt'], inplace=True)
                model_df.rename(columns={'Temp': 'Temperature', 'RH': 'Relative Humidity'}, inplace=True)
                model_df = model_df[['Temperature','Relative Humidity','PM2.5','PM10']]

                model_df['Delay'] = model_df['PM2.5'].shift(periods=1)
                model_df['Hour'] = model_df.index.hour
                model_df['Day'] = model_df.index.weekday
                model_df.dropna(inplace=True)

                model_df['Calibrated PM2.5'] = model.predict(model_df)
                model_df.to_csv(subject+'/Calibrated/'+file)

                log_data = {'subject': subject, 'file': file, 'date': model_df.index[0].date(), 'commute': file[4:6],
                            'min': model_df['Calibrated PM2.5'].min(), 'Q25': model_df['Calibrated PM2.5'].quantile(q=0.25),
                            'mean': model_df['Calibrated PM2.5'].mean(), 'Q75': model_df['Calibrated PM2.5'].quantile(q=0.75),
                            'max': model_df['Calibrated PM2.5'].max()}
                log = log.append(log_data, ignore_index=True)

print(log)
log.to_csv('calibration_log.csv')