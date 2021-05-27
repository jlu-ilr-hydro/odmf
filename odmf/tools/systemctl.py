import sys
from pathlib import Path
from textwrap import dedent
from ..config import conf

bin_path = Path(sys.executable).parent
cwd = Path.cwd()


class sudoers:

    cmd = f"""cat {conf.user}.sudo | (sudo su -c 'EDITOR="tee -a" visudo -f /etc/sudoers.d/{conf.user}')""".strip()

    content = dedent(f"""
        # This file allows all members of the user group {conf.user} to start, stop and restart the web application service 
        #
        # Install this file with visudo: 
        # {cmd} 
        
        %{conf.user} ALL= NOPASSWD: /bin/systemctl start {conf.user}.service
        %{conf.user} ALL= NOPASSWD: /bin/systemctl stop {conf.user}.service
        %{conf.user} ALL= NOPASSWD: /bin/systemctl restart {conf.user}.service
    """)

    file = cwd / (conf.user + '.sudo')


class unit:

    content = dedent(f"""
        [Unit]
        Description={conf.description}
        After=network.target
        
        [Service]
        User={conf.user}
        WorkingDirectory={conf.home}
        ExecStart={bin_path}/odmf start
        UMask=0002
        Restart=always
        
        [Install]
        WantedBy=multi-user.target
    """)

    help = dedent(f"""
        Created files: 
            - {conf.user}.service
            - {conf.user}.sudo
        
        For Debian-like systems do:
            adduser --system  --gecos "ODMF/$NAME Service" --disabled-password --group --home {cwd} {conf.user}
        
        Add your own user to the group of this service to act as an admin with this command:
            sudo adduser USER {conf.user}
            sudo cp {conf.user}.service /etc/systemd/system
            sudo systemctl enable {conf.user}.service
            sudo systemctl start {conf.user}.service
        
        If all members of {conf.user} should be able to start and stop the service, without sudo rights, 
        configure your sudoers with the following command, which installs the {conf.user}.sudo file in
        /etc/sudoers.d in a safe way:
        
            {sudoers.cmd}
        
    """)

    file = cwd / (conf.user + '.service')




def make_service():

    unit.file.write_text(unit.content)
    sudoers.file.write_text(sudoers.content)
    return unit.help
