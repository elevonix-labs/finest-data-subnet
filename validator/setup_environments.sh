#!/bin/bash

cd validator/fetch_commit
poetry install
cd ..

cd process_commit
poetry install
cd ..

echo "Environments set up successfully."