from __future__ import unicode_literals

from picklefield.constants import DEFAULT_PROTOCOL
from picklefield.fields import PickledObjectField

import django.utils.version

__all__ = 'VERSION', '__version__', 'DEFAULT_PROTOCOL', 'PickledObjectField'

VERSION = (2, 0, 0, 'alpha', 0)

__version__ = django.utils.version.get_version(VERSION)
