# Exit when any command fails
set -e

# Set up default parameters
om_develop=""
om_deps=""
om_prefix=`pwd`/install

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
  echo "   -p <path>  installation path (defaults to <om_root>/install) "      
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

# Start installation
echo "Installing OM at ${om_prefix}"

# Create sitecustomize.py file if needed
mkdir -p ${om_prefix}
om_python_version=$(python -V 2>&1 | grep -Po '(?<=Python )(.+)')
om_pyver=${om_python_version:0:3}
if [ "${om_develop}" == "--editable" ]
then
  mkdir -p ${om_prefix}/lib/python${om_pyver}/site-packages
  echo "Editable installation detected"
  echo "Creating sitecustomize.py file at ${om_prefix}/lib/python${om_pyver}/site-packages/sitecustomize.py"
cat << EOF > ${om_prefix}/lib/python${om_pyver}/site-packages/sitecustomize.py
import site

site.addsitedir('${om_prefix}/lib/python${om_pyver}/site-packages')
EOF
fi

# Perform the installation

if [ "${om_develop}" == "--editable" ]
then
  echo "Running: 'python setup.py develop ${om_deps} --prefix=${om_prefix}'"
  PYTHONPATH=${om_prefix}/lib/python${om_pyver}/site-packages:$PYTHONPATH python setup.py develop ${om_deps} --prefix=${om_prefix}
else
  echo "Running: 'pip install ${om_deps} --prefix=${om_prefix} .'"
  pip install ${om_deps} --prefix=${om_prefix} .
fi

# Create activation file
echo "Creating activation script at ${om_prefix}/bin/activate"
cat << EOF > ${om_prefix}/bin/activate
echo "Activating OM installation at ${om_prefix}"
export PATH=${om_prefix}/bin:\$PATH
export PYTHONPATH=${om_prefix}/lib/python${om_pyver}/site-packages:\$PYTHONPATH
export PYTHONPATH=${om_prefix}/lib64/python${om_pyver}/site-packages:\$PYTHONPATH
EOF

# Do not exit if any command fails
set +e
