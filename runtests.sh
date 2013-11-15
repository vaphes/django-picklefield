#!/bin/sh
ln -s src/picklefield .
DJANGO_SETTINGS_MODULE=test_settings django-admin test --pythonpath `pwd` --settings test_settings picklefield
rm -f picklefield
