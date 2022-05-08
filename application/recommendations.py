# AUDIU
# recommendations.py

import os
import json
import time


## RECOMMENDATIONS CLASS ##
# recommendations model wrapper class
class Recommendations():

    # instance fields
    dataset_src = ''
    dataset = None
    package_dir_path = None
    # constructor
    def __init__(self, dataset_src='dataset.json'):
        self.dataset = {}
        self.package_dir_path = os.path.dirname(os.path.abspath(__file__))
        self.dataset_src = os.path.join(self.package_dir_path, dataset_src)

    def model_load_dataset(self):
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

    def model_genres_to_playlists(self, genres_list, return_slugs=True):
        playlist_id_list = []
        playlist_slug_list = []
        for genre in genres_list:
            playlist_slug_list.extend(self.dataset['genres'][genre])
        print(playlist_slug_list)
        for slug in playlist_slug_list:
            playlist_id_list.extend(self.dataset['playlists'][slug])
        print(playlist_id_list)
        if return_slugs:
            return (playlist_id_list, playlist_slug_list)
        return playlist_id_list


    def model_generate_recommendations(self, run_id, target_playlists, reject_playlists, inference_playlists):
        results = []
        # training
        ts_training_start = time.time()
        for i in range(10):
            print("run {}: training - sample epoch {}".format(run_id, i))
            time.sleep(0.5)
        ts_training_end = time.time()
        ts_training_length = ts_training_end - ts_training_start
        # inference
        ts_inference_start = time.time()
        for i in range(10):
            print("run {}: inference - sample epoch {}".format(run_id, i))
            results.append(str(i))
            time.sleep(0.25)
        ts_inference_end = time.time()
        ts_inference_length = ts_inference_end - ts_inference_start
        ts_total_length = ts_training_length + ts_inference_length
        # return data
        return (results, ts_total_length, ts_training_length, ts_inference_length)
