#! /bin/bash
set -e
cd docs
make html
cd ..
doctr deploy .
  
