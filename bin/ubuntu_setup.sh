#!/usr/bin/env bash
echo '
########################################################################
 Installs necessary or helpful package on a fresh ubuntu system
 to be used for ODMF
########################################################################
'
# Remember every command ever typed
if [ "$HISTSIZE" != "INF" ]
then
  echo '
  #
  # Set infinite history
  export HISTSIZE="INF"
  export HISTFILESIZE="INF"
  export HISTTIMEFORMAT="%d/%m/%y %T "
  ' >> ~/.bashrc
fi

PYTHON_VER=3.8

sudo apt update
sudo apt -y upgrade
echo '-------------------------------------------'
echo 'Install build tools and necessary libraries'
echo '-------------------------------------------'
sudo apt -y install build-essential
sudo apt -y install cmake pandoc htop
sudo apt -y install git curl docker docker.io
sudo apt -y install libgdal-dev libnetcdf-dev libhdf-dev
sudo apt -y install openmpi-bin openmpi-common \
                    openssh-client openssh-server \
                    libopenmpi-dbg libopenmpi-devsudo


# install apache2
sudo apt -y install apache2
sudo apt -y install libapache2-mod-wsgi-py3
sudo apt-get install software-properties-common
sudo add-apt-repository universe
sudo add-apt-repository ppa:certbot/certbot
sudo apt update
sudo apt -y install certbot python-certbot-apache

sudo apt -y install postgresql pgcli

sudo apt -y install chrony
# install Remote-Desktop Connection
# sudo apt -y install xrdp

# install software to mount Windows shared folders
sudo apt -y install cifs-utils


echo '-------------------------------------------'
echo 'Complete the system python'
echo '-------------------------------------------'
sudo apt -y install python3-distutils python3-dev python3-venv python3-tk python3-wheel python3-pip

if ! command -v python$PYTHON_VER
then
  echo '-------------------------------------------'
  echo "Install python $PYTHON_VER"
  echo '-------------------------------------------'
  sudo apt update
  sudo apt -y install python$PYTHON_VER python${PYTHON_VER}-dev \
                      python${PYTHON_VER}-distutils python${PYTHON_VER}-venv \
                      python${PYTHON_VER}-tk
  sudo python$PYTHON_VER -m pip install wheel
fi

PYTHON_VER=3.8
if [ ! -f ~/.bash_aliases ]; then
  echo "
  export PYTHON_VERSION=$PYTHON_VER
  alias makevenv=python\$PYTHON_VERSION -m venv venv
  alias venv='source venv/bin/activate'
  " > ~/.bash_aliases
fi

echo "Create samba directory"
sudo apt install -y samba
echo '# Change the homes share in /etc/samba/smb.conf
[homes]
   comment = Home Directories
   browseable = no
   read only = no
   create mask = 0775
   directory mask = 2775
;   valid users = %S
'
sudo smbpasswd -a $USER

echo 'Configure Apache'

sudo addgroup webmasters
sudo adduser $USER webmasters
sudo chgrp -R /var/www
sudo chmod -R g+rwx /var/www
