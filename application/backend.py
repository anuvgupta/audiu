import os
import json
import flask
import asyncio
import waitress
import websockets
import multiprocessing


HOST = '0.0.0.0'
PORT = 8001
PROD = True

## WEBSOCKET SERVER ##
# socket server start


def socket_run(production='False', host='localhost', port='3000', signal_queue=None):
    port = int(port)
    production = bool(production)
    # socket server event handler
    async def socket_handler(websocket):
        async for message in websocket:
            print("[ws] socket received: {}".format(message))
            # await websocket.send(message)  # echo server
    # socket server event loop
    async def socket_serve(host, port):
        async with websockets.serve(socket_handler, host, port):
            await asyncio.Future()  # run forever
    # socket server start
    asyncio.run(socket_serve(host, port))

## BACKEND WRAPPER ##
# web & websocket wrapper class
class Backend():

    # instance fields
    flask_app = None
    static_folder = None
    template_folder = None
    static_url_path = None
    package_dir_path = None
    socket_process = None
    socket_signal_queue = None
    host = ''
    ws_port = 0
    web_port = 0
    # constructor
    def __init__(self, static_folder='static', template_folder='templates', host='localhost', web_port=3000, ws_port=3001):
        self.host = host
        self.ws_port = ws_port
        self.web_port = web_port
        self.socket_process = None
        self.socket_signal_queue = None
        self.static_url_path = ''
        self.package_dir_path = os.path.dirname(os.path.abspath(__file__))
        self.static_folder = os.path.join(self.package_dir_path, static_folder)
        self.template_folder = os.path.join(self.package_dir_path, template_folder)
        self.flask_app = flask.Flask(__name__,
                                     static_url_path=self.static_url_path,
                                     static_folder=self.static_folder,
                                     template_folder=self.template_folder)

    ## WEB SERVER ##
    # web home page route
    def view_home(self):
        return flask.render_template("index.html")
    # web model api route
    def view_model(self):
        try:
            request_json = flask.request.get_json()
        except flask.BadRequest:
            return (flask.jsonify({
                'success': False,
                'message': 'Invalid request input data.'
            }), 400)
        else:
            return flask.jsonify({
                'success': True,
                'message': 'Recommendations generated.',
                'data': {
                    'a': request_json.get('a'),
                    'c': request_json.get('c'),
                    'e': request_json.get('e')
                }
            })
    # web route setup
    def bind_routes(self):
        self.flask_app.add_url_rule(
            "/", "home", view_func=self.view_home, methods=['GET'])
        self.flask_app.add_url_rule(
            "/model", "model", view_func=self.view_model, methods=['POST'])
    # web server start
    def web_run(self, production='False'):
        production = bool(production)
        self.bind_routes()
        if production:
            waitress.serve(self.flask_app, host=self.host, port=self.web_port)
        else:
            self.flask_app.run(host=self.host, port=self.web_port, debug=True)
        
    ## BOTH SERVERS ##
    # start both servers in parallel
    def run_forever(self, production=False):
        self.socket_signal_queue = multiprocessing.Queue()
        self.socket_process = multiprocessing.Process(
            target=socket_run, args=(str(production), str(self.host), str(self.ws_port), self.socket_signal_queue))
        self.socket_process.start()
        self.web_run(str(production))
        self.socket_process.join()


# backend test main entry point
def main():
    Backend('static', 'templates', HOST, PORT, PORT + 1).run_forever(PROD)

# thread entry point
if __name__ == "__main__":
    main()
