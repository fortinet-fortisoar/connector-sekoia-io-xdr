""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
# environment.py

import ast
import json
import re
import logging
from django.template import engines

logger = logging.getLogger('connectors')


def expand(env, obj, workflow=None):
    """
    Expands an object using dynamic variables specified in the given environment

   :param dict env: The environment containing available dynamic variables
   :param Any obj: The object to expand

   :return: The expanded object
   :rtype: Any
    """
    if not env:
        return obj
    return _expand(env, obj, workflow)


def _expand(env, obj, workflow=None):
    """
    Expands an object using dynamic variables specified in the given environment

   :param dict env: The environment containing avaiable dynamic variables
   :param Any obj: The object to expand

   :return: The expanded object
   :rtype: Any
    """
    obj_type = type(obj).__name__
    if obj_type == 'dict':
        ret = {}
        for key, value in obj.items():
            ret[key] = _expand(env, value)
        return ret
    elif obj_type == 'list':
        return [_expand(env, list_item) for list_item in obj]
    elif obj_type == 'str':
        return _expand_string(env, obj, workflow)

    return obj


jinja2 = engines['jinja2']


def _expand_string(env, string, workflow=None):
    """
    Expands the string using jinja, with env as the context object.

   :param dict env: The environment containing available dynamic variables
   :param str string: The string to expand via jinja

   :return: The templated string
   :rtype: Any
    """
    env['request'] = env.get('request', {})
    context = {
        'vars': env,
        'request': env.get('request'),
        'files': env.get('files', {}),
    }

    if 'self_id' in string:
        string = string.replace('self_id', 'vars.self_id')

    if 'dest_id' in string:
        string = string.replace('dest_id', 'vars.dest_id')

    template = jinja2.from_string(string)
    ret = template.render(context=context)
    try:
        ret = json.loads(ret, strict=False)
        return ret
    except Exception:
        pass
    try:
        ret = ast.literal_eval(ret)
        return ret
    except (SyntaxError, ValueError):
        pass

    return ret


def _eval_args(string):
    tmp = (string.replace(' ', '').replace('{{', '').replace('}}', '').split('|')[0]). \
        replace('[', '.').replace(']', '.').replace('..', '.').split('.')
    arg1 = tmp[1]
    arg2 = None
    if len(tmp) > 2:
        arg2 = tmp[2]
    try:
        arg1 = json.loads(arg1)
    except:
        pass
    try:
        arg2 = json.loads(arg2)
    except:
        pass
    return arg1, arg2
