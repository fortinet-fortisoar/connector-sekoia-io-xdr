""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """

class Result(object):
    def __init__(self):
        self._status = 'Success'
        self._message = ''
        self._operation = None
        self._binary = False
        self._data = []
        self._env = {}
        return

    def get_operation(self):
        return self._operation

    def set_operation(self, operation):
        self._operation = operation
        return self._operation

    def get_status(self):
        return self._status

    def set_status(self, status):
        self._status = status

    def get_message(self):
        return self._message

    def set_message(self, message):
        self._message = message

    def get_data(self):
        return self._data

    def get_binary(self):
        return self._binary

    def set_data(self, item, is_binary=False):
        self._data = item
        self._binary = is_binary
        return item

    def get_env(self):
        return self._env

    def set_env(self, env):
        self._env = env
        return env

    def _fetch_exception_message(self, exception):
        message = None
        try:
            return exception.message
        except Exception:
            pass
        if hasattr(exception, 'message'):
            message = exception['message']
        if message:
            try:
                return str(message)
            except:
                pass
        try:
            message = str(exception)
        except:
            message = ''
        return message

    def set_result(self, status, message='', exception=None):
        if type(status) == str:
            self._status = status
        else:
            self._status = 'Success' if bool(status) else 'Failed'
        self._message = message
        if exception:
            self._message += self._fetch_exception_message(exception)

    def get_result(self):
        if self._binary and self.get_status() != 'Failed':
            return self.get_data()
        result = {'operation': self.get_operation(),
                  'status': self.get_status(),
                  'message': self.get_message(),
                  'data': self.get_data(),
                  'env': self.get_env()
                  }
        if result.get('status') == 'Failed':
            raise Exception(result.get('message'))
        return result
