#!/usr/bin/env bash
# Build build/lambda.zip for the AWS Lambda function.
#
# The ZIP holds src/*.py and the tzdata package at its root, so the Lambda
# handler setting lambda_function.lambda_handler finds lambda_function.py.
# Run it from anywhere with the project's virtual environment active:
#   bash scripts/build_lambda_zip.sh
set -o errexit -o nounset -o pipefail

# Work from the project root, wherever the script is called from.
cd "$(dirname "$0")/.."

build_dir=build/lambda
zip_file=build/lambda.zip

# Start clean, so files from an earlier build never end up in the ZIP.
rm --recursive --force "$build_dir" "$zip_file"
mkdir --parents "$build_dir"

cp src/*.py "$build_dir/"
python -m pip install tzdata --target "$build_dir" --no-compile --quiet

# Each top-level file and folder is stored under its own name, at the ZIP root.
python -m zipfile --create "$zip_file" "$build_dir"/*

# Show the .py files at the ZIP root; lambda_function.py must be among them.
# (grep reads the whole list; head would close the pipe early, and with
# pipefail the resulting broken pipe could make the script fail.)
echo "Built $zip_file with these files at its root:"
python -m zipfile --list "$zip_file" | grep --extended-regexp '^[a-z_]+\.py '
