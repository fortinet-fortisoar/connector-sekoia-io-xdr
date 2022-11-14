""" Copyright start
  Copyright (C) 2008 - 2021 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from threading import Thread


def threaded(func):
    def wrapper(agent_id, *args, **kwargs):
        t = Thread(target=func, args=(agent_id, ))
        t.start()

    return wrapper
