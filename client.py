#!/usr/bin/env python3

import argparse
import requests
import json


def users(args):
    _make_call('users')


def tweet(args):
    _make_call('tweet', params={'status':args.status})


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
    print(response['result'])

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

    args = parser.parse_args()
    if 'func' not in args.__dict__:
        print(f'Pass a subparser: {[key for key in subparsers.choices.keys()]}')
        exit(1)
    args.func(args)
