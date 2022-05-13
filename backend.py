# AUDIU
# backend.py

import os
import json
import time
import flask
import base64
import pathlib
import requests
import mongoengine
import flask_socketio
import flask_mongoengine

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
        # ws_port = port + 1
        ws_port = port
        bk = Backend('static', 'templates', host, port, ws_port, dataset, db_host, db_port, db_name, model_run_src, mp_queue_size, backend_signal_queue)
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
            inference_ratio = output_json.get('results_ratio', None)
            if inference_ratio != '' and inference_ratio != None:
                request_data["inference_ratio"] = inference_ratio
            playlist_names = output_json.get('playlist_names', None)
            if playlist_names != '' and playlist_names != None:
                request_data["playlist_names"] = playlist_names
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
        response = None
        while response == None:
            try:
                response = requests.put(f"http://{target_host_port}/model", json=request_data)
            except:
                response = None
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
    socket_server = None
    socket_clients = None
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
        self.socket_server = None
        self.socket_clients = None
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
        self.socket_init(str(production))
        self.web_serve(str(production))

    ## WEBSOCKET API ##
    def socket_init(self, production='False'):
        self.socket_clients = {}
        self.socket_server = flask_socketio.SocketIO()
        self.socket_server.init_app(self.flask_app)

        def sock_connect(auth):
            client_id = str(flask.request.sid)
            print(f'[ws] client {client_id} connected')
            if client_id not in self.socket_clients:
                self.socket_clients[client_id] = {'watching_runs': [], 'complete_runs': []}

        def sock_disconnect():
            client_id = str(flask.request.sid)
            print(f'[ws] client {client_id} disconnected')
            del self.socket_clients[client_id]

        def sock_subscribe_run(run_id):
            client_id = str(flask.request.sid)
            if run_id and len(run_id) > 0:
                print(f'[ws] client {client_id} subscribed to run {run_id}')
                self.socket_clients[client_id]['watching_runs'].append(run_id)
                print(self.socket_clients)

        self.socket_server.on_event('connect', sock_connect)
        self.socket_server.on_event('disconnect', sock_disconnect)
        self.socket_server.on_event('subscribe_run', sock_subscribe_run)

    def socket_send(self, client_id, event, data):
        self.socket_server.emit(event, data, room=client_id)

    def socket_notify(self, run_id):
        for c in self.socket_clients.keys():
            watching_runs = self.socket_clients[c]['watching_runs']
            for watching_run in watching_runs:
                if watching_run == run_id:
                    self.socket_clients[c]['complete_runs'].append(run_id)
                    self.socket_clients[c]['watching_runs'].remove(run_id)
            for target_run_id in self.socket_clients[c]['complete_runs']:
                self.socket_send(c, 'notify_run', target_run_id)

    ## DATABASE API ##
    # mongo configuration object subclass
    class MongoConfig(object):
        SECRET_KEY = os.environ.get('SECRET_KEY') or DB_KEY

    # mongo model run record subclass
    class ModelRun(mongoengine.Document):
        model_type = mongoengine.StringField(required=True, unique=False)
        playlist_names = mongoengine.ListField(required=False, unique=False)
        playlist_selections = mongoengine.ListField(required=True, unique=False)
        genre_selections = mongoengine.ListField(required=True, unique=False)
        inference_output = mongoengine.ListField(required=False, unique=False)
        inference_ratio = mongoengine.ListField(required=False, unique=False)
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
        inference_ratio = [0, 0]
        playlist_names = []
        try:
            new_model_run = Backend.ModelRun(
                model_type=model_type,
                playlist_names=playlist_names,
                playlist_selections=playlist_selections,
                genre_selections=genre_selections,
                inference_output=inference_output,
                inference_ratio=inference_ratio,
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
    def database_update_model_run_output(self, run_id, inference_output, inference_ratio=None):
        query = Backend.ModelRun.objects(id__exact=run_id)
        if len(query) < 1:
            return False
        model_run = query.first()
        if not model_run:
            return False
        if str(run_id) != str(model_run.id):
            return False
        model_run.inference_output = inference_output
        if inference_ratio:
            model_run.inference_ratio = inference_ratio
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

    # update model run (multiple fields) in database
    def database_update_model_run(self, run_id, run_status=None, inference_output=None, inference_ratio=None, time_profile=None, accuracy=None, playlist_names=None):
        query = Backend.ModelRun.objects(id__exact=run_id)
        if len(query) < 1:
            return False
        model_run = query.first()
        if not model_run:
            return False
        if str(run_id) != str(model_run.id):
            print('3')
            return False
        if run_status:
            model_run.status = run_status
        if inference_output:
            model_run.inference_output = inference_output
        if inference_ratio:
            model_run.inference_ratio = inference_ratio
        if time_profile:
            model_run.ts_complete = time_profile["ts_complete"]
            model_run.time_total = time_profile["ts_total_length"]
            model_run.time_training = time_profile["ts_training_length"]
            model_run.time_inference = time_profile["ts_inference_length"]
        if accuracy != None:
            model_run.accuracy = accuracy
        if playlist_names:
            model_run.playlist_names = playlist_names
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
            model_type = model_run_obj.model_type
            playlist_names = model_run_obj.playlist_names
            genre_selections = model_run_obj.genre_selections
            inference_output = model_run_obj.inference_output
            inference_ratio = model_run_obj.inference_ratio
            inference_output = model_run_obj.inference_output
            validation_accuracy = model_run_obj.accuracy
            ts_profile = {"time_total": model_run_obj.time_total, "time_training": model_run_obj.time_training, "time_inference": model_run_obj.time_inference}
            run_length = model_run_obj.ts_complete - model_run_obj.ts_created
            # return run info
            return flask.jsonify({
                'success': True,
                'message': res_msg_alternate if run_status == "complete" else res_msg_default,
                'data': {
                    'run_id': target_run_id,
                    'run_status': run_status,
                    'run_length': run_length,
                    "model_type": model_type,
                    'ts_profile': ts_profile,
                    'playlist_names': playlist_names,
                    'genre_selections': genre_selections,
                    'inference_output': inference_output,
                    'inference_ratio': inference_ratio,
                    'validation_accuracy': validation_accuracy,
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
            status_update = request_data.get('status', None)
            playlist_names_update = request_data.get('playlist_names', None)
            inference_output_update = request_data.get('inference_output', None)
            inference_accuracy_update = request_data.get('inference_accuracy', None)
            inference_ratio_update = request_data.get('inference_ratio', None)
            if inference_ratio_update:
                inference_ratio_update = [inference_ratio_update['hits'], inference_ratio_update['misses']]
            ts_profile_update = request_data.get('ts_profile', None)
            update_success = self.database_update_model_run(target_run_id,
                                                            run_status=status_update,
                                                            inference_output=inference_output_update,
                                                            inference_ratio=inference_ratio_update,
                                                            time_profile=ts_profile_update,
                                                            accuracy=inference_accuracy_update,
                                                            playlist_names=playlist_names_update)
            if not update_success:
                return (flask.jsonify({'success': False, 'message': 'Server error (failed to update new model run record in database).'}), 500)
            # send update notification over socket if available
            if status_update == 'complete':
                self.socket_notify(target_run_id)
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
        self.socket_server.run(self.flask_app, host=self.host, port=self.web_port)
