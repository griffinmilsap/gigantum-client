# FRONTEND BUILD CONTAINER
FROM ubuntu:18.04 as ui-builder

# Install system level dependencies
RUN apt-get -y update && apt-get -y install git curl gosu

# Install Node
RUN curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    apt-get -y install nodejs

# Install Yarn
RUN npm install yarn -g

# Install babel-node
RUN npm install -g @babel/cli@7.2.3 @babel/core@7.2.2 jest@24.0.0 relay-compiler@1.6.1

# Make build location dir
RUN mkdir /opt/ui

# Set the react port to match nginx
ENV PORT "10001"

# Copy source to build
ARG UI_BUILD_SCRIPT=resources/docker/ui_build_script.sh

COPY ui /opt/ui
COPY $UI_BUILD_SCRIPT /opt/ui_build_script.sh
RUN /bin/bash /opt/ui_build_script.sh





# PRODUCTION CONTAINER
FROM ubuntu:18.04
LABEL maintainer="Gigantum <support@gigantum.com>"

# Copy requirements files
COPY packages/gtmcore/requirements.txt /opt/gtmcore/requirements.txt
COPY packages/gtmapi/requirements.txt /opt/gtmapi/requirements.txt
COPY packages/confhttpproxy /opt/confhttpproxy
ENV SHELL=/bin/bash \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8


# Arguments, defaulted to production values
ARG CLIENT_CONFIG_FILE=build/client/labmanager-config.yaml
ARG NGINX_UI_CONFIG=resources/client/nginx_ui.conf
ARG NGINX_API_CONFIG=resources/client/nginx_api.conf
ARG SUPERVISOR_CONFIG=build/client/supervisord.conf
ARG ENTRYPOINT_FILE=resources/client/entrypoint-local.sh
ARG REDIS_CONFIG=resources/client/redis.conf
ARG HONEYTAIL_INSTALLER=resources/client/honeytail-installer-local.sh

COPY $HONEYTAIL_INSTALLER /tmp/honeytail.sh

# Super instruction to install all dependencies that need apt and clean up to minimize layer size
RUN apt-get -y update && \
    # Install all apt packages
    apt-get -y --no-install-recommends install nginx supervisor wget openssl python3.7 python3-pip python3-distutils \
    gcc g++ gosu redis-server libjpeg-dev python3-setuptools python3.7-dev libdpkg-perl zip unzip libsnappy-dev \
    curl make autoconf dh-autoreconf libcurl4-openssl-dev libexpat1-dev libz-dev && \
    # Make sure correct Python version is used
    # DP NOTE: pip will use whatever version python3 points to
    ln -sf python3.7 /usr/bin/python3 && \
    ln -sf python3.7-config /usr/bin/python3-config && \
    ln -sf python3.7m /usr/bin/python3m && \
    ln -sf python3.7m-config /usr/bin/python3m-config && \
    # Install Git from source to use OpenSSL for better enterprise network support.
    mkdir /tmp/gitbuild && cd /tmp/gitbuild && \
    # Get the latest git tarball
    git_tarball_url="https://www.github.com$(curl 'https://github.com/git/git/tags' | grep -o "/git/git/archive/v2\..*\.tar\.gz" | sort -r | head -1 | tr -d '\n')" && \
    curl -L --retry 5 "${git_tarball_url}" --output "git-source.tar.gz" && \
    tar -xf "git-source.tar.gz" --strip 1 && \
    # Configure the custom git build to use openSSL
    make configure && \
    ./configure --prefix=/usr/local --with-openssl NO_TCLTK=1 NO_GETTEXT=1 && \
    # Build and install git
    make -j2 && \
    make install && \
    cd /tmp && rm -rf ./gitbuild && \
    # Get the latest git LFS binary
    mkdir /tmp/lfs_install && cd /tmp/lfs_install && \
    git_lfs_tarball_url="https://www.github.com$(curl 'https://github.com/git-lfs/git-lfs/releases' | grep -o "/git-lfs/git-lfs/releases/download/v2..*/git-lfs-linux-amd64-v2..*.tar.gz" | sort -r | head -1 | tr -d '\n')" && \
    curl -L --retry 5 "${git_lfs_tarball_url}" --output "git-lfs.tar.gz" && \
    tar -xf "git-lfs.tar.gz" && \
    # Configure Git-LFS
    cp ./git-lfs /usr/local/bin/git-lfs && \
    chmod 755 /usr/local/bin/git-lfs && \
    git lfs install && \
    cd /tmp && rm -rf ./lfs_install && \
    # Install node so you can run the CHP, and install the CHP
    apt-get -y install curl gnupg gnupg1 gnupg2 && \
    curl -sL https://deb.nodesource.com/setup_12.x | bash && \
    apt-get -y install nodejs && \
    npm install -g configurable-http-proxy && \
    cd /opt/confhttpproxy && pip3 install . && \
    # Install client package dependencies
    pip3 install wheel && \
    pip3 install -r /opt/gtmcore/requirements.txt && \
    pip3 install -r /opt/gtmapi/requirements.txt && \
    pip3 install uwsgi && \
    # Configure Honeytail (If running in a cluster, will be a noop otherwise)
    chmod u+x /tmp/honeytail.sh && /tmp/honeytail.sh && \
    # Cleanup!
    apt-get -qq -y remove gcc g++ wget curl gnupg gnupg1 gnupg2 make autoconf dh-autoreconf && \
    apt-get -qq -y autoremove && \
    apt-get -qq -y autoclean && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/log/dpkg.log && \
    rm /tmp/honeytail.sh

# Copy Libraries
# TODO: Make pip installs once refactor is completed
COPY packages/gtmapi /opt/gtmapi
COPY packages/gtmcore /opt/gtmcore
RUN cd /opt/gtmcore/ && python3 setup.py install

# Install testing requirements (will essentially be a noop in production)
COPY build/requirements-testing.txt /opt/requirements-testing.txt
RUN pip3 install -r /opt/requirements-testing.txt

# Setup client config file - should be written by automation before copy
COPY $CLIENT_CONFIG_FILE /etc/gigantum/labmanager.yaml

# Setup logging config file
COPY packages/gtmcore/gtmcore/logging/logging.json.default /etc/gigantum/logging.json

# Make needed directories
RUN mkdir -p /mnt/gigantum && mkdir /opt/redis

# Copy frontend
COPY --from=ui-builder /opt/ui/build /var/www/

# Setup NGINX/uWSGI
COPY $NGINX_UI_CONFIG /etc/nginx/sites-enabled/
COPY $NGINX_API_CONFIG /etc/nginx/sites-enabled/
RUN rm /etc/nginx/sites-enabled/default

# Setup Redis
COPY $REDIS_CONFIG /opt/redis/redis.conf

# Setup Supervisord to launch both uwsgi and nginx
RUN mkdir -p /opt/log/supervisor && mkdir -p /opt/log/nginx && mkdir -p /opt/run && \
    mkdir -p /opt/nginx && nginx && nginx -s reload && nginx -s quit
COPY resources/client/supervisord_base.conf /etc/supervisor/supervisord.conf
COPY $SUPERVISOR_CONFIG /etc/supervisor/conf.d/supervisord.conf

COPY $ENTRYPOINT_FILE /usr/local/bin/entrypoint.sh
RUN chmod u+x /usr/local/bin/entrypoint.sh

# Setup demo project
COPY resources/my-first-project.zip /opt/my-first-project.zip

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Expose Ports
EXPOSE 10000 10001 10002

# Start by firing up uwsgi, nginx, redis, and workers via supervisord
CMD ["/usr/bin/supervisord", "--nodaemon"]
