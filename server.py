#!/usr/bin/env python3
import configparser
import twitter

from werkzeug.wrappers import Request, Response
from werkzeug.serving import run_simple

from jsonrpc import JSONRPCResponseManager, dispatcher

from sys import exit


def tweet_builder(apps):
    # Cannot use @dispatcher.add_mathod because `config` is needed as parameter
    def tweet(**kwargs):
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
    return tweet


def _send_tweet(apps, username, status):
    status = apps[username].PostUpdate(status=status)
    print(status)
    return {'id': status.id, 'user': status.user.screen_name, 'status': status.text}


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


@Request.application
def application(request):
    print(request.data)
    config = configparser.ConfigParser()
    config.read('creds.conf')

    _validate_config(config)
    apps = {user[5:]: _build_app(config, user) \
        for user in filter(lambda u: u.startswith('user-'), config.keys())}

    dispatcher['users'] = lambda: list(apps.keys())
    dispatcher['tweet'] = tweet_builder(apps)

    response = JSONRPCResponseManager.handle(
        request.data, dispatcher)
    return Response(response.json, mimetype='application/json')

if __name__ == '__main__':
    run_simple('localhost', 4000, application)
