import os
import json
import flask
import waitress

HOST = '0.0.0.0'
PORT = 8001  # 3017

class Backend():
    flask_app = None
    static_url_path = ''
    static_folder = 'static'
    template_folder = 'templates'

    def __init__(self, static_url_path = '', static_folder = 'static', template_folder = 'templates'):
        self.static_url_path = static_url_path
        package_dir_path = os.path.dirname(os.path.abspath(__file__))
        self.static_folder = os.path.join(package_dir_path, static_folder)
        self.template_folder = os.path.join(package_dir_path, template_folder)
        self.flask_app = flask.Flask(__name__,
                                     static_url_path=self.static_url_path,
                                     static_folder=self.static_folder,
                                     template_folder=self.template_folder)

    def view_home(self):
        return flask.render_template("index.html")

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

    def bind_routes(self):
        self.flask_app.add_url_rule(
            "/", "home", view_func=self.view_home, methods=['GET'])
        self.flask_app.add_url_rule(
            "/model", "model", view_func=self.view_model, methods=['POST'])
            
    def run_forever(self, production=False, port=3000, host='0.0.0.0'):
        if production:
            waitress.serve(self.flask_app, host=host, port=port)
        else:
            self.flask_app.run(host=host, port=port, debug=True)



def main():
    backend = Backend()
    backend.bind_routes()
    backend.run_forever(True, PORT, HOST)

if __name__ == "__main__":
    main()
