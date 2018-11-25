from __future__ import unicode_literals

from base64 import b64decode, b64encode
from copy import deepcopy
from zlib import compress, decompress

import django
from django.db import models
from django.utils.encoding import force_text

from .constants import DEFAULT_PROTOCOL

try:
    from cPickle import loads, dumps
except ImportError:
    from pickle import loads, dumps


class PickledObject(str):
    """
    A subclass of string so it can be told whether a string is a pickled
    object or not (if the object is an instance of this class then it must
    [well, should] be a pickled one).

    Only really useful for passing pre-encoded values to ``default``
    with ``dbsafe_encode``, not that doing so is necessary. If you
    remove PickledObject and its references, you won't be able to pass
    in pre-encoded values anymore, but you can always just pass in the
    python objects themselves.
    """


class _ObjectWrapper(object):
    """
    A class used to wrap object that have properties that may clash with the
    ORM internals.

    For example, objects with the `prepare_database_save` property such as
    `django.db.Model` subclasses won't work under certain conditions and the
    same apply for trying to retrieve any `callable` object.
    """
    __slots__ = ('_obj',)

    def __init__(self, obj):
        self._obj = obj


def wrap_conflictual_object(obj):
    if hasattr(obj, 'prepare_database_save') or callable(obj):
        obj = _ObjectWrapper(obj)
    return obj


def dbsafe_encode(value, compress_object=False, pickle_protocol=DEFAULT_PROTOCOL, copy=True):
    # We use deepcopy() here to avoid a problem with cPickle, where dumps
    # can generate different character streams for same lookup value if
    # they are referenced differently.
    # The reason this is important is because we do all of our lookups as
    # simple string matches, thus the character streams must be the same
    # for the lookups to work properly. See tests.py for more information.
    if copy:
        # Copy can be very expensive if users aren't going to perform lookups
        # on the value anyway.
        value = deepcopy(value)
    value = dumps(value, protocol=pickle_protocol)
    if compress_object:
        value = compress(value)
    value = b64encode(value).decode()  # decode bytes to str
    return PickledObject(value)


def dbsafe_decode(value, compress_object=False):
    value = value.encode()  # encode str to bytes
    value = b64decode(value)
    if compress_object:
        value = decompress(value)
    return loads(value)


class PickledObjectField(models.Field):
    """
    A field that will accept *any* python object and store it in the
    database. PickledObjectField will optionally compress its values if
    declared with the keyword argument ``compress=True``.

    Does not actually encode and compress ``None`` objects (although you
    can still do lookups using None). This way, it is still possible to
    use the ``isnull`` lookup type correctly.
    """

    def __init__(self, *args, **kwargs):
        self.compress = kwargs.pop('compress', False)
        self.protocol = kwargs.pop('protocol', DEFAULT_PROTOCOL)
        self.copy = kwargs.pop('copy', True)
        kwargs.setdefault('editable', False)
        super(PickledObjectField, self).__init__(*args, **kwargs)

    def get_default(self):
        """
        Returns the default value for this field.

        The default implementation on models.Field calls force_unicode
        on the default, which means you can't set arbitrary Python
        objects as the default. To fix this, we just return the value
        without calling force_unicode on it. Note that if you set a
        callable as a default, the field will still call it. It will
        *not* try to pickle and encode it.

        """
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default
        # If the field doesn't have a default, then we punt to models.Field.
        return super(PickledObjectField, self).get_default()

    def to_python(self, value):
        """
        B64decode and unpickle the object, optionally decompressing it.

        If an error is raised in de-pickling and we're sure the value is
        a definite pickle, the error is allowed to propagate. If we
        aren't sure if the value is a pickle or not, then we catch the
        error and return the original value instead.

        """
        if value is not None:
            try:
                value = dbsafe_decode(value, self.compress)
            except:
                # If the value is a definite pickle; and an error is raised in
                # de-pickling it should be allowed to propogate.
                if isinstance(value, PickledObject):
                    raise
            else:
                if isinstance(value, _ObjectWrapper):
                    return value._obj
        return value

    def pre_save(self, model_instance, add):
        value = super(PickledObjectField, self).pre_save(model_instance, add)
        return wrap_conflictual_object(value)

    if django.VERSION < (2, 0):
        def from_db_value(self, value, expression, connection, context):
            return self.to_python(value)
    else:
        def from_db_value(self, value, expression, connection):
            return self.to_python(value)

    def get_db_prep_value(self, value, connection=None, prepared=False):
        """
        Pickle and b64encode the object, optionally compressing it.

        The pickling protocol is specified explicitly (by default 2),
        rather than as -1 or HIGHEST_PROTOCOL, because we don't want the
        protocol to change over time. If it did, ``exact`` and ``in``
        lookups would likely fail, since pickle would now be generating
        a different string.

        """
        if value is not None and not isinstance(value, PickledObject):
            # We call force_text here explicitly, so that the encoded string
            # isn't rejected by the postgresql_psycopg2 backend. Alternatively,
            # we could have just registered PickledObject with the psycopg
            # marshaller (telling it to store it like it would a string), but
            # since both of these methods result in the same value being stored,
            # doing things this way is much easier.
            value = force_text(dbsafe_encode(value, self.compress, self.protocol, self.copy))
        return value

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_db_prep_value(value)

    def get_internal_type(self):
        return 'TextField'

    def get_lookup(self, lookup_name):
        """
        We need to limit the lookup types.
        """
        if lookup_name not in ['exact', 'in', 'isnull']:
            raise TypeError('Lookup type %s is not supported.' % lookup_name)
        return super(PickledObjectField, self).get_lookup(lookup_name)