"""
Blatantly copied from https://github.com/JohnPaton/huawei-hg659.
"""
import re
import json

import requests
from bs4 import BeautifulSoup

from . import util


class HG659Client:
    _response_data_rx = re.compile(r"/\*(.*)\*/$")

    def __init__(self, host, username, password):
        """
        A client for the Huawei HG659 router.

        :param host: The IP of the router, e.g. "192.168.1.1"
        :param username: The login username
        :param password: The login password
        """
        self.host = host
        self.username = username
        self.password = password

        self._csrf_param = None
        self._csrf_token = None

        # Always use session to maintain cookies
        self._session = requests.Session()

        # init csrf state
        self._refresh_csrf()

    def login(self):
        """
        Log the client in to the router.

        While logged in, the same user cannot log in to the web
        interface. Call .logout() to log back out and unblock the web
        interface again

        :return: The response data from the login attempt
        """
        self._refresh_csrf()
        data = self._auth_data()
        response = self._post("/api/system/user_login", json=data)
        output = self._extract_json(response.text)

        assert output, f"Error logging in. Response content: {response.text}"
        return self._extract_json(response.text)

    def logout(self):
        """
        Log the client out of the router

        :return: The response status of the logout request
        """
        data = self._csrf_data()
        response = self._post("/api/system/user_logout", json=data)
        return response.status_code

    def get_devices(self):
        """
        List all devices known to the router

        :return: A list of dicts containing device info
        """
        response = self._get("/api/system/HostInfo")
        output = self._extract_json(response.text)

        assert output, f"Error getting devices. Response content: {response.text}"
        return output

    def get_current_ip(self):
        """Return the current ip by parsing result of the /api/ntwk/wan service.
        """
        self.login()
        response = self._get('/api/ntwk/wan').text
        json_text = response.replace('while(1); /*', '').replace('*/', '')
        entries = json.loads(json_text)

        key = 'Name'
        value = 'INTERNET_VOICE_R_VID_300'
        entry = [i for i in entries if i[key] == value][0]
        return entry['IPv4Addr']

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = util.base64(util.sha256(value))

    def _request(self, method, path, **kwargs):
        url = f"http://{self.host}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", 2)

        response = self._session.request(method, url, **kwargs,)
        response.raise_for_status()

        param, token = self._extract_csrf(response.text)
        if param and token:
            self._csrf_param = param
            self._csrf_token = token

        return response

    def _get(self, path, **kwargs):
        return self._request("GET", path, **kwargs)

    def _post(self, path, **kwargs):
        return self._request("POST", path, **kwargs)

    def _refresh_csrf(self):
        self._get("/", timeout=1)

    @staticmethod
    def _extract_csrf(response_text):
        """Extract the csrf tokens from an HTML response"""
        param, token = None, None
        soup = BeautifulSoup(response_text, features="html.parser")

        param_elem = soup.find("meta", attrs={"name": "csrf_param"})
        if param_elem:
            param = param_elem.attrs.get("content")

        token_elem = soup.find("meta", attrs={"name": "csrf_token"})
        if token_elem:
            token = token_elem.attrs.get("content")

        return param, token

    @classmethod
    def _extract_json(cls, response_text):
        """Extract the json data from an api response"""
        match = cls._response_data_rx.search(response_text)
        if not match:
            return None
        return json.loads(match.group(1))

    def _encode_password(self):
        return util.sha256(
            self.username + self.password + self._csrf_param + self._csrf_token
        )

    def _csrf_data(self):
        return dict(csrf=dict(csrf_param=self._csrf_param, csrf_token=self._csrf_token))

    def _auth_data(self):
        data = self._csrf_data()
        data.update(
            dict(data=dict(UserName=self.username, Password=self._encode_password()))
        )
        return data

    def __del__(self):
        try:
            self.logout()
        except requests.exceptions.HTTPError as e:
            if str(e).startswith("404"):
                # Weren't logged in, no worries
                pass