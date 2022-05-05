#!/usr/bin/env bash
# Exit when any command fails
set -e

# Set up default parameters
om_develop=""
om_deps=""
om_prefix=""

# Check that the script is run from the right directory
if [ ! -f "./setup.py" ]
then
  echo "ERROR: Please run this script from the root folder of OM's repository:"
  echo "Exiting...."
  exit 1
fi  

# Parse CLI arguments
function print_usage() {
  echo "Usage: sh tools/scripts/install.sh <arguments>        Install OM"      
  echo "   Or: source tools/scripts/install.sh <arguments>    Install OM"      
  echo ""
  echo "Arguments:"
  echo "   -p <path>  installation path (defaults to the path when python is installed) "      
  echo "   -e         perform an editable (develop) installation"      
  echo "   -n         install only OM, no dependecies"      
  echo "   -h         print this help"      
}

while getopts ":p:enh" opt; do
  case $opt in
    p)
      om_prefix="$OPTARG"
      ;;
    e)
      om_develop="--editable"
      ;;
    n)
      om_deps="--no-deps"
      ;;
    h)
      print_usage
      exit 0
      ;;
    \?)
      echo "Invalid option -$OPTARG" >&2
      print_usage
      exit 1
      ;;
  esac
done

om_python_version=$(python -V 2>&1 | grep -Po '(?<=Python )(.+)')
om_pyver=${om_python_version:0:3}

# Create sitecustomize.py file if needed
if [ "${om_prefix}" != "" ]
then
  echo "Installing OM at ${om_prefix}"
  mkdir -p ${om_prefix}
  if [ "${om_develop}" == "--editable" ]
  then
     echo "Editable installation detected"
     echo "Creating sitecustomize.py file at ${om_prefix}/lib/python${om_pyver}/site-packages/sitecustomize.py"
     mkdir -p ${om_prefix}/lib/python${om_pyver}/site-packages
     cat << EOF > ${om_prefix}/lib/python${om_pyver}/site-packages/sitecustomize.py
import site

site.addsitedir('${om_prefix}/lib/python${om_pyver}/site-packages')
EOF
  fi
else
  echo "Installing OM"
fi

# Perform the installation
if [ "${om_prefix}" == "" ]
then
  prefix_opt=""
else
  prefix_opt="--prefix=${om_prefix}"
fi

if [ "${om_develop}" == "--editable" ]
then
  echo "Running: 'python setup.py develop ${om_deps} ${prefix_opt}'"
  PYTHONPATH=${om_prefix}/lib/python${om_pyver}/site-packages:$PYTHONPATH python setup.py develop ${om_deps} ${prefix_opt}
else
  echo "Running: 'pip install ${om_deps} ${prefix_opt} .'"
  pip install ${om_deps} ${prefix_opt} .
fi

# Create activation file
if [ "${om_prefix}" != "" ]
then
  echo "Creating activation script at ${om_prefix}/bin/activate-om"
  cat << EOF > ${om_prefix}/bin/activate-om
echo "Activating OM installation at ${om_prefix}"
export PATH=${om_prefix}/bin:\$PATH
export PYTHONPATH=${om_prefix}/lib/python${om_pyver}/site-packages:\$PYTHONPATH
export PYTHONPATH=${om_prefix}/lib64/python${om_pyver}/site-packages:\$PYTHONPATH
EOF
fi

# Do not exit if any command fails
set +e
