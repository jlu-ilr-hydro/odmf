#!/usr/bin/env bash
set -e
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root" 1>&2
  echo "Usage: make-odmf.sh NAME [odmf-source]" 1>&2
  exit
fi

if [ -z "$1" ]; then
  echo "You need to provide a database name" 1>&2
  echo "Usage: make-odmf.sh NAME [odmf-source]" 1>&2
  exit 1
fi


NAME="$1"
OPATH="/srv/odmf/$NAME"

if [ -z "$2" ]; then
  echo "ODMF will be downloaded from https://github.com/jlu-ilr-hydro/odmf"
  ODMF_SRC='git+https://github.com/jlu-ilr-hydro/odmf'
else
  ODMF_SRC="$2"
fi

echo "Create and activate virtual environment"
python3 -m venv venv
source $OPATH/venv/bin/activate
pip install pip wheel --upgrade

echo "Install odmf from $ODMF_SRC"
pip install $ODMF_SRC
_ODMF_COMPLETE=source_bash odmf > $OPATH/venv/bin/odmf-complete.sh
chmod u+x g+x $OPATH/venv/bin/odmf-complete.sh
echo "source odmf-complete.sh" >> $OPATH/venv/bin/activate

echo "Create data directories"
mkdir sessions
mkdir -p preferences/plots
mkdir datafiles

