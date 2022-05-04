import spotipy
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials

import pandas as pd
from sklearn.metrics import accuracy_score, mean_squared_error, r2_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split


from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier, GradientBoostingClassifier
from sklearn.linear_model import LinearRegression

from keras.models import Sequential
from keras.layers import Dense
from keras.wrappers.scikit_learn import KerasClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

import json

from types import MemberDescriptorType
from flask import Flask, render_template, request
app = Flask(__name__)

def get_results(good_playlist, bad_playlist, source_playlist):
    username = "agwx2"
    cid = "17c11cf9271f4980a85e6aab83cba6bb" 
    secret = "015c9abf126340a7981e7ba64dbe7828"
    # good_playlist_id = "61BmnG6d7ifmj8Dr5tuCBK"
    # bad_playlist_ids = "53FPslFSIAGvVyERcNG4J3"
    # source_playlist_id = "5ghFHvZmV4FDK5YLeZQRu9"
    good_playlist_ids = [
        good_playlist
    ]
    bad_playlist_ids = [
        bad_playlist
    ]
    source_playlist_ids = [
       source_playlist
    ]
    source_playlist_id = source_playlist_ids[0]

    

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
    # print(all_good_ids)

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
    # print(all_bad_ids)

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
    # print(source_ids)

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
    # print(training_features)

    source_features = []
    for i in range(0, len(source_ids), 50):
        audio_features = sp.audio_features(source_ids[i : i + 50])
        for track in audio_features:
            track['target'] = 0
            source_features.append(track)
            # source_features[-1]['target'] = 0  # arbitrary

    print(len(source_features))
    # print(source_features)

    trainingData = pd.DataFrame(training_features)

    train, test = train_test_split(trainingData, test_size = 0.15)
    target_features = ["danceability", "loudness", "valence", "energy", "instrumentalness", "acousticness", "key", "speechiness", "duration_ms"]

    x_train = train[target_features]
    y_train = train["target"]
    x_test = test[target_features]
    y_test = test["target"]

    gbc = GradientBoostingClassifier(n_estimators=100, learning_rate=.1, max_depth=1, random_state=1)
    gbc.fit(x_train, y_train)
    gbc_pred = gbc.predict(x_test)

    sourceData = pd.DataFrame(source_features)
    sourceData = sourceData[target_features]

    model = gbc

    pred = model.predict(sourceData)

    source_playlist_songs = source_playlist['tracks']['items']

    # print("ACCEPTED")

    accepted_list = []
    i = 0
    for prediction in pred:
        if prediction == 1 and i + 1 < len(source_playlist_songs):
            song_title = source_playlist_songs[i + 1]['track']['name']
            artist_name = source_playlist_songs[i + 1]['track']['artists'][0]['name']
            # print ("Song: " + song_title + ", By: "+ artist_name)

            accepted_list.append("{} by {}".format(song_title, artist_name))
        i = i + 1


    # print("REJECTED")
    rejected_list = []
    i = 0
    for prediction in pred:
        if prediction == 0 and i + 1 < len(source_playlist_songs):
            song_title = source_playlist_songs[i + 1]['track']['name']
            artist_name = source_playlist_songs[i + 1]['track']['artists'][0]['name']
            # print ("Song: " + song_title + ", By: "+ artist_name)
            rejected_list.append("{} by {}".format(song_title, artist_name))

        i = i + 1
    return [accepted_list, rejected_list]

@app.route("/")
def hello():
    return render_template("index.html")

@app.route("/model", methods = ['POST'])
def model():
    good_id = request.form['good_id']
    bad_id = request.form['bad_id']
    src_id = request.form['src_id']
    results = get_results(good_id, bad_id, src_id)
    print(results)
    return json.dumps(results[0])
    # return "hello"

if __name__ == "__main__":
    app.run()