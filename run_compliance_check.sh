#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/aegis-core
python test_compliance.py
