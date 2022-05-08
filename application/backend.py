# AUDIU
# backend.py

import os
import sys
import json
import time
import flask
import base64
import pathlib
import waitress
import mongoengine
import multiprocessing
import flask_mongoengine

# local imports
import sockets
DB_KEY = '5tay0ut!'

## BACKEND CLASS ##

# web & websocket backend wrapper class
class Backend():

    # backend web daemon process
    @staticmethod
    def web_run(dataset, host, port, db_host, db_port, db_name, model_run_src, prod, backend_signal_queue):
        port = int(port)
        db_port = int(db_port)
        prod = bool(prod)
        bk = Backend('static', 'templates', host, port, port + 1,
                    dataset, db_host, db_port, db_name, model_run_src, backend_signal_queue)
        bk.run_forever(prod)

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
    # constructor
    def __init__(self, static_folder='static', template_folder='templates', host='localhost', web_port=3000, ws_port=3001, dataset_src='dataset.json', db_host='localhost', db_port=27017, db_name='default', model_run_src='data/runs', backend_signal_queue=None):
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
        self.static_url_path = ''
        self.package_dir_path = os.path.dirname(os.path.abspath(__file__))
        self.dataset_src = os.path.join(self.package_dir_path, dataset_src)
        self.static_folder = os.path.join(self.package_dir_path, static_folder)
        self.template_folder = os.path.join(self.package_dir_path, template_folder)
        self.model_run_dir_path = os.path.join(
            self.package_dir_path, model_run_src)
        self.flask_app = flask.Flask(__name__,
                                     static_url_path=self.static_url_path,
                                     static_folder=self.static_folder,
                                     template_folder=self.template_folder)
    # start both servers in parallel & connect to db
    def run_forever(self, production=False):
        self.database_init(str(production))
        self.socket_signal_queue = multiprocessing.Queue(10)
        self.socket_process = multiprocessing.Process(
            target=sockets.Sockets.socket_run, args=(str(production), str(self.host), str(self.ws_port), self.socket_signal_queue))
        self.socket_process.start()
        self.web_serve(str(production))

    ## DATABASE API ##
    # mongo configuration object
    class MongoConfig(object):
        SECRET_KEY = os.environ.get('SECRET_KEY') or DB_KEY
    # mongo model run record class
    class ModelRun(mongoengine.Document):
        model_type = mongoengine.StringField(required=True, unique=False)
        playlist_selections = mongoengine.ListField(required=True, unique=False)
        genre_selections = mongoengine.ListField(required=True, unique=False)
        status = mongoengine.StringField(required=True, unique=False)
        ts_created = mongoengine.DecimalField(min_value=0, precision=6)
        ts_complete = mongoengine.DecimalField(min_value=0, precision=6)
        time_total = mongoengine.DecimalField(min_value=0, precision=6)
        time_training = mongoengine.DecimalField(min_value=0, precision=6)
        time_inference = mongoengine.DecimalField(min_value=0, precision=6)
    # add model run record to database
    def database_new_model_run(self, model_type, playlist_selections, genre_selections, status, ts_created, ts_complete, time_total, time_training, time_inference):
        new_model_run = Backend.ModelRun(model_type=model_type, playlist_selections=playlist_selections, genre_selections=genre_selections, status=status,
                        ts_created=ts_created, ts_complete=ts_complete, time_total=time_total, time_training=time_training, time_inference=time_inference,)
        new_model_run.save(force_insert=True)
        return str(new_model_run.id)
    # import dataset & connect to db
    def database_init(self, production='False'):
        production = bool(production)
        # mongo init
        self.db_engine = flask_mongoengine.MongoEngine()
        self.flask_app.config.from_object(Backend.MongoConfig)
        self.flask_app.config['MONGODB_SETTINGS'] = {
            "db": self.db_name,
            "host": self.db_host,
            "port": self.db_port
        }
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
    # request decode
    def request_decode(self, raw_data):
        raw_data = raw_data.decode('ascii')
        return json.loads(raw_data)
    # web home page route
    def view_home(self):
        return flask.render_template("index.html",
            config=self.json_encode(self.db_local['config']),
            genres=self.json_encode(list(self.db_local['genres'].keys())),
            models=self.json_encode(self.db_local['models']))
    # web model api route
    def view_model(self):
        # parse request data
        request_data = None
        try:
            request_data = self.request_decode(flask.request.get_data())
        except Exception as e:
            return (flask.jsonify({
                'success': False,
                'message': 'Invalid request input data.'
            }), 400)
        selected_model = request_data.get('selected_model', self.db_local['config']['defaults']['selected_model'])
        playlist_selections = request_data.get('playlist_selections', self.db_local['config']['defaults']['playlist_selections'])
        genre_selections = request_data.get('genre_selections', self.db_local['config']['defaults']['genre_selections'])
        # create model run record
        ts_created = time.time()
        run_id = self.database_new_model_run(selected_model, playlist_selections, genre_selections, "created", ts_created, 0,0,0,0)
        request_data = {
            "run_id": run_id,
            "selected_model": selected_model,
            "playlist_selections": playlist_selections,
            "genre_selections": genre_selections
        }
        # save request info for parent process to handle
        model_run_path = pathlib.Path(os.path.join(self.model_run_dir_path, run_id))
        model_run_path.mkdir(parents=True, exist_ok=True)
        with open(model_run_path / 'request.json', 'w') as f:
            json.dump(request_data, f, indent=4, sort_keys=False)
        self.backend_signal_queue.put("main:recommendations-run:{}".format(run_id))
        # return run info
        return flask.jsonify({
            'success': True,
            'message': 'Recommendations generating...',
            'data': {
                'run_id': run_id,
                'selected_model': selected_model,
                'playlist_selections': playlist_selections,
                'genre_selections': genre_selections,
                "ts_created": ts_created
            }
        })
    # convenience conversion
    def json_encode(self, obj, charset='ascii'):
        return (base64.b64encode(json.dumps(obj).encode(charset))).decode(charset)
    # web route setup
    def bind_routes(self):
        self.flask_app.add_url_rule(
            "/", "home", view_func=self.view_home, methods=['GET'])
        self.flask_app.add_url_rule(
            "/fresh", "fresh", view_func=self.view_home, methods=['GET'])
        self.flask_app.add_url_rule(
            "/model", "model", view_func=self.view_model, methods=['POST'])
    # web server start
    def web_serve(self, production='False'):
        production = bool(production)
        self.bind_routes()
        if production:
            waitress.serve(self.flask_app, host=self.host, port=self.web_port)
        else:
            self.flask_app.run(host=self.host, port=self.web_port, debug=True)
    
