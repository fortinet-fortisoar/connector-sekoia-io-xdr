""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict, namedtuple


class ConnectorPageNumberPagination(PageNumberPagination):

    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('status', 'Success'),
            ('totalItems', self.page.paginator.count),
            ('itemsPerPage', self.get_page_size(self.request)),
            ('nextPage', self.get_next_page()),
            ('previousPage', self.get_previous_page()),
            ('data', data)
        ]))

    def get_next_page(self):
        try:
            return self.page.next_page_number()
        except:
            pass
        return None

    def get_previous_page(self):
        try:
            return self.page.previous_page_number()
        except:
            pass
        return None
