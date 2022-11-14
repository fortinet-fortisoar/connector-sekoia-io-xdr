""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """

import requests
import logging

logger = logging.getLogger('connectors')


def make_request(url, method, body=None, *args, **kwargs):
    return None


def make_file_upload_request(file_name, file_content, file_type, *args, **kwargs):
    return None


def maybe_json_or_raise(response):
    """
    Helper function for processing request responses

    Returns any json found in the response. Otherwise, it will extract the
    response as text, or, failing that, as bytes.

    :return: the response from the request
    :rtype: dict or str or bytes
    :raises: :class:`requests.HTTPError` if status code was 4xx or 5xx
    """
    if response.ok:
        try:
            logger.info('Processing request responses.')
            return response.json(strict=False)
        except Exception:
            return response.text or response.content
    else:
        msg = ''
        try:
            msg = response.json()
            logger.warn(msg)
        except Exception:
            pass
        if not msg:
            msg = response.text
            logger.warn(msg)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # add any response content to the error message
            msg = '{} :: {} :: Url: {}'.format(str(e), msg, response.url)
            logger.error(msg)
            raise requests.exceptions.HTTPError(msg, response=response)
