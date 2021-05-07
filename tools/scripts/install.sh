# exit when any command fails
set -e

# Set up default parameters
om_develop=""
om_deps=""
om_prefix=`pwd`/install

if [ ! -f "./setup.py" ]
then
  echo "ERROR: Please run this script from the root folder of OM's repository:"
  echo "Exiting...."
  exit 1
fi  


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

# Parse CLI arguments
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

echo "Installing OM at "${om_prefix}

# Create sitecustomize.py file if needed
mkdir -p ${om_prefix}
om_python_version=$(python -V 2>&1 | grep -Po '(?<=Python )(.+)')
om_pyver=${om_python_version:0:3}
if [ "${om_develop}" == "--editable" ]
then
  mkdir -p ${om_prefix}/lib/python${om_pyver}/site-packages
  echo "Editable installation detected"
  echo "Creating sitecustomize.py file in '${om_prefix}/lib/python${om_pyver}/site-packages/'"
cat << EOF > ${om_prefix}/lib/python${om_pyver}/site-packages/sitecustomize.py
import site

site.addsitedir('${om_prefix}/lib/python${om_pyver}/site-packages')
EOF
fi

echo "Running: 'pip install ${om_develop} ${om_deps} --prefix=${om_prefix} .'"

set +e
