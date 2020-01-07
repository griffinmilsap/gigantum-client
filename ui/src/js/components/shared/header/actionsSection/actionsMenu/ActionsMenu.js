// @flow
// vendor
import React, { Component } from 'react';
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

type Props = {
  auth: {
    renewToken: Function,
  },
  defaultRemote: string,
  description: string,
  history: Object,
  isExporting: boolean,
  isLocked: bool,
  name: string,
  owner: string,
  remoteUrl: string,
  sectionType: string,
  setExportingState: Function,
  setSyncingState: Function,
  toggleBranchesView: Function,
  visibility: string,
};


class ActionsMenu extends Component<Props> {
  state = {
    addNoteEnabled: false,
    isValid: true,
    createBranchVisible: false,
    showLoginPrompt: false,
    exporting: false,
    deleteModalVisible: false,
    publishDisabled: false,
    justOpened: true,
    setPublic: false,
    syncWarningVisible: false,
    publishWarningVisible: false,
    visibilityModalVisible: false,
    remoteUrl: this.props.remoteUrl,
    owner: this.props.owner,
    name: this.props.owner,
  };


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
  _closeMenu = (evt) => {
    const {
      menuOpen,
      syncWarningVisible,
      publishWarningVisible,
    } = this.state;
    const isActionsMenu = (evt.target.className.indexOf('ActionsMenu') > -1)
      || (evt.target.className.indexOf('CollaboratorsModal') > -1)
      || (evt.target.className.indexOf('ActionsMenu__message') > -1)
      || (evt.target.className.indexOf('TrackingToggle') > -1);

    if (!isActionsMenu && menuOpen) {
      this.setState({ menuOpen: false, justOpened: true });
    }

    if (
      (evt.target.className.indexOf('ActionsMenu__btn--sync') === -1)
      && syncWarningVisible
    ) {
      this.setState({ syncWarningVisible: false });
    }

    if (
      (evt.target.className.indexOf('ActionsMenu__btn--remote') === -1)
      && publishWarningVisible
    ) {
      this.setState({ publishWarningVisible: false });
    }
  }

  /**
    @param {string} value
    sets state on createBranchVisible and toggles modal cover
  */
  _toggleModal = (value) => {
    this.setState((state) => {
      const inverseValue = !state[value];
      return {
        [value]: inverseValue,
      };
    });
  }

  /**
  *  @param {}
  *  toggles open menu state
  *  @return {string}
  */
  _toggleMenu = () => {
    this.setState((state) => {
      const menuOpen = !state.menuOpen;
      return ({ menuOpen });
    });

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
  _remountCollab = () => {
    this.setState({ collabKey: uuidv4() });
  }

  /**
  *  @param {string, boolean} action, containerRunning
  *  displays container menu message
  *  @return {}
  */
  _showContainerMenuMessage = (action, containerRunning) => {
    const dispatchMessage = containerRunning ? `Stop Project before ${action}. \n Be sure to save your changes.` : `Project is ${action}. \n Please do not refresh the page.`;

    this.setState({ menuOpen: false });

    setContainerMenuWarningMessage(dispatchMessage);
  }

  /**
  *  @param {Boolean} pullOnly
  *  pushes code to remote
  *  @return {string}
  */
  _sync = (pullOnly) => {
    const {
      auth,
      owner,
      name,
      isExporting,
      setSyncingState,
      sectionType,
    } = this.props;

    if (isExporting) {
      this.setState({ syncWarningVisible: true });
    } else {
      const { status } = store.getState().containerStatus;
      this.setState({ pullOnly });

      if (owner !== 'gigantum-examples') {
        this.setState({ menuOpen: false });
      }

      if (
        (status === 'Stopped')
        || (status === 'Rebuild')
        || (sectionType !== 'labbook')
      ) {
        const id = uuidv4();
        const self = this;

        this._checkSessionIsValid().then((response) => {
          if (navigator.onLine) {
            if (response.data && response.data.userIdentity) {
              if (response.data.userIdentity.isSessionValid) {
                const failureCall = (errorMessage) => {
                  setSyncingState(false);
                  if (errorMessage.indexOf('Merge conflict') > -1) {
                    self._toggleSyncModal();
                  }
                };

                const successCall = () => {
                  setSyncingState(false);
                  if (sectionType === 'labbook') {
                    BuildImageMutation(
                      owner,
                      name,
                      false,
                      (response, error) => {
                        if (error) {
                          console.error(error);
                          const messageData = {
                            id,
                            message: `ERROR: Failed to build ${name}`,
                            isLast: null,
                            error: true,
                            messageBody: error,
                          };
                          setMultiInfoMessage(owner, name, messageData);
                        }
                      },
                    );
                  }

                  setContainerMenuVisibility(false);
                };
                if (sectionType === 'labbook') {
                  LinkedLocalDatasetsQuery.getLocalDatasets({
                    owner,
                    name,
                  }).then((res) => {
                    const localDatasets = res.data
                      && res.data.labbook.linkedDatasets.filter(linkedDataset => linkedDataset.defaultRemote && linkedDataset.defaultRemote.slice(0, 4) !== 'http');

                    if (localDatasets.length === 0) {
                      setSyncingState(true);

                      this._showContainerMenuMessage('syncing');
                      SyncLabbookMutation(
                        owner,
                        name,
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
                      this.setState((state) => {
                        const publishDatasetsModalVisible = !state.publishDatasetsModalVisible;
                        return {
                          localDatasets,
                          publishDatasetsModalVisible,
                          publishDatasetsModalAction: 'Sync',
                        };
                      });
                    }
                  });
                } else {
                  setSyncingState(true);

                  this._showContainerMenuMessage('syncing');
                  SyncDatasetMutation(
                    owner,
                    name,
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
                auth.renewToken(true, () => {
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

        setContainerMenuWarningMessage('Stop Project before syncing. \n Be sure to save your changes.');
      }
    }
  }

  /**
  *  @param {}
  *  shows collaborators warning if user is not owner
  *  @return {}
  */
  _showCollaboratorsWarning = () => {
    const { owner, name } = this.props;
    const username = localStorage.getItem('username');

    if (owner !== username) {
      setWarningMessage(owner, name, `Only ${owner} can add and remove collaborators in this labbook.`);
    }
  }

  /**
  *  @param {}
  *  returns UserIdentityQeury promise
  *  @return {promise}
  */
  _checkSessionIsValid = () => {
    return (UserIdentity.getUserIdentity());
  }

  /**
  *  @param {}
  *  closes login prompt modal
  *  @return {}
  */
  _closeLoginPromptModal = () => {
    this.setState({ showLoginPrompt: false });
  }

  /**
  *  @param {}
  *  copies remote
  *  @return {}
  */
  _copyRemote = () => {
    const {
      owner,
      name,
    } = this.state;
    const copyText = document.getElementById('ActionsMenu-copy');
    copyText.select();

    document.execCommand('Copy');

    setInfoMessage(owner, name, `${copyText.value} copied!`);
  }

  /**
  *  @param {jobKey}
  *  polls jobStatus for export job message
  *  updates footer with a message
  *  @return {}
  */
  _jobStatus = (jobKey) => {
    const {
      setExportingState,
      owner,
      name,
    } = this.props;

    JobStatus.getJobStatus(owner, name, jobKey).then((data) => {
      setExportingState(false);
      updateTransitionState(owner, name, '');

      if (data.jobStatus.result) {
        setInfoMessage(owner, name, `Export file ${data.jobStatus.result} is available in the export directory of your Gigantum working directory.`);
      }

      this.setState({ exporting: false });
    }).catch((error) => {
      updateTransitionState(owner, name, '');
      console.log(error);

      setExportingState(false);

      const errorArray = [{ message: 'Export failed.' }];

      setErrorMessage(owner, name, `${name} failed to export `, errorArray);

      this.setState({ exporting: false });
    });
  }

  /**
  *  @param {}
  *  runs export mutation if export has not been downloaded
  *  @return {}
  */
  _exportLabbook = () => {
    const {
      sectionType,
      setExportingState,
      owner,
      name,
      isLocked,
    } = this.props;

    if (!isLocked) {
      this.setState({
        exporting: true,
        menuOpen: false,
      });
      const exportType = (sectionType === 'dataset') ? 'Dataset' : 'Project';

      setInfoMessage(owner, name, `Exporting ${name} ${exportType}`);
      updateTransitionState(owner, name, 'Exporting');

      setExportingState(true);
      if (sectionType !== 'dataset') {
        ExportLabbookMutation(
          owner,
          name,
          (response, error) => {
            if (response.exportLabbook) {
              this._jobStatus(response.exportLabbook.jobKey);
            } else {
              console.log(error);

              setExportingState(false);

              setErrorMessage(owner, name, 'Export Failed', error);
            }
          },
        );
      } else {
        ExportDatasetMutation(
          owner,
          name,
          (response, error) => {
            if (response.exportDataset) {
              this._jobStatus(response.exportDataset.jobKey);
            } else {
              console.log(error);

              setExportingState(false);

              setErrorMessage(owner, name, 'Export Failed', error);
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
  _toggleDeleteModal = () => {
    this.setState((state) => {
      const deleteModalVisible = !state.deleteModalVisible;
      return {
        deleteModalVisible,
      };
    });
  }

  /**
  *  @param {}
  *  sets menu
  *  @return {}
  */
  _mergeFilter = () => {
    const { toggleBranchesView } = this.props;
    if (store.getState().containerStatus.status !== 'Running') {
      toggleBranchesView(true, true);

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
  _switchBranch = () => {
    const { toggleBranchesView } = this.props;
    const { status } = store.getState().containerStatus;

    if (status !== 'Running') {
      window.scrollTo(0, 0);

      toggleBranchesView(true, false);

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
  _handleToggleModal = (modal) => {
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
  _resetState = () => {
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
  _resetPublishState = (publishDisabled) => {
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
  _setRemoteSession = () => {
    const { owner, name } = this.props;
    this.setState({
      addedRemoteThisSession: true,
      remoteUrl: `https://gigantum.com/${owner}/${name}`,
    });
  }


  render() {
    const {
      name,
      owner,
      sectionType,
      defaultRemote,
      history,
      auth,
      visibility,
      description,
      isLocked,
    } = this.props;
    const {
      menuOpen,
      showLoginPrompt,
      deleteModalVisible,
      visibilityModalVisible,
      remoteUrl,
      justOpened,
      exporting,
    } = this.state;
    const deleteText = (sectionType === 'labbook') ? 'Delete Project' : 'Delete Dataset';
    // declare css here
    const branchMenuCSS = classNames({
      'ActionsMenu__menu--animation': justOpened, // this is needed to stop animation from breaking position flow when collaborators modal is open
      hidden: !menuOpen,
      'ActionsMenu__menu box-shadow': true,
    });

    return (
      <div className="ActionsMenu flex flex--column'">

        { showLoginPrompt
          && (
            <LoginPrompt closeModal={this._closeLoginPromptModal} />
          )
        }

        { (deleteModalVisible && (sectionType === 'labbook'))
          && (
            <DeleteLabbook
              handleClose={() => this._toggleDeleteModal()}
              remoteAdded={defaultRemote}
              history={history}
              name={name}
              owner={owner}
              remoteDelete={false}
            />
          )
        }

        { (deleteModalVisible && (sectionType === 'dataset'))
          && (
            <DeleteDataset
              handleClose={() => this._toggleDeleteModal()}
              remoteAdded={defaultRemote}
              history={history}
              name={name}
              owner={owner}
            />
          )
        }

        { visibilityModalVisible
          && (
          <VisibilityModal
            sectionType={sectionType}
            owner={owner}
            name={name}
            auth={auth}
            toggleModal={this._toggleModal}
            buttonText="Save"
            header="Change Visibility"
            modalStateValue="visibilityModalVisible"
            checkSessionIsValid={this._checkSessionIsValid}
            resetState={this._resetState}
            visibility={visibility}
          />
          )
        }

        <CreateBranch
          description={description}
          modalVisible={this.state.createBranchVisible}
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
                onClick={evt => this._exportLabbook(evt)}
                disabled={exporting || isLocked}
                className="ActionsMenu__btn--flat"
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
                type="button"
              >
                {deleteText}
              </button>

            </li>

            { defaultRemote
              && (
              <li className={`ActionsMenu__item ActionsMenu__item--visibility-${visibility}`}>

                <button
                  onClick={() => this._toggleModal('visibilityModalVisible')}
                  className="ActionsMenu__btn--flat"
                  type="button"
                >
                  Change Visibility
                </button>

              </li>
              )
            }
            { (remoteUrl || defaultRemote)
              && (
              <li className="ActionsMenu__item ActionsMenu__item--copy">
                <div className="ActionsMenu__item--label">Get Share URL</div>
                <div className="ActionsMenu__copyRemote">

                  <input
                    id="ActionsMenu-copy"
                    className="ActionsMenu__input"
                    defaultValue={`gigantum.com/${owner}/${name}`}
                    type="text"
                  />

                  <button
                    onClick={() => this._copyRemote()}
                    className="ActionsMenu__btn--copy fa fa-clone"
                    type="button"
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

const mapStateToProps = state => state.packageDependencies;

const mapDispatchToProps = () => ({
  setContainerMenuWarningMessage,
});

export default connect(mapStateToProps, mapDispatchToProps)(ActionsMenu);
