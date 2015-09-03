import django
from django.db import models
from django.utils import six

# python 3.x does not have cPickle module
try:
    from cPickle import loads, dumps # cpython 2.x
except ImportError:
    from pickle import loads, dumps # cpython 3.x, other interpreters

if django.VERSION >= (1, 8):
    _PickledObjectField = models.Field
else:
    _PickledObjectField = six.with_metaclass(models.SubfieldBase, models.Field)
