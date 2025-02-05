#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######  

from model.configurations.tabs.general.network import Network as NetworkModel

import json

class Network():

   _configuration = {}
   
   def __init__(self):

      self.model = NetworkModel()
      self._configuration = self.model.get()


   @property
   def configuration(self):
      return {key: value for key, value in self._configuration[0].__dict__.items() if not key.startswith("_") and not key.startswith("__") and not key.startswith("db")}

   # a setter function
   @configuration.setter
   def configuration(self, configuration):
      self.model.update(configuration)

      
