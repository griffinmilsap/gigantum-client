// vendor
import React, { Component } from 'react';
import uuidv4 from 'uuid/v4';
import Highlighter from 'react-highlight-words';
import classNames from 'classnames';
import Moment from 'moment';
import { boundMethod } from 'autobind-decorator';
// muations
import ImportRemoteDatasetMutation from 'Mutations/ImportRemoteDatasetMutation';
// store
import store from 'JS/redux/store';
import { setWarningMessage, setMultiInfoMessage } from 'JS/redux/actions/footer';
// queries
import UserIdentity from 'JS/Auth/UserIdentity';
// components
import LoginPrompt from 'Components/shared/modals/LoginPrompt';
import Loader from 'Components/common/Loader';
// assets
import './RemoteDatasetsPanel.scss';
// config
import config from 'JS/config';

export default class RemoteDatasetPanel extends Component {
  state = {
    isImporting: false,
    showLoginPrompt: false,
  };

  /**
    *  @param {String} owner
    *  @param {String} datasetName
    *  @param {String} remote
    *  handles importing dataset mutation
  */
  @boundMethod
  _handleImportDataset(owner, datasetName, remote) {
    const { props } = this;
    const id = uuidv4();
    ImportRemoteDatasetMutation(
      owner,
      datasetName,
      remote,
      (response, error) => {
        this._clearState();

        if (error) {
          console.error(error);
          const messageData = {
            id,
            message: 'ERROR: Could not import remote Dataset',
            isLast: null,
            error: true,
            messageBody: error,
          };
          setMultiInfoMessage(messageData);
        } else if (response) {
          const { newDatasetEdge } = response.importRemoteDataset;
          const { name } = newDatasetEdge.node;
          const messageData = {
            id,
            message: `Successfully imported remote Dataset ${name}`,
            isLast: true,
            error: false,
          };
          setMultiInfoMessage(messageData);

          props.history.replace(`/datasets/${owner}/${name}`);
        }
      },
    );
  }

  /**
    *  @param {owner, datasetName}
    *  imports dataset from remote url, builds the image, and redirects to imported dataset
    *  @return {}
  */
  @boundMethod
  _importDataset(owner, datasetName) {
    const { props } = this;
    const id = uuidv4();
    const remote = `https://repo.${config.domain}/${owner}/${datasetName}`;

    UserIdentity.getUserIdentity().then((response) => {
      if (navigator.onLine) {
        if (response.data) {
          if (response.data.userIdentity.isSessionValid) {
            this._importingState();
            const messageData = {
              id,
              message: 'Importing Dataset please wait',
              isLast: false,
              error: false,
            };
            setMultiInfoMessage(messageData);
            this._handleImportDataset(owner, datasetName, remote);
          } else {
            props.auth.renewToken(true, () => {
              this.setState({ showLoginPrompt: true });
            }, () => {
              this._importDataset(owner, datasetName);
            });
          }
        }
      } else {
        this.setState({ showLoginPrompt: true });
      }
    });
  }

  /**
   *  @param {}
   *  changes state of isImporting to false
   */
  @boundMethod
  _clearState() {
    if (document.getElementById('dashboard__cover')) {
      document.getElementById('dashboard__cover').classList.add('hidden');
    }
    this.setState({
      isImporting: false,
    });
  }

  /**
     * @param {}
     * fires when user identity returns invalid session
     * prompts user to revalidate their session
  */
  @boundMethod
  _closeLoginPromptModal() {
    this.setState({ showLoginPrompt: false });
  }

  /**
    *  @param {}
    *  changes state of isImporting to true
   */
  @boundMethod
  _importingState() {
    if (document.getElementById('dashboard__cover')) {
      document.getElementById('dashboard__cover').classList.remove('hidden');
    }
    this.setState({ isImporting: true });
  }

  /**
  * @param {object} edge
  * validates user's session and then triggers toggleDeleteModal
  * which passes parameters to the DeleteDataset component
  */
  @boundMethod
  _handleDelete(edge) {
    const { props } = this;
    if (localStorage.getItem('username') !== edge.node.owner) {
      setWarningMessage('You can only delete remote Datasets that you have created.');
    } else {
      UserIdentity.getUserIdentity().then((response) => {
        if (navigator.onLine) {
          if (response.data) {
            if (response.data.userIdentity.isSessionValid) {
              props.toggleDeleteModal({
                remoteId: edge.node.id,
                remoteOwner: edge.node.owner,
                remoteDatasetName: edge.node.name,
                existsLocally: props.existsLocally,
              });
            } else {
              props.auth.renewToken(true, () => {
                this.setState({ showLoginPrompt: true });
              }, () => {
                props.toggleDeleteModal({
                  remoteId: edge.node.id,
                  remoteOwner: edge.node.owner,
                  remoteDatasetName: edge.node.name,
                  existsLocally: props.existsLocally,
                });
              });
            }
          }
        } else {
          this.setState({ showLoginPrompt: true });
        }
      });
    }
  }

  render() {
    const { props, state } = this;
    const { edge } = props;
    const deleteTooltipText = localStorage.getItem('username') !== edge.node.owner ? 'Only owners and admins can delete a remote Dataset' : '';
    const deleteDisabled = state.isImporting || (localStorage.getItem('username') !== edge.node.owner);
    // declare css here
    const descriptionCss = classNames({
      'RemoteDatasets__row RemoteDatasets__row--text': true,
      blur: state.isImporting,
    });
    const deleteCSS = classNames({
      'Btn__dashboard Btn--action': true,
      'Btn__dashboard--delete': localStorage.getItem('username') === edge.node.owner,
      'Btn__dashboard--delete-disabled Tooltip-data': localStorage.getItem('username') !== edge.node.owner,
    });

    return (
      <div
        key={edge.node.name}
        className="Card Card--225 column-4-span-3 flex flex--column justify--space-between"
      >
        <div className="RemoteDatasets__row RemoteDatasets__row--icon">
          { !(edge.node.visibility === 'local')
            && (
              <div
                data-tooltip={`${edge.node.visibility}`}
                className={`Tooltip-Listing RemoteDatasets__${edge.node.visibility} Tooltip-data Tooltip-data--small`}
              />
            )
          }
          { props.existsLocally
            ? (
              <button
                type="button"
                className="Btn__dashboard Btn--action Btn__dashboard--cloud Tooltip-data"
                data-tooltip="This Dataset has already been imported"
                disabled
              >
              Imported
              </button>
            )
            : (
              <button
                type="button"
                disabled={state.isImporting}
                className="Btn__dashboard Btn--action Btn__dashboard--cloud-download"
                onClick={() => this._importDataset(edge.node.owner, edge.node.name)}
              >
              Import
              </button>
            )
        }
          <button
            type="button"
            className={deleteCSS}
            data-tooltip={deleteTooltipText}
            disabled={deleteDisabled}
            onClick={() => this._handleDelete(edge)}
          >
            Delete
          </button>

        </div>

        <div className={descriptionCss}>
          <div className="RemoteDatasets__row RemoteDatasets__row--title">
            <h5 className="RemoteDatasets__panel-title">
              <Highlighter
                highlightClassName="LocalDatasets__highlighted"
                searchWords={[store.getState().datasetListing.filterText]}
                autoEscape={false}
                caseSensitive={false}
                textToHighlight={edge.node.name}
              />
            </h5>
          </div>

          <p className="RemoteDatasets__paragraph RemoteDatasets__paragraph--owner">{edge.node.owner}</p>
          <p className="RemoteDatasets__paragraph RemoteDatasets__paragraph--metadata">
            <span className="bold">Created:</span>
            {' '}
            {Moment(edge.node.creationDateUtc).format('MM/DD/YY')}
          </p>
          <p className="RemoteDatasets__paragraph RemoteDatasets__paragraph--metadata">
            <span className="bold">Modified:</span>
            {' '}
            {Moment(edge.node.modifiedDateUtc).fromNow()}
          </p>
          <p className="RemoteDatasets__paragraph RemoteDatasets__paragraph--description">

            { edge.node.description && edge.node.description.length
              ? (
                <Highlighter
                  highlightClassName="LocalDatasets__highlighted"
                  searchWords={[store.getState().datasetListing.filterText]}
                  autoEscape={false}
                  caseSensitive={false}
                  textToHighlight={edge.node.description}
                />
              )
              : <span className="RemoteDatasets__description--blank"> No description provided </span>
           }
          </p>
        </div>

        { state.isImporting
          && <div className="RemoteDatasets__loader"><Loader /></div>
        }

        { state.showLoginPrompt
          && <LoginPrompt closeModal={this._closeLoginPromptModal} />
        }
      </div>
    );
  }
}
