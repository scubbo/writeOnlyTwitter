#!/usr/bin/env python3

import argparse
import requests
import json


def users(args):
    _make_call_and_print('users')


def tweet(args):
    _make_call_and_print('tweet', params={'status':args.status})


def register(args):
    response = _make_call('register')
    token = response['result']['oauth_token']
    print(f'Go to https://api.twitter.com/oauth/authorize?oauth_token={token}, follow the prompts and login, then enter the resultant PIN below')
    pin = input('>> ')
    _make_call_and_print('register_complete', params={'oauth_token': token, 'pin': pin})


def _make_call_and_print(method, params=None):
  print(_make_call(method, params)['result'])


def _make_call(method, params=None):
    payload = {
        'method': method,
        'jsonrpc': '2.0',
        'id': 0
    }
    if params:
        payload['params'] = params

    response = requests.post(
        f'http://localhost:{args.port}/jsonrpc',
        data=json.dumps(payload),
        headers={'content-type': 'application/json'}).json()
    return response


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4000)

    subparsers = parser.add_subparsers()

    users_parser = subparsers.add_parser('users')
    users_parser.set_defaults(func=users)

    tweet_parser = subparsers.add_parser('tweet')
    tweet_parser.add_argument('--status', required=True)
    tweet_parser.add_argument('--user')
    tweet_parser.set_defaults(func=tweet)

    register_parser = subparsers.add_parser('register')
    register_parser.set_defaults(func=register)

    args = parser.parse_args()
    if 'func' not in args.__dict__:
        print(f'Pass a subparser: {[key for key in subparsers.choices.keys()]}')
        exit(1)
    args.func(args)
