""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import logging

from subprocess import check_output
from connectors.core.base_connector import *
from connectors.core.result import *
from connectors.core.constants import *
from connectors.core.utils import *


def get_logger(name=None):
    if name:
        logger = logging.getLogger('connectors.%s' % name)
    else:
        logger = logging.getLogger('connectors')
    return logger

logger = get_logger()


class SDKVersion:
    def __init__(self):
        self.version = None
        try:
            pkg_detail = check_output('rpm -qa| grep cyops-integrations', shell=True).decode('utf-8')
            logger.debug('pkg details: %s' % pkg_detail)
            self.version = pkg_detail.split('-')[2]
        except Exception as e:
            self.version = "dev"

SDK_VERSION = SDKVersion().version
