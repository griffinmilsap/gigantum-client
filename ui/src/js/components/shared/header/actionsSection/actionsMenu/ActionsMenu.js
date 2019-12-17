// vendor
import React, { Component, Fragment } from 'react';
import classNames from 'classnames';
import uuidv4 from 'uuid/v4';
import { connect } from 'react-redux';
// utilities
import JobStatus from 'JS/utils/JobStatus';
// mutations
import ExportLabbookMutation from 'Mutations/ExportLabbookMutation';
import ExportDatasetMutation from 'Mutations/ExportDatasetMutation';
import SyncLabbookMutation from 'Mutations/branches/SyncLabbookMutation';
import SyncDatasetMutation from 'Mutations/branches/SyncDatasetMutation';
import BuildImageMutation from 'Mutations/container/BuildImageMutation';
// store
import {
  setErrorMessage,
  setWarningMessage,
  setInfoMessage,
  setMultiInfoMessage,
} from 'JS/redux/actions/footer';
import store from 'JS/redux/store';
import { updateTransitionState } from 'JS/redux/actions/labbook/labbook';
import { setContainerMenuWarningMessage, setContainerMenuVisibility } from 'JS/redux/actions/labbook/environment/environment';
// queries
import UserIdentity from 'JS/Auth/UserIdentity';
import LinkedLocalDatasetsQuery from 'Components/shared/header/actionsSection/queries/LinkedLocalDatasetsQuery';
// components
import CreateBranch from 'Components/shared/modals/CreateBranch';
import Tooltip from 'Components/common/Tooltip';
import LoginPrompt from 'Components/shared/modals/LoginPrompt';
import VisibilityModal from 'Components/shared/modals/VisibilityModal';
import DeleteLabbook from 'Components/shared/modals/DeleteLabbook';
import DeleteDataset from 'Components/shared/modals/DeleteDataset';
// assets
import './ActionsMenu.scss';

class ActionsMenu extends Component {
  constructor(props) {
    super(props);

    const { owner, labbookName } = store.getState().routes;

    this.state = {
      addNoteEnabled: false,
      isValid: true,
      createBranchVisible: false,
      showLoginPrompt: false,
      exporting: false,
      deleteModalVisible: false,
      remoteUrl: props.remoteUrl,
      publishDisabled: false,
      justOpened: true,
      setPublic: false,
      syncWarningVisible: false,
      publishWarningVisible: false,
      visibilityModalVisible: false,
      owner,
      labbookName,
    };

    this._toggleMenu = this._toggleMenu.bind(this);
    this._closeMenu = this._closeMenu.bind(this);
    this._toggleModal = this._toggleModal.bind(this);
    this._mergeFilter = this._mergeFilter.bind(this);
    this._sync = this._sync.bind(this);
    this._closeLoginPromptModal = this._closeLoginPromptModal.bind(this);
    this._exportLabbook = this._exportLabbook.bind(this);
    this._switchBranch = this._switchBranch.bind(this);

    this._handleToggleModal = this._handleToggleModal.bind(this);

    this._resetState = this._resetState.bind(this);
    this._resetPublishState = this._resetPublishState.bind(this);
    this._setRemoteSession = this._setRemoteSession.bind(this);
    this._showContainerMenuMessage = this._showContainerMenuMessage.bind(this);
  }


  /**
   * attach window listener evetns here
  */
  componentDidMount() {
    window.addEventListener('click', this._closeMenu);
  }

  /**
   * detach window listener evetns here
  */
  componentWillUnmount() {
    window.removeEventListener('click', this._closeMenu);
  }

  /**
    @param {event} evt
    closes menu
  */
  _closeMenu(evt) {
    const isActionsMenu = (evt.target.className.indexOf('ActionsMenu') > -1) || (evt.target.className.indexOf('CollaboratorsModal') > -1) || (evt.target.className.indexOf('ActionsMenu__message') > -1)
    || (evt.target.className.indexOf('TrackingToggle') > -1);

    if (!isActionsMenu && this.state.menuOpen) {
      this.setState({ menuOpen: false, justOpened: true });
    }

    if ((evt.target.className.indexOf('ActionsMenu__btn--sync') === -1) && this.state.syncWarningVisible) {
      this.setState({ syncWarningVisible: false });
    }

    if ((evt.target.className.indexOf('ActionsMenu__btn--remote') === -1) && this.state.publishWarningVisible) {
      this.setState({ publishWarningVisible: false });
    }
  }

  /**
    @param {string} value
    sets state on createBranchVisible and toggles modal cover
  */
  _toggleModal(value) {
    this.setState({
      [value]: !this.state[value],
    });
  }

  /**
  *  @param {}
  *  toggles open menu state
  *  @return {string}
  */
  _toggleMenu() {
    this.setState({ menuOpen: !this.state.menuOpen });

    if (!this.state.menuOpen) {
      setTimeout(() => {
        this.setState({ justOpened: false });
      }, 500);
    } else {
      this.setState({ justOpened: true });
    }
  }

  /**
  *  @param {}
  *  remounts collaborators by updating key
  *  @return {}
  */
  _remountCollab() {
    this.setState({ collabKey: uuidv4() });
  }

  /**
  *  @param {string, boolean} action, containerRunning
  *  displays container menu message
  *  @return {}
  */
  _showContainerMenuMessage(action, containerRunning) {
    const dispatchMessage = containerRunning ? `Stop Project before ${action}. \n Be sure to save your changes.` : `Project is ${action}. \n Please do not refresh the page.`;

    this.setState({ menuOpen: false });

    this.props.setContainerMenuWarningMessage(dispatchMessage);
  }

  /**
  *  @param {Boolean} pullOnly
  *  pushes code to remote
  *  @return {string}
  */
  _sync(pullOnly) {
    const { props } = this;
    if (props.isExporting) {
      this.setState({ syncWarningVisible: true });
    } else {
      const status = store.getState().containerStatus.status;
      this.setState({ pullOnly });
      if (this.state.owner !== 'gigantum-examples') {
        this.setState({ menuOpen: false });
      }

      if ((status === 'Stopped') || (status === 'Rebuild') || props.sectionType !== 'labbook') {
        const id = uuidv4();
        const self = this;

        this._checkSessionIsValid().then((response) => {
          if (navigator.onLine) {
            if (response.data && response.data.userIdentity) {
              if (response.data.userIdentity.isSessionValid) {
                const failureCall = (errorMessage) => {
                  props.setSyncingState(false);
                  if (errorMessage.indexOf('Merge conflict') > -1) {
                    self._toggleSyncModal();
                  }
                };

                const successCall = () => {
                  props.setSyncingState(false);
                  if (props.sectionType === 'labbook') {
                    BuildImageMutation(
                      this.state.owner,
                      this.state.labbookName,
                      false,
                      (response, error) => {
                        if (error) {
                          console.error(error);
                          const messageData = {
                            id,
                            message: `ERROR: Failed to build ${this.state.labookName}`,
                            isLast: null,
                            error: true,
                            messageBody: error,
                          };
                          setMultiInfoMessage(messageData);
                        }
                      },
                    );
                  }

                  setContainerMenuVisibility(false);
                };
                if (props.sectionType === 'labbook') {
                  LinkedLocalDatasetsQuery.getLocalDatasets({ owner: this.state.owner, name: this.state.labbookName }).then((res) => {
                    const localDatasets = res.data && res.data.labbook.linkedDatasets.filter(linkedDataset => linkedDataset.defaultRemote && linkedDataset.defaultRemote.slice(0, 4) !== 'http');
                    if (localDatasets.length === 0) {
                      props.setSyncingState(true);

                      this._showContainerMenuMessage('syncing');
                      SyncLabbookMutation(
                        this.state.owner,
                        this.state.labbookName,
                        null,
                        pullOnly,
                        successCall,
                        failureCall,
                        (error) => {
                          if (error) {
                            failureCall(error);
                          }
                        },
                      );
                    } else {
                      this.setState({ localDatasets, publishDatasetsModalVisible: !this.state.publishDatasetsModalVisible, publishDatasetsModalAction: 'Sync' });
                    }
                  });
                } else {
                  props.setSyncingState(true);

                  this._showContainerMenuMessage('syncing');
                  SyncDatasetMutation(
                    this.state.owner,
                    this.state.labbookName,
                    false,
                    successCall,
                    failureCall,
                    (error) => {
                      if (error) {
                        failureCall(error);
                      }
                    },
                  );
                }
              } else {
                props.auth.renewToken(true, () => {
                  self.setState({ showLoginPrompt: true });
                }, () => {
                  self._sync(pullOnly);
                });
              }
            }
          } else {
            self.setState({ showLoginPrompt: true });
          }
        });
      } else {
        this.setState({ menuOpen: false });

        props.setContainerMenuWarningMessage('Stop Project before syncing. \n Be sure to save your changes.');
      }
    }
  }

  /**
  *  @param {}
  *  shows collaborators warning if user is not owner
  *  @return {}
  */
  _showCollaboratorsWarning() {
    const { owner } = store.getState().routes;
    const username = localStorage.getItem('username');

    if (owner !== username) {
      setWarningMessage(`Only ${owner} can add and remove collaborators in this labbook.`);
    }
  }

  /**
  *  @param {}
  *  returns UserIdentityQeury promise
  *  @return {promise}
  */
  _checkSessionIsValid() {
    return (UserIdentity.getUserIdentity());
  }

  /**
  *  @param {}
  *  closes login prompt modal
  *  @return {}
  */
  _closeLoginPromptModal() {
    this.setState({ showLoginPrompt: false });
  }

  /**
  *  @param {}
  *  copies remote
  *  @return {}
  */
  _copyRemote() {
    const copyText = document.getElementById('ActionsMenu-copy');
    copyText.select();

    document.execCommand('Copy');

    setInfoMessage(`${copyText.value} copied!`);
  }

  /**
  *  @param {jobKey}
  *  polls jobStatus for export job message
  *  updates footer with a message
  *  @return {}
  */
  _jobStatus(jobKey) {
    const self = this;
    const {
      owner,
      labbookName,
    } = self.state;
    JobStatus.getJobStatus(jobKey).then((data) => {
      this.props.setExportingState(false);
      updateTransitionState(owner, labbookName, '');
      if (data.jobStatus.result) {
        setInfoMessage(`Export file ${data.jobStatus.result} is available in the export directory of your Gigantum working directory.`);
      }

      this.setState({ exporting: false });
    }).catch((error) => {
      updateTransitionState(owner, labbookName, '');
      console.log(error);

      this.props.setExportingState(false);

      const errorArray = [{ message: 'Export failed.' }];

      setErrorMessage(`${this.state.labbookName} failed to export `, errorArray);

      this.setState({ exporting: false });
    });
  }

  /**
  *  @param {}
  *  runs export mutation if export has not been downloaded
  *  @return {}
  */
  _exportLabbook = () => {
    const { props } = this;
    const {
      owner,
      labbookName,
    } = this.state;
    if (!props.isLocked) {
      this.setState({ exporting: true, menuOpen: false });

      const exportType = (this.props.sectionType === 'dataset') ? 'Dataset' : 'Project';

      setInfoMessage(`Exporting ${labbookName} ${exportType}`);

      updateTransitionState(owner, labbookName, 'Exporting');

      this.props.setExportingState(true);
      if (this.props.sectionType !== 'dataset') {
        ExportLabbookMutation(
          owner,
          labbookName,
          (response, error) => {
            if (response.exportLabbook) {
              this._jobStatus(response.exportLabbook.jobKey);
            } else {
              console.log(error);

              this.props.setExportingState(false);

              setErrorMessage('Export Failed', error);
            }
          },
        );
      } else {
        ExportDatasetMutation(
          owner,
          labbookName,
          (response, error) => {
            if (response.exportDataset) {
              this._jobStatus(response.exportDataset.jobKey);
            } else {
              console.log(error);

              this.props.setExportingState(false);

              setErrorMessage('Export Failed', error);
            }
          },
        );
      }
    } else {
      this._showContainerMenuMessage('exporting', true);
    }
  }

  /**
  *  @param {}
  *  toggle stat and modal visibility
  *  @return {}
  */
  _toggleDeleteModal() {
    this.setState({ deleteModalVisible: !this.state.deleteModalVisible });
  }

  /**
  *  @param {}
  *  sets menu
  *  @return {}
  */
  _mergeFilter() {
    if (store.getState().containerStatus.status !== 'Running') {
      this.props.toggleBranchesView(true, true);

      this.setState({ menuOpen: false });

      window.scrollTo(0, 0);
    } else {
      this._showContainerMenuMessage('merging branches', true);
    }
  }

  /**
  *  @param {}
  *  sets menu
  *  @return {}
  */
  _switchBranch() {
    const status = store.getState().containerStatus.status;

    if (status !== 'Running') {
      window.scrollTo(0, 0);

      this.props.toggleBranchesView(true, false);

      this.setState({ menuOpen: false });
    } else {
      this._showContainerMenuMessage('switching branches', true);
    }
  }

  /**
  *  @param {string} modal
  *  passes modal to toggleModal if container is not running
  *  @return {}
  */
  _handleToggleModal(modal) {
    let action = '';

    if (store.getState().containerStatus.status !== 'Running') {
      this._toggleModal(modal);
    } else {
      switch (modal) {
        case 'createBranchVisible':
          action = 'creating branches';
          break;
        default:
          break;
      }

      this._showContainerMenuMessage(action, true);
    }
  }

  /**
  *  @param {}
  *  resets state after publish
  *  @return {}
  */
  _resetState() {
    this.setState({
      remoteUrl: '',
      showLoginPrompt: true,
    });
  }

  /**
  *  @param {}
  *  resets state after publish
  *  @return {}
  */
  _resetPublishState(publishDisabled) {
    this.setState({
      menuOpen: false,
      publishDisabled,
    });
  }

  /**
  *  @param {}
  *  resets state after publish
  *  @return {}
  */
  _setRemoteSession() {
    this.setState({
      addedRemoteThisSession: true,
      remoteUrl: `https://gigantum.com/${this.state.owner}/${this.state.labbookName}`,
    });
  }


  render() {
    const { props, state } = this;
    const { labbookName, owner } = state;
    const branchMenuCSS = classNames({
      'ActionsMenu__menu--animation': state.justOpened, // this is needed to stop animation from breaking position flow when collaborators modal is open
      hidden: !state.menuOpen,
      'ActionsMenu__menu box-shadow': true,
    });

    const exportButtonCSS = classNames({
      'ActionsMenu__btn--flat': true,
      'Tooltip-data': props.isLocked,
    });

    const deleteText = props.sectionType === 'labbook' ? 'Delete Project' : 'Delete Dataset';

    return (
      <div className="ActionsMenu flex flex--column'">

        {
          state.showLoginPrompt

          && <LoginPrompt closeModal={this._closeLoginPromptModal} />
        }
        {
          (state.deleteModalVisible && (props.sectionType === 'labbook'))
          && (
            <DeleteLabbook
              handleClose={() => this._toggleDeleteModal()}
              remoteAdded={props.defaultRemote}
              history={props.history}
            />
          )
        }
        {
          (state.deleteModalVisible && !(props.sectionType === 'labbook'))
          && (
            <DeleteDataset
              handleClose={() => this._toggleDeleteModal()}
              remoteAdded={props.defaultRemote}
              history={props.history}
              owner={state.owner}
              name={state.labbookName}
            />
          )
        }
        {
          state.visibilityModalVisible

          && (
          <VisibilityModal
            sectionType={props.sectionType}
            owner={state.owner}
            name={state.labbookName}
            auth={props.auth}
            toggleModal={this._toggleModal}
            buttonText="Save"
            header="Change Visibility"
            modalStateValue="visibilityModalVisible"
            checkSessionIsValid={this._checkSessionIsValid}
            resetState={this._resetState}
            visibility={props.visibility}
          />
          )
        }

        <CreateBranch
          description={props.description}
          modalVisible={state.createBranchVisible}
          toggleModal={this._toggleModal}
        />

        <button
          onClick={() => { this._toggleMenu(); }}
          className="ActionsMenu__btn Btn--last"
          type="button"
        />

        <div className={branchMenuCSS}>

          <ul className="ActionsMenu__list">

            <li className="ActionsMenu__item ActionsMenu__item--export">
              <button
                onClick={() => this._exportLabbook()}
                disabled={state.exporting || props.isLocked}
                className={exportButtonCSS}
                type="button"
                data-tooltip="Cannot export Project while in use"
              >
                Export to Zip
              </button>

              <div
                className="Tooltip-data Tooltip-data--top-offset Tooltip-data--info"
                data-tooltip="Exports project zip file to your gignatum directory"
              />

            </li>


            <li className="ActionsMenu__item ActionsMenu__item--delete">

              <button
                onClick={() => this._toggleDeleteModal()}
                className="ActionsMenu__btn--flat"
              >
                {deleteText}
              </button>

            </li>

            {
              props.defaultRemote

              && (
              <li className={`ActionsMenu__item ActionsMenu__item--visibility-${props.visibility}`}>

                <button
                  onClick={evt => this._toggleModal('visibilityModalVisible')}
                  className="ActionsMenu__btn--flat"
                >
                  Change Visibility
                </button>

              </li>
              )
            }
            {
              (state.remoteUrl || props.defaultRemote)
              && (
              <li className="ActionsMenu__item ActionsMenu__item--copy">
                <div className="ActionsMenu__item--label">Get Share URL</div>
                <div className="ActionsMenu__copyRemote">

                  <input
                    id="ActionsMenu-copy"
                    className="ActionsMenu__input"
                    defaultValue={`gigantum.com/${state.owner}/${state.labbookName}`}
                    type="text"
                  />

                  <button
                    onClick={() => this._copyRemote()}
                    className="ActionsMenu__btn--copy fa fa-clone"
                  />
                </div>
              </li>
              )
            }

          </ul>

        </div>

        <Tooltip section="actionMenu" />

      </div>
    );
  }
}

const mapStateToProps = (state, ownProps) => state.packageDependencies;

const mapDispatchToProps = dispatch => ({
  setContainerMenuWarningMessage,
});

export default connect(mapStateToProps, mapDispatchToProps)(ActionsMenu);
