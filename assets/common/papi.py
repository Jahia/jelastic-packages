#!/usr/bin/python3

import argparse
from json import loads as jloads, JSONDecodeError
import requests
from datetime import datetime
from http import HTTPStatus
from os import environ
from sys import exit, stderr, stdout


class Papi():
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
    HTTP_METHODS= ['GET', 'PUT', 'POST', 'DELETE']
    JELASTIC_LOG_FILE = '/var/log/jelastic-packages/papi.log'
    PAPI_SCHEME = 'https'


    def __init__(self, hostname, api_version, token, method, data, path):
        self.path = path
        self.method = method
        if method not in self.HTTP_METHODS:
            self.__printerr("The method should be one of " + self.HTTP_METHODS + ", aborting")
            exit(1)
        if hostname is None:
            self.__printerr("Papi hostname not specified, aborting")
            exit(1)
        if api_version is None:
            self.__printerr("Papi API version not specified, aborting")
            exit(1)
        if token is None:
            self.__printerr("No token provided, aborting")
            exit(1)
        if data is not None:
            try:
                jloads(data)
            except JSONDecodeError:
                self.__printerr("Bad format for data, JSON expected. Aborting")
                exit(1)
        self.data = data
        self.hostname = hostname
        self.api_version = api_version
        self.token = token
        self.base_url = f'{self.PAPI_SCHEME}://{self.hostname}/api/{self.api_version}'
        self.url = f'{self.base_url}/{self.path}'


    def __printerr(self, msg):
        print(f'{msg} ({self.path})', file=stderr)
        with open(self.JELASTIC_LOG_FILE, 'a') as logfile:
            print(f'{datetime.now()} [ERROR] {msg} ({self.method} {self.path})', file=logfile)


    def __printout(self, msg):
        print(msg)
        with open(self.JELASTIC_LOG_FILE, 'a') as logfile:
            print(f'{datetime.now()} [INFO] {self.method} {self.path}', file=logfile)


    def get(self):
        try:
            response = requests.get(url=self.url, headers={self.PAPI_HEADER: self.token})
            if response.status_code != HTTPStatus.OK:
                self.__printerr(f'HTTP/{response.status_code}: {response.reason}')
                exit(self.RETURN_CODES[response.status_code])
        except requests.RequestException as exception:
            self.__printerr("Exception when trying to send the GET request" +
                    str(exception))
            exit(2)
        self.__printout(response.text)


    def put(self):
        try:
            response = requests.put(
                url=self.url, headers={self.PAPI_HEADER: self.token}, json=jloads(self.data))
            if response.status_code != HTTPStatus.OK:
                self.__printerr(f'HTTP/{response.status_code}: {response.reason}')
                exit(self.RETURN_CODES[response.status_code])
        except requests.RequestException as exception:
            self.__printerr("Exception when trying to send the PUT request" +
                    str(exception))
            exit(3)
        self.__printout(response.text)


    def post(self):
        try:
            response = requests.post(
                url=self.url, headers={self.PAPI_HEADER: self.token}, json=jloads(self.data))
            if response.status_code != HTTPStatus.OK:
                self.__printerr(f'HTTP/{response.status_code}: {response.reason}')
                exit(self.RETURN_CODES[response.status_code])
        except requests.RequestException as exception:
            self.__printerr("Exception when trying to send the POST request" +
                    str(exception))
            exit(4)
        self.__printout(response.text)


    def delete(self):
        try:
            response = requests.delete(url=self.url, headers={self.PAPI_HEADER: self.token})
            if response.status_code != HTTPStatus.NO_CONTENT:
                self.__printerr(f'HTTP/{response.status_code}: {response.reason}')
                exit(self.RETURN_CODES[response.status_code])
        except requests.RequestException as exception:
            self.__printerr("Exception when trying to send the DELETE request" +
                    str(exception))
            exit(5)


def parse_args():
    parser = argparse.ArgumentParser(description="Papi parameters")
    parser.add_argument(
        "-e", "--hostname",
        help="Papi hostname, can also be defined as PAPI_HOSTNAME environment variable",
        default=environ.get('PAPI_HOSTNAME')
    )
    parser.add_argument(
        "-a", "--api-version",
        help="Optional, Papi API version, can also be defined as PAPI_API_VERSION" +
            "environment variable",
        default=environ.get('PAPI_API_VERSION')
    )
    parser.add_argument(
        "-t", "--token",
        help="Papi Token, can also be defined as PAPI_TOKEN environment variable",
        default=environ.get('PAPI_TOKEN')
    )
    parser.add_argument(
        "-X", "--method",
        help="Optional, HTTP method to use: GET (default), PUT, POST or DELETE",
        default="GET"
    )
    parser.add_argument(
        "-d", "--data",
        help="Optional, payload to pass to the request",
        required=False
    )
    parser.add_argument(
        "path",
        help="URL's path"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    papi = Papi(
        hostname=args.hostname,
        api_version=args.api_version,
        token=args.token,
        method=args.method,
        data=args.data,
        path=args.path,
    )
    eval(f'papi.{papi.method.lower()}()')
    exit(0)
