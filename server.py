#!/usr/bin/env python3
import argparse
import configparser
import requests

from sys import exit
from urllib.parse import quote_plus

import twitter

from jsonrpc import JSONRPCResponseManager, dispatcher
from requests_oauthlib import OAuth1
from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple

CREDS_PATH = 'creds.conf'

# Have to define these as globals because they need to be referenced by
# the methods of the server and also updated by those same methods.
# If they were passed in as arguments to a method-creator, then
# the method wouldn't see any updates.
config = configparser.ConfigParser()
config.read(CREDS_PATH)


def _validate_config(config):
    if 'app-creds' not in config or \
            'apiKey' not in config['app-creds'] or \
            'apiSecret' not in config['app-creds']:
        print('Malformed api credentials')
        exit(1)
    for user in filter(lambda u: u.startswith('user-'), config.keys()):
        if 'accessToken' not in config[user] or 'accessSecret' not in config[user]:
            print(f'Malformed user {user}')
            exit(1)

def _build_app(config, user):
    return twitter.Api(
        consumer_key=config['app-creds']['apiKey'],
        consumer_secret=config['app-creds']['apiSecret'],
        access_token_key=config[user]['accessToken'],
        access_token_secret=config[user]['accessSecret'])

_validate_config(config)
apps = {user[5:]: _build_app(config, user) \
    for user in filter(lambda u: u.startswith('user-'), config.keys())}

@dispatcher.add_method
def tweet(**kwargs):
    print(f'DEBUG - {kwargs}')
    # Newlines get double-escaped between the client and the server
    kwargs['status'] = kwargs['status'].replace('\\n', '\n')
    user = kwargs.get('user')
    if not user:
        print(f'DEBUG - {list(apps.keys())}')
        if len(list(apps.keys())) != 1:
            return {
                'result': 'Must pass an explicit user if more than one user is registered in the server',
                'jsonrpc': '2.0'
            }
        else:
            return _send_tweet(apps, next(iter(apps.keys())), kwargs['status'])
    return _send_tweet(apps, kwargs['user'], kwargs['status'])


def _send_tweet(apps, username, status):
    status = apps[username].PostUpdate(status=status)
    print(status)
    return {
        'id': status.id,
        'user': status.user.screen_name,
        'status': status.text,
        'url': f'https://twitter.com/{status.user.screen_name}/status/{status.id}'}


@dispatcher.add_method
def register(**kwargs):
    oauth = OAuth1(config['app-creds']['apiKey'], client_secret=config['app-creds']['apiSecret'])
    # "oob" as the callback_url enables PIN-based authentication
    r = requests.post(url=f'https://api.twitter.com/oauth/request_token?oauth_callback=oob', auth=oauth, headers={"Content-type": "application/x-www-form-urlencoded"})
    token = dict([e.split('=') for e in r.text.split('&')])['oauth_token']
    return {'oauth_token': token}


@dispatcher.add_method
def register_complete(**kwargs):
    token = kwargs['oauth_token']
    pin = kwargs['pin']
    client_id = config['app-creds']['apiKey']
    client_secret = config['app-creds']['apiSecret']
    oauth = OAuth1(client_id, client_secret=client_secret)
    print(f'DEBUG - token is {token}, pin is {pin}')
    r = requests.post(url=f'https://api.twitter.com/oauth/access_token?oauth_verifier={pin}&oauth_token={token}', auth=oauth)
    final_creds = dict([e.split('=') for e in r.text.split('&')])
    screen_name = final_creds['screen_name'].lower()
    accessToken = final_creds['oauth_token']
    accessSecret = final_creds['oauth_token_secret']
    apps[screen_name] = twitter.Api(
        consumer_key=client_id,
        consumer_secret=client_secret,
        access_token_key=accessToken,
        access_token_secret=accessSecret)
    config[f'user-{screen_name}'] = {
        'accessToken': accessToken,
        'accessSecret': accessSecret
    }
    with open(CREDS_PATH, 'w') as configfile:
        config.write(configfile)
    return f'Registered a new app for user {screen_name}'

def application_builder(args):
    @Request.application
    def application(request):
        print(request.data)

        dispatcher['users'] = lambda: list(apps.keys())

        response = JSONRPCResponseManager.handle(
            request.data, dispatcher)
        return Response(response.json, mimetype='application/json')
    return application

if __name__ == '__main__':
    # Yes, this is a no-op parser right now - but it could be useful in the future!
    # (E.g. if we want to provide a callback_url)
    parser = argparse.ArgumentParser()
    run_simple('0.0.0.0', 4000, application_builder(parser.parse_args()))
