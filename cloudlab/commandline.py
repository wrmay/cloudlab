import argparse
import os
import pkg_resources
import sys

def run():
    os.makedirs('aws_basic')
    pkg_resources.set_extraction_path('aws_basic')
    filename = pkg_resources.resource_filename('cloudlab','plans/aws_basic')
    print("OK " + filename)
