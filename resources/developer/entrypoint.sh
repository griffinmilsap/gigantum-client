#!/bin/bash

# BVB - Required to get rq to run.
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# TODO: Generalize Dev Env Vars
export JUPYTER_RUNTIME_DIR=/mnt/share/jupyter/runtime

# Open up the docker socket for now
chmod 777 /var/run/docker.sock

# Add local user
# Either use the LOCAL_USER_ID if passed in at runtime or fallback
USER_ID=${LOCAL_USER_ID:-9001}

echo "Starting with UID: $USER_ID"
useradd --shell /bin/bash -u $USER_ID -o -c "" -m giguser
export HOME=/home/giguser

# Set permissions for container-container share
chown -R giguser:root /mnt/share/

# Set permissions for demo project
chown giguser:root /opt/my-first-project.zip

# Setup git config for giguser
gosu giguser bash -c "git config --global user.email 'noreply@gigantum.io'"
gosu giguser bash -c "git config --global user.name 'Gigantum AutoCommit'"
gosu giguser bash -c "git config --global credential.helper store"

# Setup everything to allow giguser to run nginx and git
chown -R giguser:root /opt/log
chown -R giguser:root /opt/nginx
chown -R giguser:root /opt/redis
chown -R giguser:root /opt/run
chown -R giguser:root /var/lib/nginx/
chown -R giguser:root /var/log/nginx/
chown --silent giguser:root /var/lock/nginx.lock
chown giguser:root /run/nginx.pid
chmod ugo+x /opt/setup.sh

if [ -n "$SET_PERMISSIONS" ]; then
    # This is a *nix config running shell dev so you need to setup perms on the mounted code (skipping node packages)
   cd $SET_PERMISSIONS
   chown giguser:root -R gtmapi
   chown giguser:root -R gtmcore
fi

# Setup LFS
gosu giguser git lfs install

# Setup custom CA certs if provided by the user
CERT_COUNT=`ls -1 /mnt/gigantum/certificates/*.crt 2>/dev/null | wc -l`
if [[ ${CERT_COUNT} != 0 ]];then
  echo "Configuring user provided CA certificates"
  cp /mnt/gigantum/certificates/*.crt /usr/local/share/ca-certificates/
  update-ca-certificates
  export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
  export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
else
  echo "No user provided CA certificates found. Skipping CA update."
fi

# Start supervisord
gosu giguser /usr/bin/supervisord &
exec gosu giguser "$@"
