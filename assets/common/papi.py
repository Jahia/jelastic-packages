#!/usr/bin/python3

import argparse
import json
import requests
from datetime import datetime
from http import HTTPStatus
from os import environ
from sys import exit, stderr, stdout


PAPI_HEADER = 'X-PAPI-KEY'
# The maximum value for a sys.exit() return code is 255 so we can't return
# the HTTP code.
# Those two digits return codes try to be as close as possible to the original
# HTTP code.
RETURN_CODES = {
    HTTPStatus.BAD_REQUEST: 40,
    HTTPStatus.FORBIDDEN: 43,
    HTTPStatus.NOT_FOUND: 44,
    HTTPStatus.CONFLICT: 49,
    HTTPStatus.INTERNAL_SERVER_ERROR: 50,
    HTTPStatus.SERVICE_UNAVAILABLE: 53,
}
JELASTIC_LOG_FILE='/tmp/test'


def init():
    parser = argparse.ArgumentParser(description="Papi parameters")
    parser.add_argument(
        "-t", "--token",
        help="Papi Token, can also be defined as PAPI_TOKEN environment variable",
        default=environ.get('PAPI_TOKEN')
    )
    parser.add_argument(
        "-X", "--method",
        help="HTTP method to use: GET, PUT, POST or DELETE",
        default="GET"
    )
    parser.add_argument(
        "-d", "--data",
        help="Payload to pass to the request",
        required=False
    )
    parser.add_argument(
        "url",
        help="Papi URL"
    )
    args = parser.parse_args()
    
    if args.token is None:
        printerr("No token provided, aborting", args.url)
        exit(1)

    return args


def printerr(msg, url):
    print(f'{msg} ({url})', file=stderr)
    with open(JELASTIC_LOG_FILE, 'a') as logfile:
        print(f'{datetime.now()} [ERROR] {msg} ({url})', file=logfile)


def printout(msg, url):
    print(msg)
    with open(JELASTIC_LOG_FILE, 'a') as logfile:
        print(f'{datetime.now()} [INFO] {url}', file=logfile)


def get(url, token):
    try:
        response = requests.get(url=url, headers={PAPI_HEADER: token})
        if response.status_code != HTTPStatus.OK:
            printerr(f"HTTP/{response.status_code}: {response.reason}", url)
            exit(RETURN_CODES[response.status_code])
    except requests.RequestException as exception:
        printerr("Exception when trying to send the GET request" + str(exception), url)
        exit(2)
    printout(response.json(), url)


def put(url, token, data):
    try:
        response = requests.put(url=url, headers={PAPI_HEADER: token}, json=json.loads(data))
        if response.status_code != HTTPStatus.OK:
            printerr(f"HTTP/{response.status_code}: {response.reason}", url)
            exit(RETURN_CODES[response.status_code])
    except requests.RequestException as exception:
        printerr("Exception when trying to send the PUT request" + str(exception), url)
        exit(3)
    printout(response.json(), url)


def post(url, token, data):
    try:
        response = requests.post(url=url, headers={PAPI_HEADER: token}, json=json.loads(data))
        if response.status_code != HTTPStatus.OK:
            printerr(f"HTTP/{response.status_code}: {response.reason}", url)
            exit(RETURN_CODES[response.status_code])
    except requests.RequestException as exception:
        printerr("Exception when trying to send the POST request" + str(exception), url)
        exit(4)
    printout(response.json(), url)


def delete(url, token):
    try:
        response = requests.delete(url=url, headers={PAPI_HEADER: token})
        if response.status_code != HTTPStatus.NO_CONTENT:
            printerr(f"HTTP/{response.status_code}: {response.reason}", url)
            exit(RETURN_CODES[response.status_code])
    except requests.RequestException as exception:
        printerr("Exception when trying to send the DELETE request" + str(exception), url)
        exit(5)


if __name__ == "__main__":
    args = init()
    if args.method == 'GET':
        get(args.url, args.token)
    elif args.method == 'PUT':
        put(args.url, args.token, args.data)
    elif args.method == 'POST':
        post(args.url, args.token, args.data)
    elif args.method == 'DELETE':
        delete(args.url, args.token)
    exit(0)
