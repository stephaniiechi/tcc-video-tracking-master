import os
from distutils.core import setup, Extension

os.chdir(os.path.dirname(__file__))

module_device = Extension('video_device_listing',
                          sources=[
                              'source.cpp']
                          )

setup(name='video-device-listing',
      version='1.0',
      description='Get device list with DirectShow',
      ext_modules=[module_device])
