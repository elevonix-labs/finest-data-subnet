#!/bin/bash

poetry install

cd fetch_commit
poetry install
cd ..

cd process_commit
poetry install
pip install flash-attn==2.7.3
poetry run pip install flash-attn==2.7.3
cd ..

echo "Environments set up successfully."