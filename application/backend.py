# AUDIU
# backend.py

import os
import sys
import json
import time
import flask
import base64
import pathlib
import requests
import waitress
import mongoengine
import multiprocessing
import flask_mongoengine

# local imports
import sockets

# constants
DB_ID_LEN = 24
DB_KEY = '5tay0ut!'

## BACKEND CLASS ##


# web & websocket backend wrapper class
class Backend():

    ## static methods ##
    # backend web daemon process
    @staticmethod
    def web_run(dataset, host, port, db_host, db_port, db_name, model_run_src, mp_queue_size, prod, backend_signal_queue):
        port = int(port)
        db_port = int(db_port)
        mp_queue_size = int(mp_queue_size)
        prod = bool(prod)
        bk = Backend('static', 'templates', host, port, port + 1, dataset, db_host, db_port, db_name, model_run_src, mp_queue_size, backend_signal_queue)
        bk.run_forever(prod)

    # update model run record status/inference output with local PUT request to backend
    @staticmethod
    def update_model_run_record(run_id, status=None, target_host_port='localhost:80', update_inference_output=False, model_run_src='', calling_th='backend'):
        # paths
        package_dir_path = os.path.dirname(os.path.abspath(__file__))
        model_run_dir_path = os.path.join(package_dir_path, model_run_src)
        model_run_path = pathlib.Path(os.path.join(model_run_dir_path, run_id))
        # setup PUT request data
        request_data = {"run_id": run_id}
        if status != '' and status != None:
            request_data['status'] = status
        if update_inference_output:
            with open(model_run_path / "output.json", 'r') as output_file:
                output_json = json.load(output_file)
            inference_output = output_json.get('results', None)
            if inference_output != '' and inference_output != None:
                request_data["inference_output"] = inference_output
            inference_accuracy = output_json.get('accuracy', None)
            if inference_accuracy != '' and inference_accuracy != None:
                request_data["inference_accuracy"] = inference_accuracy
            ts_profile_json = output_json.get('ts_profile', None)
            if ts_profile_json:
                ts_complete = time.time()
                request_data["ts_profile"] = {
                    "ts_complete": ts_complete,
                    "ts_total_length": float(ts_profile_json.get('ts_total_length', 0)),
                    "ts_training_length": float(ts_profile_json.get('ts_training_length', 0)),
                    "ts_inference_length": float(ts_profile_json.get('ts_inference_length', 0))
                }
        print(f"[{calling_th}] updating model run record with local put request:")
        print(request_data)
        response = requests.put(f"http://{target_host_port}/model", json=request_data)
        response_status = response.status_code
        response_json = response.json()
        print(response_json)
        if response_status != 200:
            return False
        return True

    # instance fields
    flask_app = None
    static_folder = None
    template_folder = None
    static_url_path = None
    package_dir_path = None
    socket_process = None
    socket_signal_queue = None
    backend_signal_queue = None
    model_run_src = ''
    host = ''
    db_host = ''
    ws_port = 0
    web_port = 0
    db_name = ''
    db_port = 0
    db_local = None
    db_engine = None
    mp_queue_size = 10

    # constructor
    def __init__(self,
                 static_folder='static',
                 template_folder='templates',
                 host='localhost',
                 web_port=3000,
                 ws_port=3001,
                 dataset_src='dataset.json',
                 db_host='localhost',
                 db_port=27017,
                 db_name='default',
                 model_run_src='data/runs',
                 mp_queue_size=10,
                 backend_signal_queue=None):
        self.host = host
        self.db_host = db_host
        self.ws_port = ws_port
        self.web_port = web_port
        self.db_name = db_name
        self.db_port = db_port
        self.db_local = {}
        self.db_engine = None
        self.socket_process = None
        self.socket_signal_queue = None
        self.backend_signal_queue = backend_signal_queue
        self.model_run_src = model_run_src
        self.mp_queue_size = mp_queue_size
        self.static_url_path = ''
        self.package_dir_path = os.path.dirname(os.path.abspath(__file__))
        self.dataset_src = os.path.join(self.package_dir_path, dataset_src)
        self.static_folder = os.path.join(self.package_dir_path, static_folder)
        self.template_folder = os.path.join(self.package_dir_path, template_folder)
        self.model_run_dir_path = os.path.join(self.package_dir_path, model_run_src)
        self.flask_app = flask.Flask(__name__, static_url_path=self.static_url_path, static_folder=self.static_folder, template_folder=self.template_folder)

    # start both servers in parallel & connect to db
    def run_forever(self, production=False):
        self.database_init(str(production))
        self.socket_signal_queue = multiprocessing.Queue(self.mp_queue_size)
        self.socket_process = multiprocessing.Process(target=sockets.Sockets.socket_run, args=(str(production), str(self.host), str(self.ws_port), self.socket_signal_queue))
        self.socket_process.start()
        self.web_serve(str(production))

    ## DATABASE API ##
    # mongo configuration object subclass
    class MongoConfig(object):
        SECRET_KEY = os.environ.get('SECRET_KEY') or DB_KEY

    # mongo model run record subclass
    class ModelRun(mongoengine.Document):
        model_type = mongoengine.StringField(required=True, unique=False)
        playlist_selections = mongoengine.ListField(required=True, unique=False)
        genre_selections = mongoengine.ListField(required=True, unique=False)
        inference_output = mongoengine.ListField(required=False, unique=False)
        status = mongoengine.StringField(required=True, unique=False)
        accuracy = mongoengine.DecimalField(min_value=0, precision=6)
        ts_created = mongoengine.DecimalField(min_value=0, precision=6)
        ts_complete = mongoengine.DecimalField(min_value=0, precision=6)
        time_total = mongoengine.DecimalField(min_value=0, precision=6)
        time_training = mongoengine.DecimalField(min_value=0, precision=6)
        time_inference = mongoengine.DecimalField(min_value=0, precision=6)

    # add model run record to database
    def database_new_model_run(self, model_type, playlist_selections, genre_selections, status, ts_created, ts_complete, time_total, time_training, time_inference):
        inference_output = []
        try:
            new_model_run = Backend.ModelRun(
                model_type=model_type,
                playlist_selections=playlist_selections,
                genre_selections=genre_selections,
                inference_output=inference_output,
                status=status,
                ts_created=ts_created,
                ts_complete=ts_complete,
                time_total=time_total,
                time_training=time_training,
                time_inference=time_inference,
            )
            new_model_run.save(force_insert=True)
            return str(new_model_run.id)
        except Exception as e:
            print(e)
            return None

    # get model run from database
    def database_get_model_run(self, run_id):
        query = Backend.ModelRun.objects(id__exact=run_id)
        if len(query) != 1:
            return None
        model_run = query.first()
        if not model_run:
            return None
        return model_run

    # get model run status from database
    def database_get_model_run_status(self, run_id):
        query = Backend.ModelRun.objects(id__exact=run_id)
        if len(query) != 1:
            return None
        model_run = query.first()
        if not model_run:
            return None
        model_run_status = model_run.status
        return model_run_status

    # update model run status in database
    def database_update_model_run_status(self, run_id, run_status):
        query = Backend.ModelRun.objects(id__exact=run_id)
        if len(query) < 1:
            return False
        model_run = query.first()
        if not model_run:
            return False
        if str(run_id) != str(model_run.id):
            print('3')
            return False
        model_run.status = run_status
        model_run.save()
        return True

    # update model run output
    def database_update_model_run_output(self, run_id, inference_output):
        query = Backend.ModelRun.objects(id__exact=run_id)
        if len(query) < 1:
            return False
        model_run = query.first()
        if not model_run:
            return False
        if str(run_id) != str(model_run.id):
            return False
        model_run.inference_output = inference_output
        model_run.save()
        return True

    # update model run time_profile
    def database_update_model_run_time_profile(self, run_id, time_profile):
        query = Backend.ModelRun.objects(id__exact=run_id)
        if len(query) < 1:
            return False
        model_run = query.first()
        if not model_run:
            return False
        if str(run_id) != str(model_run.id):
            return False
        model_run.ts_complete = time_profile["ts_complete"]
        model_run.time_total = time_profile["ts_total_length"]
        model_run.time_training = time_profile["ts_training_length"]
        model_run.time_inference = time_profile["ts_inference_length"]
        model_run.save()
        return True

    # update model run accuracy
    def database_update_model_run_accuracy(self, run_id, accuracy):
        query = Backend.ModelRun.objects(id__exact=run_id)
        if len(query) < 1:
            return False
        model_run = query.first()
        if not model_run:
            return False
        if str(run_id) != str(model_run.id):
            return False
        model_run.accuracy = accuracy
        model_run.save()
        return True

    # import dataset & connect to db
    def database_init(self, production='False'):
        production = bool(production)
        # mongo init
        self.db_engine = flask_mongoengine.MongoEngine()
        self.flask_app.config.from_object(Backend.MongoConfig)
        self.flask_app.config['MONGODB_SETTINGS'] = {"db": self.db_name, "host": self.db_host, "port": self.db_port}
        self.db_engine.init_app(self.flask_app)
        # local init
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
        self.db_local['playlists'] = playlists
        self.db_local['genres'] = genres
        self.db_local['models'] = models
        self.db_local['config'] = config

    ## WEB SERVER ##
    # encode json data to embed into client JavaScript
    def json_encode(self, obj, charset='ascii'):
        try:
            return (base64.b64encode(json.dumps(obj).encode(charset))).decode(charset)
        except:
            return None

    # decode raw data from post request into json object
    def request_decode(self, raw_data, charset='ascii'):
        try:
            return json.loads(raw_data.decode(charset))
        except:
            return None

    # web home page route
    def view_home(self):
        print("[backend] GET @ /")
        return flask.render_template("index.html",
                                     config=self.json_encode(self.db_local['config']),
                                     models=self.json_encode(self.db_local['models']),
                                     genres=self.json_encode(list(self.db_local['genres'].keys())))

    # web model api route
    def view_model(self):
        res_msg_default = 'Recommendations generating...'
        res_msg_alternate = 'Recommendations generated!'
        method = flask.request.method
        print(f"[backend] {method} @ /model")
        if method == "POST":  # POST
            ## process a new model run ##
            # parse request data
            request_data = None
            try:
                request_data = self.request_decode(flask.request.get_data())
            except:
                return (flask.jsonify({'success': False, 'message': 'Invalid request input data (invalid format).'}), 400)
            selected_model = request_data.get('selected_model', self.db_local['config']['defaults']['selected_model'])
            playlist_selections = request_data.get('playlist_selections', self.db_local['config']['defaults']['playlist_selections'])
            genre_selections = request_data.get('genre_selections', self.db_local['config']['defaults']['genre_selections'])
            # create model run record
            ts_created = time.time()
            run_id = self.database_new_model_run(selected_model, playlist_selections, genre_selections, "created", ts_created, 0, 0, 0, 0)
            if run_id == None or not run_id:
                return (flask.jsonify({'success': False, 'message': 'Server error (failed to create new model run record in database).'}), 500)
            request_data = {"run_id": run_id, "selected_model": selected_model, "playlist_selections": playlist_selections, "genre_selections": genre_selections}
            # save request info for parent process to handle
            model_run_path = pathlib.Path(os.path.join(self.model_run_dir_path, run_id))
            model_run_path.mkdir(parents=True, exist_ok=True)
            with open(model_run_path / 'request.json', 'w') as f:
                json.dump(request_data, f, indent=4, sort_keys=False)
            self.backend_signal_queue.put("main:recommendations-run:{}".format(run_id))
            # return run info
            return flask.jsonify({
                'success': True,
                'message': res_msg_default,
                'data': {
                    'run_id': run_id,
                    'selected_model': selected_model,
                    'playlist_selections': playlist_selections,
                    'genre_selections': genre_selections,
                    "ts_created": ts_created
                }
            })
        elif method == "GET":  # GET
            ## check status of existing model run ##
            # parse & verify run id
            target_run_id = flask.request.args.get("run_id", "")
            if target_run_id == None or not target_run_id or target_run_id == "" or len(target_run_id) != DB_ID_LEN:
                return (flask.jsonify({'success': False, 'message': 'Invalid request input data (invalid "run_id").'}), 400)
            # check model run status in database
            run_status = self.database_get_model_run_status(target_run_id)
            if run_status == None or not run_status:
                return (flask.jsonify({'success': False, 'message': 'Server error (failed to retrieve model run record from database).'}), 500)
            model_run_obj = self.database_get_model_run(target_run_id)
            inference_output = model_run_obj.inference_output
            ts_profile = {"time_total": model_run_obj.time_total, "time_training": model_run_obj.time_training, "time_inference": model_run_obj.time_inference}
            # return run info
            return flask.jsonify({
                'success': True,
                'message': res_msg_alternate if run_status == "complete" else res_msg_default,
                'data': {
                    'run_id': target_run_id,
                    'run_status': run_status,
                    'ts_profile': ts_profile,
                    'inference_output': inference_output
                }
            })
        elif method == "PUT":  # PUT
            ## update model status and run output results (between processes) ##
            # (accessed by main process when child model run process starts and ends)
            # parse request data
            request_data = None
            try:
                request_data = self.request_decode(flask.request.get_data())
            except:
                return (flask.jsonify({'success': False, 'message': 'Invalid request input data (invalid format).'}), 400)
            # parse & verify run id
            target_run_id = request_data.get("run_id", "")
            if target_run_id == None or not target_run_id or target_run_id == "" or len(target_run_id) != DB_ID_LEN:
                return (flask.jsonify({'success': False, 'message': 'Invalid request input data (invalid "run_id").'}), 400)
            status_update = request_data.get('status', '')
            inference_output_update = request_data.get('inference_output', None)
            inference_accuracy_update = request_data.get('inference_accuracy', None)
            ts_profile_update = request_data.get('ts_profile', None)
            if status_update != '':
                update_success = self.database_update_model_run_status(target_run_id, status_update)
                if not update_success:
                    return (flask.jsonify({'success': False, 'message': 'Server error (failed to update new model run record status in database).'}), 500)
            if inference_output_update != '' and inference_output_update != None:
                update_success = self.database_update_model_run_output(target_run_id, inference_output_update)
                if not update_success:
                    return (flask.jsonify({'success': False, 'message': 'Server error (failed to update new model run record inference output in database).'}), 500)
            if ts_profile_update != '' and ts_profile_update != None:
                update_success = self.database_update_model_run_time_profile(target_run_id, ts_profile_update)
                if not update_success:
                    return (flask.jsonify({'success': False, 'message': 'Server error (failed to update new model run record time profile in database).'}), 500)
            if inference_accuracy_update != '' and inference_accuracy_update != None:
                update_success = self.database_update_model_run_accuracy(target_run_id, inference_accuracy_update)
                if not update_success:
                    return (flask.jsonify({'success': False, 'message': 'Server error (failed to update new model run record inference accuracy in database).'}), 500)
            # return success
            return flask.jsonify({
                'success': True,
                'message': "Model run record updated",
                'data': {
                    'run_id': target_run_id,
                }
            })
        else:  # invalid method
            return (flask.jsonify({'success': False, 'message': 'Invalid request type/method "{}".'.format(method)}), 405)

    # web route setup
    def bind_routes(self):
        self.flask_app.add_url_rule("/", "home", view_func=self.view_home, methods=['GET'])
        self.flask_app.add_url_rule("/fresh", "fresh", view_func=self.view_home, methods=['GET'])
        self.flask_app.add_url_rule("/model", "model", view_func=self.view_model, methods=['POST', 'GET', 'PUT'])

    # web server start
    def web_serve(self, production='False'):
        production = bool(production)
        self.bind_routes()
        if production:
            waitress.serve(self.flask_app, host=self.host, port=self.web_port)
        else:
            self.flask_app.run(host=self.host, port=self.web_port, debug=True)
