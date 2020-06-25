#!flask/bin/python
from functools import wraps
from flask import request, Response, Flask, make_response
import json

app = Flask(__name__)


def check_auth(username, password):
    """This function is called to check if a username password combination is valid."""
    return username == 'admin' and password == 'secret'


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    return "Hello, World!"


@app.route('/json')
def json_body():
    json_object = {"key1": "value1", "key2": ["value21", "value22"]}
    response = make_response(json.dumps(json_object))
    response.headers['Content-Type'] = 'application/json'
    return response


@app.route('/authentication-required')
@requires_auth
def secret_page():
    return "Authentication successful"


@app.route('/echo-parameters', methods=['GET', 'POST'])
def echo_parameters():
    # use `flat=False` to have all values returned as lists for a given key.
    return json.dumps(request.args.to_dict(flat=False))


@app.route('/echo-method', methods=['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'])
def echo_method():
    response = make_response()
    response.headers['Request-Method'] = request.method
    return response


@app.route('/echo-headers', methods=['GET', 'POST'])
def echo_headers():
    return json.dumps(dict(request.headers))


@app.route('/echo-body', methods=['POST'])
def echo_body():
    return request.stream.read()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
