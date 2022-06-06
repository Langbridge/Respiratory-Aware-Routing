import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

def df_shifted(df, target=None, lag=0):
    '''
    Returns a period-shifted DataFrame.

            Parameters:
                df (pd.DataFrame): DataFrame on which to operate
                target (string): Target column to be shifted
                lag (int): Number of periods to shift

            Returns:
                df (pd.DataFrame): Period-shifted DataFrame.
    '''
    if not lag and not target:
        return df       
    new = {}
    for c in df.columns:
        if c == target:
            new[c] = df[target]
        else:
            new[c] = df[c].shift(periods=lag)
    return pd.DataFrame(data=new)

def lin_model(norm, train_features, loss_func):
    '''
    Returns a compiled linear model.

            Parameters:
                norm (tf.layers.Normalization): Adapted normalization filter
                train_features (list of str): List of features to train on
                loss_func (str): Name of the loss function to use

            Returns:
                model (tf.model): Compiled linear model
    '''
    linear_model = tf.keras.Sequential([norm, layers.Dense(units=1)])
    linear_model.predict(train_features)
    linear_model.compile(optimizer = tf.optimizers.Adam(learning_rate=0.1), loss=loss_func)
    return linear_model

def deep_model(norm, train_features, loss_func):
    '''
    Returns a compiled deep model.

            Parameters:
                norm (tf.layers.Normalization): Adapted normalization filter
                train_features (list of str): List of features to train on
                loss_func (str): Name of the loss function to use

            Returns:
                model (tf.model): Compiled deep model
    '''
    if len(train_features.columns) > 10:
        model = tf.keras.Sequential([
            norm,
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(64, activation='relu'),
            layers.Dense(1)
            ])
    else:
        model = tf.keras.Sequential([
            norm,
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(64, activation='relu'),
            layers.BatchNormalization(),
            layers.Dense(64, activation='relu'),
            layers.Dense(1)
            ])
    model.predict(train_features)
    model.compile(optimizer = tf.optimizers.Adam(learning_rate=0.0005), loss=loss_func)
    return model

def regression(df, y_col, mode, loss_func='mean_squared_error'):
    '''
    Returns the test dataset and the RMSE of the model.

            Parameters:
                df (tf.layers.Normalization): DataFrame including the target column
                y_col (list of str): Target column for the model to learn
                mode (str): 'linear or 'deep'
                loss_func (str): Name of the loss function

            Returns:
                test_features (pd.DataFrame): Test dataset + prediction
                RMSE (float): RMSE on the test dataset
    '''
    df = df.dropna()

    # create train-test split
    train_features = df.sample(frac=0.8, random_state=0)
    test_features = df.drop(train_features.index)
    train_labels = train_features.pop(y_col)
    test_labels = test_features.pop(y_col)

    # create the normalization filter
    normalizer = tf.keras.layers.Normalization(axis=-1)
    normalizer.adapt(np.array(train_features))

    # build the model of correct type
    if mode.lower() == 'linear': model = lin_model(normalizer, train_features, loss_func)
    elif mode.lower() == 'deep': model = deep_model(normalizer, train_features, loss_func)
    else: return None

    # fit the model
    history = model.fit(
        train_features,
        train_labels,
        epochs=200,
        verbose=0,
        validation_split = 0.2)

    # use the model to predict the test features
    test_predictions = model.predict(test_features).flatten()
    test_features['Prediction'] = test_predictions
    test_features['Reference Value'] = test_labels

    # print the weights for linear model
    if mode.lower() == 'linear': print(model.layers[1].get_weights())

    # save the model
    model.save(mode.lower()+'_model_weather.h5')
    return test_features, np.sqrt(model.evaluate(test_features.drop(columns=['Prediction', 'Reference Value']), test_labels, verbose=0))

# ----- PREPROCESS WEATHER DATA
weather = pd.read_csv('MY_weatherdata.csv')
weather['last_updated'] = pd.to_datetime(weather['last_updated'])
weather.drop_duplicates(subset='last_updated', inplace=True)
weather.set_index('last_updated', inplace=True)
weather.sort_index(inplace=True)
weather = weather.loc['2022-02-09':'2022-04-13']
weather.drop(columns=['timestamp','last_updated_epoch', 'feelslike_f', 'gust_mph', 'precip_in', 'pressure_in', 'temp_f', 'vis_miles', 'wind_dir', 'wind_mph'], inplace=True)
# produces 15 columns corresponding to the various conditions
weather = pd.get_dummies(weather, columns=['condition'])
weather = weather.resample('1H').pad()

# ----- PROCESS PM DATA
data = pd.read_csv('results 17 5.csv')
data['Time'] = pd.to_datetime(data['Time'])
data.set_index('Time', inplace=True)
data.sort_index(inplace=True)
data = data.apply(pd.to_numeric, errors='coerce')
data = data.resample('1H').mean()

# ----- COMBINING DATAFRAMES
data = pd.concat([data, weather], axis=1, join='inner')

# ----- MODEL
learn_results = {}

# construct the learning data based on selected features
# learn_df = data[['Temperature','Relative Humidity','PM2.5','PM10','1H Reference']]
learn_df = data[['precip_mm','humidity','temp_c','wind_kph','Temperature','Relative Humidity','PM2.5','PM10','1H Reference']]
# learn_df = data[list(weather.columns)+['Temperature','Relative Humidity','PM2.5','PM10','1H Reference']]

# augment the learning data with additional columns
learn_df['Delay'] = learn_df['PM2.5'].shift(periods=1)
learn_df['Hour'] = learn_df.index.hour
learn_df['Day'] = learn_df.index.weekday
learn_df.dropna(inplace=True)
# learn_df.to_csv('cleaned data + weather.csv')

# train the models and display results
df_linear, learn_results['linear'] = regression(learn_df, '1H Reference', 'Linear')
df_deep, learn_results['deep'] = regression(learn_df, '1H Reference', 'Deep')
# df_deep_no_weather, learn_results['deep_no_weather'] = regression(learn_df[['Temperature','Relative Humidity','PM2.5','PM10','1H Reference']], '1H Reference', 'Deep')
print(learn_results)

# plot the performance of the selected deep model
df_deep.reset_index(inplace=True)
df_deep[['PM2.5', 'Prediction', 'Reference Value']].plot(ylabel='PM2.5, ug/m3', figsize=(18,12), color=['gray','blue','red'])
plt.savefig('PM_measured_predicted_ref.png', dpi=300)