from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_oauthlib.client import OAuth
from auth0.v3.management import Auth0
from auth0.v3.authentication import GetToken
from six.moves.urllib.parse import urlencode
import stripe

import requests

import hub.settings

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


app = Flask(__name__)
app.config.from_object(settings)
app.debug = True

# get token
get_token = GetToken(app.config['AUTH0_DOMAIN'])
token = get_token.client_credentials(app.config['AUTH0_CLIENT_ID'],
    app.config['AUTH0_CLIENT_SECRET'], 'https://{}/api/v2/'.format(app.config['AUTH0_DOMAIN']))
mgmt_api_token = token['access_token']

auth0_API = Auth0(app.config['AUTH0_DOMAIN'], mgmt_api_token)

oauth = OAuth(app)

auth0 = oauth.remote_app(
    'auth0',
    consumer_key=app.config['AUTH0_CLIENT_ID'],
    consumer_secret=app.config['AUTH0_CLIENT_SECRET'],
    request_token_params={
        'scope': 'openid email profile',
        'audience': 'https://%s/userinfo' % app.config['AUTH0_DOMAIN'] 
    },
    base_url='https://%s' % app.config['AUTH0_DOMAIN'],
    access_token_method='POST',
    access_token_url='/oauth/token',
    authorize_url='/authorize',
)

db = SQLAlchemy(app)

stripe.api_key = app.config['STRIPE_SECRET_KEY']

from . import views
from . import models
