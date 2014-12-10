#! /bin/bash
set -e

export suite=${*:-}

coverage erase
coverage run $(which nosetests) --pdb --pdb-failures -sv ${suite}
coverage report -m --include="*ssws*" 
