from __future__ import unicode_literals

from picklefield.constants import DEFAULT_PROTOCOL
from picklefield.fields import PickledObjectField

import django.utils.version

__all__ = 'VERSION', '__version__', 'DEFAULT_PROTOCOL', 'PickledObjectField'

VERSION = (1, 1, 0, 'final', 0)

__version__ = django.utils.version.get_version(VERSION)
