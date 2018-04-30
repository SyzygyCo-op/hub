from functools import wraps
import json
from os import environ as env

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask_oauthlib.client import OAuth
from auth0.v3.management import Auth0
from auth0.v3.authentication import GetToken
from six.moves.urllib.parse import urlencode

import requests

import constants

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


APP = Flask(__name__, static_url_path='/public', static_folder='./public')
APP.config.from_object(constants)
APP.debug = True

# get token
get_token = GetToken(APP.config['AUTH0_DOMAIN'])
token = get_token.client_credentials(APP.config['AUTH0_CLIENT_ID'],
    APP.config['AUTH0_CLIENT_SECRET'], 'https://{}/api/v2/'.format(APP.config['AUTH0_DOMAIN']))
mgmt_api_token = token['access_token']

auth0_API = Auth0(APP.config['AUTH0_DOMAIN'], mgmt_api_token)


# Format error response and append status code.
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


@APP.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


@APP.errorhandler(Exception)
def handle_auth_error(ex):
    response = jsonify(message=ex)
    return response

oauth = OAuth(APP)

auth0 = oauth.remote_app(
    'auth0',
    consumer_key=APP.config['AUTH0_CLIENT_ID'],
    consumer_secret=APP.config['AUTH0_CLIENT_SECRET'],
    request_token_params={
        'scope': 'openid email profile',
        'audience': 'https://%s/userinfo' % APP.config['AUTH0_DOMAIN'] 
    },
    base_url='https://%s' % APP.config['AUTH0_DOMAIN'],
    access_token_method='POST',
    access_token_url='/oauth/token',
    authorize_url='/authorize',
)


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


# Controllers API
@APP.route('/')
def home():
    return render_template('home.html')


@APP.route('/callback')
def callback_handling():
    resp = auth0.authorized_response()
    if resp is None:
        raise AuthError({'code': request.args['error'],
                         'description': request.args['error_description']}, 401)

    url = 'https://' + APP.config['AUTH0_DOMAIN'] + '/userinfo'
    headers = {'authorization': 'Bearer ' + resp['access_token']}
    resp = requests.get(url, headers=headers)
    userinfo = resp.json()

    session[constants.JWT_PAYLOAD] = userinfo

    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }

    return redirect('/dashboard')


@APP.route('/login')
def login():
    return auth0.authorize(callback=APP.config['AUTH0_CALLBACK_URL'])


@APP.route('/logout')
def logout():
    session.clear()
    params = {'returnTo': url_for('home', _external=True), 'client_id': APP.config['AUTH0_CLIENT_ID']}
    return redirect(auth0.base_url + '/v2/logout?' + urlencode(params))


@APP.route('/dashboard')
@requires_auth
def dashboard():
    user = auth0_API.users.get(session['profile']['user_id'])
    return render_template('dashboard.html',
                           userinfo=session['profile']['user_id'],
                           userinfo_pretty=json.dumps(session[constants.JWT_PAYLOAD], indent=4))


if __name__ == "__main__":
    APP.run(host='0.0.0.0', port=env.get('PORT', 4000))
