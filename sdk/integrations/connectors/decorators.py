""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from rest_framework.response import Response
from threading import Thread
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.conf import settings


def json_response(func):
    """
    A simple decorator that takes a view response and turns it
    into json.

    """

    def wrapper(request, *args, **kwargs):
        response = func(request, *args, **kwargs)
        if isinstance(response, Response):
            return response
        if isinstance(response, dict):
            return Response(response, status=response.get('status'))
        if isinstance(response, list):
            return Response(response)
        elif isinstance(response, int):
            return Response(status=response)
        else:
            return response

    return wrapper


def run_async(func):
    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target=func, args=args, kwargs=kwargs)
        func_hl.start()
        return func_hl

    return async_func


def threaded(func):
    def wrapper(*args, **kwargs):
        future = settings.THREAD_POOL_EXECUTOR.submit(func, *args, **kwargs)
    return wrapper
