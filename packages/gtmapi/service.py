#!/usr/bin/python3

import shutil
import os
import base64
import flask
import blueprint
from flask_cors import CORS
from confhttpproxy import ProxyRouter
from flask import Flask, jsonify

import rest_routes
from gtmcore.configuration import Configuration
from gtmcore.logging import LMLogger
from gtmcore.environment import RepositoryManager
from gtmcore.auth.identity import AuthenticationError, get_identity_manager
from gtmcore.labbook.lock import reset_all_locks


logger = LMLogger.get_logger()
app = Flask("lmsrvlabbook")

# Load configuration class into the flask application
if os.path.exists(Configuration.USER_LOCATION):
    logger.info(f"Using custom user configuration from {Configuration.USER_LOCATION}")
else:
    logger.info("No custom user configuration found")

random_bytes = os.urandom(32)
app.config["SECRET_KEY"] = base64.b64encode(random_bytes).decode('utf-8')
app.config["LABMGR_CONFIG"] = config = Configuration()
app.config["LABMGR_ID_MGR"] = get_identity_manager(Configuration())

# Set Debug mode
app.config['DEBUG'] = config.config["flask"]["DEBUG"]
app.register_blueprint(blueprint.complete_labbook_service)

# Configure CHP
try:
    # /api by default
    api_prefix = app.config["LABMGR_CONFIG"].config['proxy']["labmanager_api_prefix"]

    # CHP interface params
    apparent_proxy_port = app.config["LABMGR_CONFIG"].config['proxy']["apparent_proxy_port"]
    api_port = app.config["LABMGR_CONFIG"].config['proxy']['api_port']
    proxy_router = ProxyRouter.get_proxy(app.config["LABMGR_CONFIG"].config['proxy'])

    if config.is_hub_client:
        # Use full route prefix, including run/<client_id> if running in the Hub
        api_target = f"run/{os.environ['GIGANTUM_CLIENT_ID']}{api_prefix}"
        api_prefix = f"/{api_target}"

        # explicit routes for UI with full route prefix
        proxy_router.add("http://localhost:10002", f"run/{os.environ['GIGANTUM_CLIENT_ID']}")
    else:
        api_target = "api"

    proxy_router.add("http://localhost:10001", api_target)
    logger.info(f"Proxy routes ({type(proxy_router)}): {proxy_router.routes}")

    # Add rest routes
    app.register_blueprint(rest_routes.rest_routes, url_prefix=api_prefix)
except Exception as e:
    logger.error(e)
    logger.exception(e)


if config.config["flask"]["allow_cors"]:
    # Allow CORS
    CORS(app, max_age=7200)


# Set auth error handler
@app.errorhandler(AuthenticationError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


# TEMPORARY KLUDGE
# Due to GitPython implementation, resources leak. This block deletes all GitPython instances at the end of the request
# Future work will remove GitPython, at which point this block should be removed.
@app.after_request
def cleanup_git(response):
    loader = getattr(flask.request, 'labbook_loader', None)
    if loader:
        for key in loader.__dict__["_promise_cache"]:
            try:
                lb = loader.__dict__["_promise_cache"][key].value
                lb.git.repo.__del__()
            except AttributeError:
                continue
    return response
# TEMPORARY KLUDGE


logger.info("Cloning/Updating environment repositories.")

try:
    erm = RepositoryManager()
    update_successful = erm.update_repositories()
    if update_successful:
        logger.info("Indexing environment repositories.")
        erm.index_repositories()
        logger.info("Environment repositories updated and ready.")

    else:
        logger.info("Unable to update environment repositories at startup, most likely due to lack of internet access.")
except Exception as e:
    logger.error(e)
    raise

# Empty container-container share dir as it is ephemeral
share_dir = os.path.join(os.path.sep, 'mnt', 'share')
logger.info("Emptying container-container share folder: {}.".format(share_dir))
try:
    for item in os.listdir(share_dir):
        item_path = os.path.join(share_dir, item)
        if os.path.isfile(item_path):
            os.unlink(item_path)
        else:
            shutil.rmtree(item_path)
except Exception as e:
    logger.error(f"Failed to empty share folder: {e}.")
    raise

post_save_hook_code = """
import subprocess, os
def post_save_hook(os_path, model, contents_manager, **kwargs):
    try:
        client_ip = os.environ.get('GIGANTUM_CLIENT_IP')
        if os.environ.get('HUB_CLIENT_ID'):
            # Running in the Hub
            service_route = "run/{}/api/savehook".format(os.environ.get('HUB_CLIENT_ID'))
        else:
            # Running locally
            service_route = "api/savehook"
        
        tokens = open('/home/giguser/jupyter_token').read().strip()
        username, owner, lbname, jupyter_token = tokens.split(',')
        url_args = "file={}&jupyter_token={}".format(os.path.basename(os_path), jupyter_token)
        url = "http://{}:10001/{}/{}/{}/{}?{}".format(client_ip,service_route,username,owner,lbname,url_args)
        subprocess.run(['wget', '--spider', url], cwd='/tmp')
    except Exception as e:
        print(e)

"""
os.makedirs(os.path.join(share_dir, 'jupyterhooks'))
with open(os.path.join(share_dir, 'jupyterhooks', '__init__.py'), 'w') as initpy:
    initpy.write(post_save_hook_code)


# Reset distributed lock, if desired
if config.config["lock"]["reset_on_start"]:
    logger.info("Resetting ALL distributed locks")
    reset_all_locks(config.config['lock'])

# Create local data (for local dataset types) dir if it doesn't exist
local_data_dir = os.path.join(app.config["LABMGR_CONFIG"].config['git']['working_directory'], 'local_data')
if os.path.isdir(local_data_dir) is False:
    os.makedirs(local_data_dir, exist_ok=True)
    logger.info(f'Created `local_data` dir for Local Filesystem Dataset Type: {local_data_dir}')

# Create certificates file directory for custom CA certificate support.
certificate_dir = os.path.join(app.config["LABMGR_CONFIG"].config['git']['working_directory'], 'certificates')
if os.path.isdir(certificate_dir) is False:
    os.makedirs(certificate_dir, exist_ok=True)
    logger.info(f'Created `certificates` dir for custom CA certificates: {certificate_dir}')


# make sure temporary upload directory exists and is empty
tempdir = Configuration().upload_dir
if os.path.exists(tempdir):
    shutil.rmtree(tempdir)
    logger.info(f'Cleared upload temp dir: {tempdir}')
os.makedirs(tempdir)


def main(debug=False) -> None:
    try:
        # Run app on 0.0.0.0, assuming not an issue since it should be in a container
        # Please note: Debug mode must explicitly be set to False when running integration
        # tests, due to properties of Flask werkzeug dynamic package reloading.
        if debug:
            # This is to support integration tests, which will call main
            # with debug=False in order to avoid runtime reloading of Python code
            # which causes the interpreter to crash.
            app.run(host="0.0.0.0", port=10001, debug=debug)
        else:
            # If debug arg is not explicitly given then it is loaded from config
            app.run(host="0.0.0.0", port=10001)
    except Exception as err:
        logger.exception(err)
        raise


if __name__ == '__main__':
    main()
