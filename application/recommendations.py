# AUDIU
# recommendations.py

import os
import json
import time
import numpy
import keras
import random
import pandas
import spotipy
import sklearn
import pathlib
import scikeras
import sklearn.model_selection


## RECOMMENDATIONS CLASS ##
# recommendations model wrapper class
class Recommendations():

    ## RECOMMENDATIONS ML MODEL ##

    # machine learning model subclass
    class Model():

        # global settings
        SP_TARGET_AUDIO_FEATURES = ["danceability", "loudness", "valence", "energy", "instrumentalness", "acousticness", "key", "speechiness", "duration_ms"]
        TRAIN_TEST_SPLIT_VAL_SIZE = 0.15
        # model type-specific settings
        RANDOM_FOREST_N_ESTIMATORS = 400
        GRADIENT_BOOST_N_ESTIMATORS = 400
        GRADIENT_BOOST_LEARNING_RATE = .1
        GRADIENT_BOOST_MAX_DEPTH = 2
        RANDOM_STATE = 1
        KNN_NUMBER_NEIGHBORS = 25
        PLAYLIST_LIMIT = 10

        # instance fields
        run_id = ''
        model_type = ''
        target_data = None
        reject_data = None
        inference_data = None
        spotify_credentials = None
        spotipy_credentials = None
        spotipy_client = None
        sklearn_classifier = None
        dataframes = None

        # constructor
        def __init__(self, model_type, target_data, reject_data, inference_data, spotify_credentials, run_id):
            self.run_id = run_id
            self.model_type = model_type
            self.target_data = target_data
            self.reject_data = reject_data
            self.inference_data = inference_data
            self.spotify_credentials = spotify_credentials
            self.spotipy_credentials = None
            self.sklearn_classifier = None
            self.spotipy_client = None
            self.dataframes = None

        ## main model methods ##

        # collect & prepare data from spotify api
        def prepare(self, output=True):
            # connect to spotify api
            self.spotipy_credentials = spotipy.oauth2.SpotifyClientCredentials(client_id=self.spotify_credentials['client_id'], client_secret=self.spotify_credentials['client_secret'])
            self.spotipy_client = spotipy.Spotify(client_credentials_manager=self.spotipy_credentials)
            # limit training data size to prevent imbalanced dataset
            playlist_limit = Recommendations.Model.PLAYLIST_LIMIT
            target_data_limited = self.target_data if len(self.target_data) <= playlist_limit else random.sample(self.target_data, playlist_limit)
            reject_data_limited = self.reject_data if len(self.reject_data) <= playlist_limit else random.sample(self.reject_data, playlist_limit)
            inference_data_limited = self.inference_data if len(self.inference_data) <= playlist_limit else random.sample(self.inference_data, playlist_limit)
            # collect training & inference data track IDs
            training_target_ids = self.sp_playlists_to_tracks(target_data_limited)
            training_reject_ids = self.sp_playlists_to_tracks(reject_data_limited)
            inference_ids = self.sp_playlists_to_tracks(inference_data_limited)
            # collect training & inference data audio features
            training_target_features = self.sp_tracks_to_audio_features(training_target_ids, True)
            training_reject_features = self.sp_tracks_to_audio_features(training_reject_ids, False)
            training_features = training_target_features + training_reject_features
            inference_features = self.sp_tracks_to_audio_features(inference_ids, None)
            # gather audio features into dataframe
            training_data = pandas.DataFrame(training_features)
            inference_data = pandas.DataFrame(inference_features)
            # split training features into subsections
            feature_subset = Recommendations.Model.SP_TARGET_AUDIO_FEATURES
            train_split, test_split = sklearn.model_selection.train_test_split(training_data, test_size=Recommendations.Model.TRAIN_TEST_SPLIT_VAL_SIZE)
            x_total = training_data[feature_subset]
            y_total = training_data["target"]
            x_train = train_split[feature_subset]
            y_train = train_split["target"]
            x_test = test_split[feature_subset]
            y_test = test_split["target"]
            # prepare inference features
            x_total_inf = inference_data[feature_subset]
            # save organized data dictionary
            self.dataframes = {"training": {"x_total": x_total, "y_total": y_total, "x_train": x_train, "y_train": y_train, "x_test": x_test, "y_test": y_test}, "inference": {"x_total": x_total_inf}}

        # build model architecture in memory
        def build(self, output=True):
            self.sklearn_classifier = None
            classifier_final = None
            if self.model_type == 'nn_stacked':
                pass
            elif self.model_type == 'nn_baseline':
                pass
            elif self.model_type == 'gradient_boost':
                classifier_final = sklearn.ensemble.GradientBoostingClassifier(n_estimators=Recommendations.Model.GRADIENT_BOOST_N_ESTIMATORS,
                                                                               learning_rate=Recommendations.Model.GRADIENT_BOOST_LEARNING_RATE,
                                                                               max_depth=Recommendations.Model.GRADIENT_BOOST_MAX_DEPTH,
                                                                               random_state=Recommendations.Model.RANDOM_STATE)
            elif self.model_type == 'random_forest':
                classifier_final = sklearn.ensemble.RandomForestClassifier(n_estimators=Recommendations.Model.RANDOM_FOREST_N_ESTIMATORS, random_state=Recommendations.Model.RANDOM_STATE)
            elif self.model_type == 'k_neighbors':
                classifier_final = sklearn.ensemble.KNeighborsClassifier(n_neighbors=Recommendations.Model.KNN_NUMBER_NEIGHBORS)
            else:
                classifier_final = None
            self.sklearn_classifier = classifier_final

        # train model on targeted & rejected playlists
        def train(self, output=True):
            pass

        # test model on inference playlists
        def infer(self, output=True):
            pass

        ## model convenience functions ##

        # convert playlist ID list to large track ID list (via spotipy)
        def sp_playlists_to_tracks(self, target_playlist_ids, output=True):
            all_target_ids = []
            for target_playlist_id in target_playlist_ids:
                target_ids = self.sp_playlist_to_tracks(target_playlist_id, output)
                if output:
                    print(len(target_ids))
                all_target_ids += target_ids
            if output:
                print(len(all_target_ids))
                print(all_target_ids[0])
            return all_target_ids

        # convert playlist ID to list of track IDs (via spotipy)
        def sp_playlist_to_tracks(self, target_playlist_id, output=True):
            target_playlist = self.spotipy_client.user_playlist(self.spotify_credentials['playlist_user'], target_playlist_id)
            target_tracks = target_playlist["tracks"]
            target_songs = target_tracks["items"]
            while target_tracks['next']:
                target_tracks = self.spotipy_client.next(target_tracks)
                for item in target_tracks["items"]:
                    target_songs.append(item)
            target_ids = []
            for i in range(len(target_songs)):
                if target_songs[i] and target_songs[i]['track'] and target_songs[i]['track']['id']:
                    target_ids.append(target_songs[i]['track']['id'])
            return target_ids

        # collect spotify audio features from track IDs (via spotipy)
        def sp_tracks_to_audio_features(self, track_ids, target=True, output=True):
            target_val = 1 if target else 0
            track_audio_features = []
            for i in range(0, len(track_ids), 50):
                audio_features = self.spotipy_client.audio_features(track_ids[i:i + 50])
                for track in audio_features:
                    if track != None:
                        track['target'] = target_val
                        track_audio_features.append(track)
            if output:
                print(len(track_audio_features))
                print(track_audio_features[0])
            return track_audio_features

        # analyze performace of model on all sections/folds of dataset
        def cross_val_analysis(self, model, x_train, y_train, k=10, output=True):
            kfold = sklearn.model_selection.StratifiedKFold(n_splits=k, shuffle=True)
            results = sklearn.model_selection.cross_val_score(model, x_train, y_train, cv=kfold)
            if output:
                print("Cross-Validation Score Standardized: %.2f%% (%.2f%%)" % (results.mean() * 100, results.std() * 100))
            return (results.mean() * 100)

    ## static methods ##
    # process fork for generating recommendations
    @staticmethod
    def recommendations_run(run_id, model_run_src, config_src, model_run_signal_queue):
        model_run_signal_queue.put("main:run-start:{}".format(run_id))
        package_dir_path = os.path.dirname(os.path.abspath(__file__))
        config_src_path = os.path.join(package_dir_path, config_src)
        model_run_dir_path = os.path.join(package_dir_path, model_run_src)
        model_run_path = pathlib.Path(os.path.join(model_run_dir_path, run_id))
        input_data_json = None
        with open(model_run_path / 'input.json', 'r') as f:
            input_data_json = json.load(f)
        input_data = {
            "run_id": run_id,
            "model_type": input_data_json["model_type"],
            "target_playlists": input_data_json["target_playlists"],
            "reject_playlists": input_data_json["reject_playlists"],
            "inference_playlists": input_data_json["inference_playlists"]
        }
        config_json = None
        with open(config_src_path, 'r') as f:
            config_json = json.load(f)
        spotify_credentials_json = config_json.get('spotify_api_credentials', {})
        spotify_credentials = {
            "token_user": spotify_credentials_json.get('token_user', ''),
            "playlist_user": spotify_credentials_json.get('playlist_user', ''),
            "client_id": spotify_credentials_json.get('client_id', ''),
            "client_secret": spotify_credentials_json.get('client_secret', '')
        }
        print("[ml] generating recommendations for run {}".format(run_id))
        # print(input_data)
        results, ts_profile = Recommendations.generate_recommendations(run_id, input_data, spotify_credentials)
        output_data = {
            "run_id": run_id,
            "model_type": input_data["model_type"],
            "results": results,
            "ts_profile": {
                "ts_total_length": ts_profile[0],
                "ts_training_length": ts_profile[1],
                "ts_inference_length": ts_profile[2]
            }
        }
        with open(model_run_path / 'output.json', 'w') as f:
            json.dump(output_data, f, indent=4, sort_keys=False)
        model_run_signal_queue.put("main:run-done:{}".format(run_id))

    # generate recommendations
    @staticmethod
    def generate_recommendations(run_id, input_data, spotify_credentials):
        # TODO: actually generate recommendations using ml models
        model_type = input_data["model_type"]
        target_playlists = input_data["target_playlists"]
        reject_playlists = input_data["reject_playlists"]
        inference_playlists = input_data["inference_playlists"]
        model = Recommendations.Model(model_type, target_playlists, reject_playlists, inference_playlists, spotify_credentials, run_id)
        model.prepare()
        # model.build()
        # model.train()
        # model.infer()
        ########
        results = []
        # training
        ts_training_start = time.time()
        ts_training_end = time.time()
        ts_training_length = ts_training_end - ts_training_start
        # inference
        ts_inference_start = time.time()
        ts_inference_end = time.time()
        ts_inference_length = ts_inference_end - ts_inference_start
        ts_total_length = ts_training_length + ts_inference_length
        # return data
        return (results, (ts_total_length, ts_training_length, ts_inference_length))

    # generate recommendations (mock method)
    @staticmethod
    def generate_recommendations_mock(run_id, input_data, spotify_credentials):
        results = []
        # training
        ts_training_start = time.time()
        for i in range(10):
            print("[ml] run {}: training - sample epoch {}".format(run_id, i))
            time.sleep(0.5)
        ts_training_end = time.time()
        ts_training_length = ts_training_end - ts_training_start
        # inference
        ts_inference_start = time.time()
        for i in range(10):
            print("[ml] run {}: inference - sample epoch {}".format(run_id, i))
            results.append(str(i))
            time.sleep(0.25)
        ts_inference_end = time.time()
        ts_inference_length = ts_inference_end - ts_inference_start
        ts_total_length = ts_training_length + ts_inference_length
        # return data
        return (results, (ts_total_length, ts_training_length, ts_inference_length))

    # instance fields
    dataset_src = ''
    dataset = None
    package_dir_path = None
    model_run_src = None
    model_run_dir_path = None

    # constructor
    def __init__(self, dataset_src='dataset.json', model_run_src='data/runs'):
        self.dataset = {}
        self.model_run_src = model_run_src
        self.package_dir_path = os.path.dirname(os.path.abspath(__file__))
        self.dataset_src = os.path.join(self.package_dir_path, dataset_src)
        self.model_run_dir_path = os.path.join(self.package_dir_path, model_run_src)

    # load local dataset
    def load_dataset(self):
        playlists = None
        genres = None
        config = None
        models = None
        with open(self.dataset_src) as dataset_file:
            dataset_json = json.load(dataset_file)
            playlists = dataset_json['playlists']
            genres = dataset_json['genres']
            models = dataset_json['models']
            config = dataset_json['config']
        self.dataset['playlists'] = playlists
        self.dataset['genres'] = genres
        self.dataset['models'] = models
        self.dataset['config'] = config

    # convert genre list to playlist using local dataset
    def genres_to_playlists(self, genres_list, return_slugs=True):
        playlist_id_list = []
        playlist_slug_list = []
        for genre in genres_list:
            playlist_slug_list.extend(self.dataset['genres'][genre])
        playlist_slug_list = list(set(playlist_slug_list))
        # print(playlist_slug_list)
        for slug in playlist_slug_list:
            playlist_id_list.append(self.dataset['playlists'][slug])
        playlist_id_list = list(set(playlist_id_list))
        # print(playlist_id_list)
        if return_slugs:
            return (playlist_id_list, playlist_slug_list)
        return playlist_id_list

    # invert list of genres with dataset
    def genre_set_invert(self, genres_list):
        genres_inverse = []
        for genre in self.dataset['genres'].keys():
            if genre not in genres_list and genre != self.dataset['config']['genre_remove_item']:
                genres_inverse.append(genre)
        return genres_inverse

    # prep method before process fork for generating recommendations
    def recommendations_prepare_input(self, run_id):
        model_run_path = pathlib.Path(os.path.join(self.model_run_dir_path, run_id))
        model_run_path.mkdir(parents=True, exist_ok=True)
        request_json = None
        with open(model_run_path / 'request.json', 'r') as f:
            request_json = json.load(f)
        request_data = {
            "run_id": run_id,
            "selected_model": request_json['selected_model'],
            "playlist_selections": request_json['playlist_selections'],
            "genre_selections": request_json['genre_selections']
        }
        # # data preprocessing
        model_type = request_data["selected_model"]
        target_playlists = request_data['playlist_selections']
        reject_playlists = self.genres_to_playlists(self.genre_set_invert(request_data['genre_selections']), False)
        inference_playlists = self.genres_to_playlists(request_data['genre_selections'], False)
        input_data = {"run_id": run_id, "model_type": model_type, "target_playlists": target_playlists, "reject_playlists": reject_playlists, "inference_playlists": inference_playlists}
        with open(model_run_path / 'input.json', 'w') as f:
            json.dump(input_data, f, indent=4, sort_keys=False)
