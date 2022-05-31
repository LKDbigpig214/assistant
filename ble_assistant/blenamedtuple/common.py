from collections import namedtuple

FrameTuple = namedtuple('frame', ['header',
                                  'data_len',
                                  'payload',
                                  'checksum',
                                  'length',
                                  'raw_data'])

ErrorCodeTuple = namedtuple('error_code', ['code',
                                           'status'])
