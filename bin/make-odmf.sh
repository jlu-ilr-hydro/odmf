#!/usr/bin/env bash

if [ -n "$1" ]; then
  NAME="$1"
  USERNAME="odmf-$NAME"
  OPATH="/srv/odmf/$NAME"

else
  echo "You need to provide a database name\nUsage: make-odmf.sh NAME [odmf-target]" 1>&2
  exit 1
fi

echo "Add a new user $USERNAME"
adduser --system  --gecos "ODMF/$NAME Service" --disabled-password --group --home $OPATH odmf-$NAME

echo "Create and activate virtual environment"
python3 -m venv venv
source $OPATH/venv/bin/activate
pip install pip wheel --upgrade

echo "Install odmf"
pip install $2

_ODMF_COMPLETE=source_bash odmf > $OPATH/venv/bin/odmf-complete.sh
chmod u+x g+x $OPATH/venv/bin/odmf-complete.sh
echo "source odmf-complete.sh" >> $OPATH/venv/bin/activate



echo "Change ownership of files to $USERNAME"
chown -R $USERNAME:$USERNAME .
chmod g+w -R .

echo "Add your own user to the group of this service to act as an admin with this command:"
echo "sudo adduser USER $USERNAME"
