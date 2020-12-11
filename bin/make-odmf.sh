
#!/usr/bin/env bash

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
USERNAME="odmf-$NAME"
PYTHON=python3.8
OPATH="/srv/odmf/$NAME"

if [ -z "$2" ]; then
  echo "ODMF will be downloaded from https://github.com/jlu-ilr-hydro/odmf"
  ODMF_SRC='git+https://github.com/jlu-ilr-hydro/odmf'
else
  ODMF_SRC="$2"
fi

echo "Create and activate virtual environment"
$PYTHON --version
$PYTHON -m venv $OPATH/venv
source $OPATH/venv/bin/activate
which python
which pip
python -VV

pip install pip wheel --upgrade

echo "Install odmf from $ODMF_SRC"
pip install $ODMF_SRC
_ODMF_COMPLETE=source_bash odmf > $OPATH/venv/bin/odmf-complete.sh
chmod ug+x $OPATH/venv/bin/odmf-complete.sh
echo "source odmf-complete.sh" >> $OPATH/venv/bin/activate

echo "Create data directories"
mkdir $OPATH/sessions
mkdir -p $OPATH/preferences/plots
mkdir $OPATH/datafiles

echo "Add a new user $USERNAME"
adduser --system  --gecos "ODMF/$NAME Service" --disabled-password --group --home $OPATH odmf-$NAME

chown $USERNAME:$USERNAME -R $OPATH
chmod ug+rw -R $OPATH

echo "#!/usr/bin/env bash
pip install $ODMF_SRC --upgrade
sudo systemctl restart $USERNAME.service
" > upgrade.sh
chmod ug+rwx upgrade.sh

echo "Add me ($SUDO_USER) to the group of $USERNAME"
adduser $SUDO_USER $USERNAME"

