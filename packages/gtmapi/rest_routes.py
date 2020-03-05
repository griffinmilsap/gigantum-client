from flask import Blueprint, jsonify, request, abort, current_app
from flask_cors import CORS, cross_origin
import redis

from lmsrvcore import telemetry
from lmsrvcore.auth.user import get_logged_in_author, get_logged_in_username
from gtmcore.inventory.inventory import InventoryManager
from gtmcore.logging import LMLogger
from gtmcore.gitlib.git import GitAuthor


logger = LMLogger.get_logger()
rest_routes = Blueprint('rest_routes', __name__)


@rest_routes.route(f"/sysinfo")
@cross_origin(headers=["Content-Type", "Authorization"], max_age=7200)
def sysinfo():
    return jsonify(telemetry.service_telemetry())


@rest_routes.route(f"/project-errors")
@cross_origin(headers=["Content-Type", "Authorization"], max_age=7200)
def check_projects():
    """Check a user's set of projects to find any that may be corrupted, and return
    it as a JSON object with the schema specified in the `check_projects` method.

    Note: We only use username loaded from the request headers for security reasons --
    i.e., we don't want to invite someone to crawl anyone else's projects. """

    try:
        username = get_logged_in_username()
        return jsonify(telemetry.check_projects(current_app.config['LABMGR_CONFIG'], username))
    except Exception as e:
        logger.error(e)
        return jsonify({'error': 'Cannot load username from request.'})


# Set Unauth'd route for API health-check
@rest_routes.route(f"/ping")
@cross_origin(headers=["Content-Type", "Authorization"], max_age=7200)
def ping():
    """Unauthorized endpoint for validating the API is up"""
    config = current_app.config['LABMGR_CONFIG']
    app_name, built_on, revision = config.config['build_info'].split(' :: ')
    return jsonify({
        "application": app_name,
        "built_on": built_on,
        "revision": revision
    })


@rest_routes.route(f"/version/")
@rest_routes.route(f"/version")
@cross_origin(headers=["Content-Type", "Authorization"], max_age=7200)
def version():
    """Unauthorized endpoint for validating the API is up.

    Note: /api/version endpoint added due to popup blockers starting to block /api/ping/

    TODO! By August 2019, remove the .route(f'/version/') route.
    """
    config = current_app.config['LABMGR_CONFIG']
    app_name, built_on, revision = config.config['build_info'].split(' :: ')
    return jsonify({
        "application": app_name,
        "built_on": built_on,
        "revision": revision
    })


@rest_routes.route(f'/savehook/<username>/<owner>/<labbook_name>')
def savehook(username: str, owner: str, labbook_name: str):
    """Save hook called by Jupyter

    Note that this is handled directly in monitor_rserver.py"""
    try:
        changed_file = request.args.get('file')
        jupyter_token = request.args.get('jupyter_token')
        email = request.args.get('email')
        logger.debug(f"Received save hook for {changed_file} in {username}/{owner}/{labbook_name}")

        redis_conn = redis.Redis(db=1)
        lb_jupyter_token_key = '-'.join(['gmlb', username, owner, labbook_name, 'jupyter-token'])
        lb_active_key = f"{'|'.join([username, owner, labbook_name])}&is-busy*"

        r = redis_conn.get(lb_jupyter_token_key.encode())
        if r is None:
            logger.error(f"Could not find jupyter token for {username}/{owner}/{labbook_name}")
            abort(400)

        if r.decode() != jupyter_token:
            raise ValueError("Incoming jupyter token must be valid")

        if len(redis_conn.keys(lb_active_key.encode())) > 0:
            # A kernel in this project is still active. Don't save auto-commit because it can blow up the
            # repository size depending on what the user is doing
            logger.info(f"Skipping jupyter savehook for {username}/{owner}/{labbook_name} due to active kernel")
            return 'success'

        lb = InventoryManager().load_labbook(username, owner, labbook_name,
                                             author=GitAuthor(name=username, email=email))
        with lb.lock():
            lb.sweep_uncommitted_changes()

        logger.info(f"Jupyter save hook saved {changed_file} from {str(lb)}")
        return 'success'
    except Exception as err:
        logger.error(err)
        return abort(400)
