# -*- coding: utf-8 -*-
"""Spotify Suggestion Model V3.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Pr72g5LT1ddLkFRCvJ8OcUsCgSYRVlCX

# Spotify Suggestion Model V3

## Infrastructure
"""

import sys
# !{sys.executable} -m pip install spotipy

username = "agwx2"
cid = "17c11cf9271f4980a85e6aab83cba6bb" 
secret = "015c9abf126340a7981e7ba64dbe7828"
# good_playlist_id = "61BmnG6d7ifmj8Dr5tuCBK"
# bad_playlist_ids = "53FPslFSIAGvVyERcNG4J3"
# source_playlist_id = "5ghFHvZmV4FDK5YLeZQRu9"
good_playlist_ids = [
    "37i9dQZF1DX48TTZL62Yht",   # Hip Hop Favourites
    "37i9dQZF1EQnqst5TRi17F",   # Hip Hop Mix
    "37i9dQZF1DX7FY5ma9162x",   # R&B Favourites
    "37i9dQZF1EQoqCH7BwIYb7",   # R&B Mix
    "53FPslFSIAGvVyERcNG4J3",   # Trap/R&B (personal mix)
    # "37i9dQZF1DWWEcRhUVtL8n"    # Indie Pop
]
bad_playlist_ids = [
    "37i9dQZF1EQpj7X7UK8OOF",   # Rock Mix
    "37i9dQZF1DX1kCIzMYtzum",   # EDM
    "37i9dQZF1DXbITWG1ZJKYt",   # Jazz Classics
    "37i9dQZF1EQmPV0vrce2QZ",   # Country Mix
    "37i9dQZF1EQncLwOalG3K7",   # Pop Mix
    "61BmnG6d7ifmj8Dr5tuCBK"    # Classic Rock (personal mix)
]
source_playlist_ids = [
    # "37i9dQZF1DXb57FjYWz00c",   # 80s Hits
    # "37i9dQZF1EQn2GRFTFMl2A",   # 90s Mix
    # "37i9dQZF1DWUZv12GM5cFk",   # 2000s Hits
    # "37i9dQZF1DXc6IFF23C9jj",   # 2010s Hits
    "5ghFHvZmV4FDK5YLeZQRu9",   # Top 100 (personal mix)
]
source_playlist_id = source_playlist_ids[0]

import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials

import pandas as pd
from sklearn.metrics import accuracy_score, mean_squared_error, r2_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split


from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier, GradientBoostingClassifier, StackingClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression

from keras.models import Sequential
from keras.layers import Dense
from keras.wrappers.scikit_learn import KerasClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

"""## Data Collection"""

sp_cred = SpotifyClientCredentials(
    client_id=cid,
    client_secret=secret
)
sp = spotipy.Spotify(client_credentials_manager=sp_cred)

all_good_ids = []
for good_playlist_id in good_playlist_ids:
  good_playlist = sp.user_playlist(username, good_playlist_id)
  good_tracks = good_playlist["tracks"]
  good_songs = good_tracks["items"]

  while good_tracks['next']:
      good_tracks = sp.next(good_tracks)
      for item in good_tracks["items"]:
          good_songs.append(item)

  good_ids = []
  for i in range(len(good_songs)):
      good_ids.append(good_songs[i]['track']['id'])
  print(len(good_ids))
  all_good_ids += good_ids
print("")
print(len(all_good_ids))
print(all_good_ids)

all_bad_ids = []
for bad_playlist_id in bad_playlist_ids:
  bad_playlist = sp.user_playlist(username, bad_playlist_id)
  bad_tracks = bad_playlist["tracks"]
  bad_songs = bad_tracks["items"]

  while bad_tracks['next']:
      bad_tracks = sp.next(bad_tracks)
      for item in bad_tracks["items"]:
          bad_songs.append(item)

  bad_ids = []
  for i in range(len(bad_songs)):
      bad_ids.append(bad_songs[i]['track']['id'])
  print(len(bad_ids))
  all_bad_ids += bad_ids
print("")
print(len(all_bad_ids))
print(all_bad_ids)

source_playlist = sp.user_playlist(username, source_playlist_id)
source_tracks = source_playlist["tracks"]
source_songs = source_tracks["items"]

while source_tracks['next']:
    source_tracks = sp.next(source_tracks)
    for item in source_tracks["items"]:
        source_songs.append(item)

source_ids = []
for i in range(len(source_songs)):
    if source_songs[i]['track'] != None:
      source_ids.append(source_songs[i]['track']['id'])
print(len(source_ids))
print(source_ids)

training_features = []

for i in range(0, len(all_good_ids), 50):
  audio_features = sp.audio_features(all_good_ids[i : i + 50])
  for track in audio_features:
    if track != None:

      track['target'] = 1
      training_features.append(track)
      # training_features[-1]['target'] = 1

for i in range(0, len(all_bad_ids), 50):
  audio_features = sp.audio_features(all_bad_ids[i : i + 50])
  for track in audio_features:
    if track != None:
      track['target'] = 0
      training_features.append(track)
      # training_features[-1]['target'] = 0

print(len(training_features))
print(training_features)

source_features = []
for i in range(0, len(source_ids), 50):
    audio_features = sp.audio_features(source_ids[i : i + 50])
    for track in audio_features:
        track['target'] = 0
        source_features.append(track)
        # source_features[-1]['target'] = 0  # arbitrary

print(len(source_features))
print(source_features)

"""## Data Preparation"""

trainingData = pd.DataFrame(training_features)

trainingData

train, test = train_test_split(trainingData, test_size = 0.15)

target_features = ["danceability", "loudness", "valence", "energy", "instrumentalness", "acousticness", "key", "speechiness", "duration_ms"]

x_train = train[target_features]
y_train = train["target"]
x_test = test[target_features]
y_test = test["target"]

x_train

y_train

x_test

y_test

"""## Model Evaluation

### Random Forest
"""

# random forest combines multiple decision trees and uses bagging
# (training multiple trees on different sections of training data, averaging the result)
rfc = RandomForestClassifier(n_jobs=1, random_state=1)
rfc.fit(x_train, y_train)
rfc_pred = rfc.predict(x_test)

score = accuracy_score(y_test, rfc_pred) * 100
print("Accuracy using Random Forest: ", round(score, 2), "%")
print('Mean squared error: %.2f' % mean_squared_error(y_test, rfc_pred))

"""Measured Accuracy: 88.82%

### Gradient Boosting
"""

# I <3 gradient boost
gbc = GradientBoostingClassifier(n_estimators=100, learning_rate=.1, max_depth=1, random_state=1)
gbc.fit(x_train, y_train)
gbc_pred = gbc.predict(x_test)

score = accuracy_score(y_test, gbc_pred) * 100
print("Accuracy using Gradient Boost: ", round(score, 2), "%")
print('Mean squared error: %.2f' % mean_squared_error(y_test, gbc_pred))

"""Measured Accuracy: 90.68%

### Gradient Boosting w/ Manual Stacking (Random Forest)
"""

x_train_rfc = (x_train.iloc[0:int(len(x_train) / 2)]).copy()
y_train_rfc = (y_train.iloc[0:int(len(y_train) / 2)]).copy()
x_train_gbc = (x_train.iloc[int(len(x_train) / 2):len(x_train)]).copy()
y_train_gbc = (y_train.iloc[int(len(y_train) / 2):len(y_train)]).copy()

x_test_rfc = x_train_gbc
y_test_rfc = y_train_gbc
x_test_gbc = x_test.copy()
y_test_gbc = y_test.copy()

rfc_stack = RandomForestClassifier(n_jobs=1, random_state=1)
rfc_stack.fit(x_train_rfc, y_train_rfc)
rfc_stack_pred_train = rfc_stack.predict(x_test_rfc)

score = accuracy_score(y_test_rfc, rfc_stack_pred) * 100
print("Accuracy using Random Forest: ", round(score, 2), "%")
print('Mean squared error: %.2f' % mean_squared_error(y_test_rfc, rfc_stack_pred))

rfc_stack_pred_test = rfc_stack.predict(x_test_gbc)

# stack
x_train_gbc['rfc_stack_pred'] = rfc_stack_pred_train.tolist()
x_test_gbc['rfc_stack_pred'] = rfc_stack_pred_test.tolist()

x_train_gbc

x_test_gbc

gbc_stack = GradientBoostingClassifier(n_estimators=100, learning_rate=.1, max_depth=1, random_state=1)
gbc_stack.fit(x_train_gbc, y_train_gbc)
gbc_stack_pred = gbc_stack.predict(x_test_gbc)

score = accuracy_score(y_test_gbc, gbc_stack_pred) * 100
print("Accuracy using Gradient Boost: ", round(score, 2), "%")
print('Mean squared error: %.2f' % mean_squared_error(y_test_gbc, gbc_stack_pred))

"""Measured Accuracy: 88.2%

### Stacking Classifier
"""

base_learners = [
  ('rf_1', RandomForestClassifier(n_estimators=10, random_state=42)),
  ('rf_2', KNeighborsClassifier(n_neighbors=5)),             
]

stk = StackingClassifier(estimators=base_learners, final_estimator=LogisticRegression())
stk.fit(x_train, y_train)
stk_pred = stk.predict(x_test)

score = accuracy_score(y_test, stk_pred) * 100
print("Accuracy using Gradient Boost: ", round(score, 2), "%")
print('Mean squared error: %.2f' % mean_squared_error(y_test, stk_pred))

"""Measured Accuracy: 88.2%"""

base_learners = [
  ('rf_1', RandomForestClassifier(n_estimators=10, random_state=42)),
  ('rf_2', KNeighborsClassifier(n_neighbors=5)),             
  ('rf_3', GradientBoostingClassifier(n_estimators=100, learning_rate=.1, max_depth=1, random_state=1))
]

stk = StackingClassifier(estimators=base_learners, final_estimator=LogisticRegression())
stk.fit(x_train, y_train)
stk_pred = stk.predict(x_test)

score = accuracy_score(y_test, stk_pred) * 100
print("Accuracy using Gradient Boost: ", round(score, 2), "%")
print('Mean squared error: %.2f' % mean_squared_error(y_test, stk_pred))

"""Measured Accuracy: 89.44%

### Neural Networks

#### Baseline
"""

def keras_nn_baseline_model_small():
  model = Sequential()
  model.add(Dense(9, input_dim=9, activation='relu'))
  model.add(Dense(1, activation='sigmoid'))
  model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
  return model

def keras_nn_baseline_model_big():
  model = Sequential()
  model.add(Dense(9, input_dim=9, activation='relu'))
  model.add(Dense(18, input_dim=9, activation='relu'))
  model.add(Dense(90, input_dim=18, activation='sigmoid'))
  model.add(Dense(1, activation='sigmoid'))
  model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
  return model

def keras_nn_baseline_model_shaped():
  model = Sequential()
  model.add(Dense(5, input_dim=9, activation='relu'))
  model.add(Dense(60, input_dim=5, activation='sigmoid'))
  model.add(Dense(5, input_dim=60, activation='relu'))
  model.add(Dense(1, activation='sigmoid'))
  model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
  return model

"""#### Pipeline w/ Normalization"""

estimators = []
estimators.append(('standardize', StandardScaler()))
estimators.append(('mlp', KerasClassifier(build_fn=keras_nn_baseline_model_shaped, epochs=200, batch_size=5, verbose=0)))
keras_pipeline = Pipeline(estimators)

kfold = StratifiedKFold(n_splits=10, shuffle=True)
results = cross_val_score(keras_pipeline, x_train, y_train, cv=kfold)
print("Standardized: %.2f%% (%.2f%%)" % (results.mean() * 100, results.std() * 100))

"""**Cross-Validation Scores**  
keras_nn_baseline_model_small: 87.51%  
keras_nn_baseline_model_big: 85.09%  
keras_nn_baseline_model_shaped: 88.27%  
"""

keras_pipeline.fit(x_train, y_train)
keras_pred = keras_pipeline.predict(x_test)

score = accuracy_score(y_test, keras_pred) * 100
print("Accuracy using NN: ", round(score, 2), "%")
print('Mean squared error: %.2f' % mean_squared_error(y_test, keras_pred))

"""### Neural Networks w/ Stacking"""

def get_nn_classifier():
  nn_clf = KerasClassifier(build_fn=keras_nn_baseline_model_shaped, epochs=200, batch_size=5, verbose=0)
  nn_clf._estimator_type = "classifier"
  estimators = []
  estimators.append(('standardize', StandardScaler()))
  estimators.append(('mlp', nn_clf))
  return Pipeline(estimators)

base_learners = [
  ('rf_1', RandomForestClassifier(n_estimators=10, random_state=42)),
  ('rf_2', KNeighborsClassifier(n_neighbors=5)),             
  ('rf_3', GradientBoostingClassifier(n_estimators=100, learning_rate=.1, max_depth=1, random_state=1)),
  ('rf_4', get_nn_classifier())
]

nn_stk = StackingClassifier(estimators=base_learners, final_estimator=LogisticRegression())
nn_stk.fit(x_train, y_train)
nn_stk_pred = nn_stk.predict(x_test)

score = accuracy_score(y_test, nn_stk_pred) * 100
print("Accuracy using NN & Stacking: ", round(score, 2), "%")
print('Mean squared error: %.2f' % mean_squared_error(y_test, nn_stk_pred))

"""Measured Accuracy: 90.06%

## Generate Predictions
"""

sourceData = pd.DataFrame(source_features)
sourceData = sourceData[target_features]

sourceData

# model = gbc
# model = keras_pipeline
model = nn_stk

pred = model.predict(sourceData)

source_playlist_songs[0]

source_playlist_songs = source_playlist['tracks']['items']

print("ACCEPTED")


i = 0
for prediction in pred:
    if prediction == 1 and i + 1 < len(source_playlist_songs):
        song_title = source_playlist_songs[i + 1]['track']['name']
        artist_name = source_playlist_songs[i + 1]['track']['artists'][0]['name']
        print ("Song: " + song_title + ", By: "+ artist_name)
    i = i + 1


print("REJECTED")

i = 0
for prediction in pred:
    if prediction == 0 and i + 1 < len(source_playlist_songs):
        song_title = source_playlist_songs[i + 1]['track']['name']
        artist_name = source_playlist_songs[i + 1]['track']['artists'][0]['name']
        print ("Song: " + song_title + ", By: "+ artist_name)
    i = i + 1