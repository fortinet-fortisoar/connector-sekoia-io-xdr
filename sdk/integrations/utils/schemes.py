""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from __future__ import absolute_import
import base64

from cshmac.exceptions import HmacValidationException
from cshmac.validators import validate_hmac_message
from django.conf import settings
from django.contrib.auth.models import User
import requests
import json
import subprocess
import logging
from rest_framework import authentication, exceptions

logger = logging.getLogger('postman')


def _maybe_create_user(username):
    """
    Creates a "builtin" user tied to a specific auth type if it does not \
    already exist, otherwise returns the existing user.

   :param str username: The username of the user to create / retrieve

   :return: The User object that was created / retrieved
   :rtype: User
    """
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        logger.warn('User does not exist, creating new user')
        return User.objects.create_user(username=username)

def decode_payload(request):
    try:
        bodyless_method = ['GET', 'HEAD']
        method  = request.method
        encode_type = request.headers.get('FSR-Encoding')
        if not method in bodyless_method and encode_type:
            input_data = json.loads(request.body)
            if encode_type == 'fsr':
                output = subprocess.check_output(['/opt/cyops-auth/.env/bin/python',
                                                  '/opt/cyops/configs/scripts/manage_passwords.py',
                                                  '--decrypt',
                                                  input_data.pop('payload', ''),
                                                  'jQp3(7@jod#j38d1']
                                                 ).strip().decode()
                output = json.loads(output.replace('Password:', ''))
                input_data.update(output)
                return json.dumps(input_data).encode('utf-8')
            elif encode_type == 'base64':
                pass
        return request.body
    except Exception as e:
        logger.warn("Error occured while decoding the request body ERROR:: {0}".format(str(e)))

class HmacAuthenticationScheme(authentication.BaseAuthentication):
    """
    Authentication scheme that uses HMAC to identify the incoming user and
    authenticate the message.

    Expects the Authorization header be provided, and start with CS . Otherwise,
    it will move on to any subsequent authentication schemes.

    Any valid HMAC request (using Sealab's keys) is associated with the
    Sealab HMAC user.
    """

    def authenticate(self, request):
        meta = request.META
        auth_header = meta.get('HTTP_AUTHORIZATION')
        # Move to next authentication scheme if any required header is missing
        if not auth_header or not auth_header.startswith('CS '):
            request.body = decode_payload(request)
            return None

        if not settings.INTEGRATION_PUBLIC_KEY or not settings.INTEGRATION_PRIVATE_KEY:
            logger.error(
                'API credentials could not be loaded for validation'
            )
            raise exceptions.AuthenticationFailed(
                'API credentials could not be loaded for validation'
            )

        full_uri = request.build_absolute_uri()
        payload = request.body
        try:
            validate_hmac_message(auth_header,
                                  full_uri,
                                  request.method,
                                  settings.INTEGRATION_PRIVATE_KEY,
                                  payload)
            request.body = decode_payload(request)
        except HmacValidationException as hve:
            logger.error('Authentication failed: %s', hve.args[0])
            raise exceptions.AuthenticationFailed(hve.args[0])

        return _maybe_create_user(settings.HMAC_USER), {
            'auth_method': 'CS HMAC'
        }
