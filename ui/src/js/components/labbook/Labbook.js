// vendor
import React, { Component, Fragment } from 'react';
import { Route, Switch } from 'react-router-dom';
import {
  createRefetchContainer,
  graphql,
} from 'react-relay';
import { DragDropContext } from 'react-dnd';
import HTML5Backend from 'react-dnd-html5-backend';
import classNames from 'classnames';
import { connect } from 'react-redux';
// store
import store from 'JS/redux/store';
import { setContainerMenuWarningMessage } from 'JS/redux/actions/labbook/environment/environment';
import {
  setMergeMode,
  setBuildingState,
  setStickyDate,
  updateTransitionState,
} from 'JS/redux/actions/labbook/labbook';
import { setCallbackRoute } from 'JS/redux/actions/routes';
import { setInfoMessage } from 'JS/redux/actions/footer';
// utils
import { getFilesFromDragEvent } from 'JS/utils/html-dir-content';
import BranchMutations from 'Components/shared/utils/BranchMutations';
// config
import Config from 'JS/config';
// mutations
import LabbookContainerStatusMutation from 'Mutations/LabbookContainerStatusMutation';
import LabbookLookupMutation from 'Mutations/LabbookLookupMutation';
import MigrateProjectMutation from 'Mutations/MigrateProjectMutation';
// components
import Loader from 'Components/common/Loader';
import Login from 'Components/login/Login';
import ErrorBoundary from 'Components/common/ErrorBoundary';
import Header from 'Components/shared/header/Header';
import ButtonLoader from 'Components/common/ButtonLoader';
import Modal from 'Components/common/Modal';
import Activity from './activity/LabbookActivityContainer';
import Overview from './overview/LabbookOverviewContainer';
import Environment from './environment/Environment';
import Code from './code/Code';
import InputData from './inputData/Input';
import OutputData from './outputData/Output';
// query
import fetchMigrationInfoQuery from './queries/fetchMigrationInfoQuery';
// assets
import './Labbook.scss';

let count = 0;
const containerStatusList = [];

/**
  scrolls to top of window
*/
const scrollToTop = () => {
  window.scrollTo(0, 0);
};

/**
   @param {Object} props
   determines if project is locked
   @return {Boolean}
  */
const determineIsLocked = (props) => {
  const {
    labbook,
    isBuilding,
    isSyncing,
    isPublishing,
    isUploading,
    globalIsUploading,
  } = props;

  return (
    (labbook.environment.containerStatus !== 'NOT_RUNNING')
    || (labbook.environment.imageStatus === 'BUILD_IN_PROGRESS')
    || (labbook.environment.imageStatus === 'BUILD_QUEUED')
    || isBuilding
    || isSyncing
    || isPublishing
    || isUploading
    || globalIsUploading
  );
};


type Props = {
  auth: {
    isAuthenticated: Function,
  },
  diskLow: boolean,
  labbook: {
    activeBranchName: string,
    branches: Array<Object>,
    canManageCollaborators: boolean,
    collaborators: Array<Object>,
    id: string,
    name: string,
    owner: string,
  },
  location: {
    pathname: string,
  },
  relay: {
    refetch: Function,
  },
}

class Labbook extends Component<Props> {
  state = {
    isLocked: determineIsLocked(this.props),
    collaborators: this.props.labbook.collaborators,
    canManageCollaborators: this.props.labbook.canManageCollaborators,
    branches: this.props.labbook.branches,
    deletedBranches: [],
    migrationInProgress: false,
    migrateComplete: false,
    branchMutations: new BranchMutations({
      parentId: this.props.labbook.id,
      name: this.props.labbook.name,
      owner: this.props.labbook.owner,
    }),
    isDeprecated: null,
    shouldMigrate: null,
    buttonState: '',
    packageLatestVersions: [],
    isFetchingPackages: false,
    queuePackageFetch: false,
    activeBranchName: this.props.labbook.activeBranchName,
    overviewSkip: true,
    activitySkip: true,
    environmentSkip: true,
    codeSkip: true,
    inputSkip: true,
    outputSkip: true,
    lockFileBrowser: false,
    packageRefetchRan: false,
  }

  static getDerivedStateFromProps(nextProps, state) {
    setCallbackRoute(nextProps.location.pathname);
    const propBranches = nextProps.labbook && nextProps.labbook.branches
      ? nextProps.labbook.branches
      : [];
    const stateBranches = state.branches || [];
    const branchMap = new Map();
    const mergedBranches = [];
    const newDeletedBranches = state.deletedBranches.slice();
    const { isPublishing, isUploading, transitionState } = nextProps;

    propBranches.forEach((branch) => {
      if (newDeletedBranches.indexOf(branch.id) === -1) {
        branchMap.set(branch.id, branch);
      }
    });
    stateBranches.forEach((branch) => {
      if (branchMap.has(branch.id)) {
        const itemReference = branchMap.get(branch.id);
        const newItem = Object.assign({}, branch, itemReference);
        branchMap.set(branch.id, newItem);
      } else {
        newDeletedBranches.push(branch.id);
      }
    });

    branchMap.forEach((branch) => {
      mergedBranches.push(branch);
    });
    const isLocked = (nextProps.labbook
      && nextProps.labbook.environment.containerStatus !== 'NOT_RUNNING')
      || (nextProps.labbook.environment.imageStatus === 'BUILD_IN_PROGRESS')
      || (nextProps.labbook.environment.imageStatus === 'BUILD_QUEUED')
      || nextProps.isBuilding
      || nextProps.isSyncing
      || isPublishing
      || isUploading
      || nextProps.globalIsUploading
      || (transitionState === 'Starting')
      || (transitionState === 'Exporting');

    const canManageCollaborators = nextProps.labbook
      ? nextProps.labbook.canManageCollaborators
      : false;
    const collaborators = nextProps.labbook
      ? nextProps.labbook.collaborators
      : [];

    const lockFileBrowser = nextProps.isSyncing
      || nextProps.globalIsUploading
      || isPublishing
      || nextProps.isExporting;
    return {
      ...state,
      deletedBranches: newDeletedBranches,
      branches: mergedBranches,
      canManageCollaborators,
      collaborators,
      isLocked,
      lockFileBrowser,
    };
  }

  /**
    @param {}
    subscribe to store to update state
    set unsubcribe for store
  */
  componentDidMount() {
    const { props, state } = this;
    const { name, owner } = props.labbook;

    localStorage.setItem('owner', owner);
    setCallbackRoute(props.location.pathname);

    this.mounted = true;
    document.title = `${owner}/${name}`;

    props.auth.isAuthenticated().then((response) => {
      let isAuthenticated = response;
      if (isAuthenticated === null) {
        isAuthenticated = false;
      }
      if ((isAuthenticated !== state.authenticated) && this.mounted) {
        this.setState({ authenticated: isAuthenticated });
      }
    });

    this._fetchMigrationInfo();

    this._setStickHeader();
    this._fetchStatus(true);

    window.addEventListener('scroll', this._setStickHeader);
    window.addEventListener('click', this._branchViewClickedOff);
  }

  componentDidUpdate() {
    const { props, state } = this;
    const { activeBranchName } = props.labbook;
    // TODO do not set state in componenetDidUpdate
    if (activeBranchName !== state.activeBranchName) {
      this.setState({ activeBranchName });
    }
  }

  /**
    @param {}
    removes event listeners
  */
  componentWillUnmount() {
    this.mounted = false;

    window.removeEventListener('scroll', this._setStickHeader);
    window.removeEventListener('click', this._branchViewClickedOff);
  }

  /**
  @param {}
  cancels refetch packages
  */
  _cancelRefetch = () => {
    if (this.refetch && this.refetch.dispose) {
      this.refetch.dispose();
    }
  }

  /**
   @param {}
   refetch packages
   */
  _packageLatestRefetch = () => {
    const { props, state } = this;
    const queryVariables = {
      labbookID: props.labbook.id,
      skipPackages: false,
      environmentSkip: false,
      first: 1000,
    };
    const renderVariables = {
      labbookID: props.labbook.id,
      overviewSkip: false,
      activitySkip: false,
      environmentSkip: false,
      inputSkip: false,
      outputSkip: false,
      codeSkip: false,
      labbookSkip: false,
      skipPackages: false,
    };
    const options = {
      force: true,
    };
    if (!state.packageRefetchRan) {
      this.refetch = props.relay.refetch(queryVariables, renderVariables, () => {
        this.setState({ packageRefetchRan: true });
      }, options);
    }
  }

  /**
   @param {String} section
   refetch labbook
   */
  _refetchSection = (section) => {
    const { props, state } = this;
    const currentSection = `${section}Skip`;
    const currentState = {
      overviewSkip: state.overviewSkip,
      activitySkip: state.activitySkip,
      environmentSkip: state.environmentSkip,
      inputSkip: state.inputSkip,
      outputSkip: state.outputSkip,
      codeSkip: state.codeSkip,
    };
    const sections = ['overview', 'activity', 'environment', 'input', 'output', 'code'];
    const queryVariables = {
      labbookID: props.labbook.id,
      [currentSection]: false,
    };
    const renderVariables = {
      labbookID: props.labbook.id,
      ...currentState,
      [currentSection]: false,
      skipPackages: false,
    };
    const remainingQueryVariables = {
      labbookID: props.labbook.id,
      labbookSkip: false,
    };
    const remainingRenderVariables = {
      labbookID: props.labbook.id,
      labbookSkip: false,
      skipPackages: false,
    };
    const newState = {
      labbookSkip: true,
    };
    const options = {
      force: true,
    };

    sections.forEach((fragmentSection) => {
      const remainingSection = `${fragmentSection}Skip`;
      if (fragmentSection !== section) {
        remainingQueryVariables[remainingSection] = false;
        newState[remainingSection] = false;
      }
      remainingRenderVariables[remainingSection] = false;
    });

    const refetchCallback = () => {
      this.setState({ [currentSection]: false });
      props.relay.refetch(
        remainingQueryVariables,
        remainingRenderVariables,
        () => {
          this.setState(newState);
        },
        options,
      );
    };


    if (state[currentSection]) {
      props.relay.refetch(queryVariables, renderVariables, refetchCallback, options);
    }
  }

  /**
   * @param {}
   * checks if project is deprecated and should migrate and sets state
  */
  _fetchMigrationInfo = () => {
    const { props } = this;
    const { owner, name } = props.labbook;
    const self = this;

    fetchMigrationInfoQuery.getLabook(owner, name).then((response) => {
      if (response.labbook) {
        const {
          isDeprecated,
          shouldMigrate,
        } = response.labbook;
        self.setState({
          isDeprecated,
          shouldMigrate,
        });
      }
    });
  }

  /**
  *  @param {object} - response
  *  update state from switch mutation
  *  @return {}
  */
  _updateMigationState = (response) => {
    if (response && response.workonExperimentalBranch) {
      const { isDeprecated, shouldMigrate } = response.workonExperimentalBranch.labbook;
      this.setState({
        isDeprecated,
        shouldMigrate,
      });
    }
  }

  /**
  *  @param {} -
  *  fetches status of labbook container and image
  *  sets state of labbook using redux and containerStatus using setState
  *  @return {}
  */
  _fetchStatus = (isLabbookUpdate) => {
    const { props } = this;
    const { owner, name } = props.labbook;
    const self = this;
    const { isBuilding } = props;


    if (this.mounted) {
      if (!isLabbookUpdate) {
        LabbookContainerStatusMutation(owner, name, (error, response) => {
          if (response && response.fetchLabbookEdge && response.fetchLabbookEdge.newLabbookEdge) {
            const { environment } = response.fetchLabbookEdge.newLabbookEdge.node;
            containerStatusList.push(environment.imageStatus);
            const containerStatusLength = containerStatusList.length;
            const previousImageStatus = containerStatusList[containerStatusLength - 2];
            if (((previousImageStatus !== 'BUILD_IN_PROGRESS') || (previousImageStatus !== 'BUILD_FAILED'))
              && ((environment.imageStatus === 'EXISTS') || (environment.imageStatus === 'BUILD_FAILED'))
              && isBuilding) {
              setBuildingState(owner, name, false);
            }
            if ((previousImageStatus !== 'NOT_RUNNING')
              && (environment.containerStatus === 'RUNNING')) {
              updateTransitionState(owner, name, '');
            }
          }
          setTimeout(() => {
            const canLabbookUpdate = (count === 20);
            self._fetchStatus(canLabbookUpdate);
            count = canLabbookUpdate ? 0 : (count + 1);
          }, 3 * 1000);
        });
      } else {
        LabbookLookupMutation(owner, name, (error, response) => {
          if (response && response.fetchLabbookEdge && response.fetchLabbookEdge.newLabbookEdge) {
            const {
              branches,
              collaborators,
              canManageCollaborators,
            } = response.fetchLabbookEdge.newLabbookEdge.node;
            self.setState({
              branches,
              collaborators,
              canManageCollaborators,
            });
          }
          setTimeout(() => {
            const canLabbookUpdate = (count === 20);
            self._fetchStatus(canLabbookUpdate);
            count = canLabbookUpdate ? 0 : (count + 1);
          }, 3 * 1000);
        });
      }
    }
  }

  /**
    @param {event}
    updates state of labbook when prompted ot by the store
    updates history prop
  */
  _branchViewClickedOff = (evt) => {
    if (evt.target.className.indexOf('Labbook__veil') > -1) {
      this._toggleBranchesView(false, false);
    }
  }

  /**
    sets branch uptodate in state
  */
  _setBranchUptodate = () => {
    const { branches } = this.state;
    const activePosition = branches.map(branch => branch.isActive).indexOf(true);
    const branchesClone = branches.slice();
    branchesClone[activePosition].commitsBehind = 0;
    branchesClone[activePosition].commitsAhead = 0;
    this.setState({ branches: branchesClone });
  }

  /**
    migrates project
  */
  _migrateProject = () => {
    const { props, state } = this;
    const { owner, name } = props.labbook;

    this.setState({ buttonState: 'loading' });
    MigrateProjectMutation(owner, name, (response, error) => {
      if (error) {
        console.log(error);
        this.setState({ buttonState: 'error' });
        setTimeout(() => {
          this.setState({ buttonState: '' });
        }, 2000);
      } else {
        this.setState({
          isDeprecated: false,
          shouldMigrate: false,
        });
        const oldBranches = props.labbook.branches.filter((branch => branch.branchName.startsWith('gm.workspace')));
        oldBranches.forEach(({ branchName }, index) => {
          const data = {
            branchName,
            deleteLocal: true,
            deleteRemote: true,
          };

          state.branchMutations.deleteBranch(data, (deleteResponse, delteError) => {
            if (delteError) {
              this.setState({ buttonState: 'error' });

              setTimeout(() => {
                this.setState({ buttonState: '' });
              }, 2000);
            }

            if (index === oldBranches.length - 1) {
              this.setState({
                migrateComplete: true,
                buttonState: 'finished',
              });
              setInfoMessage(owner, name, 'Project migrated successfully');
              setTimeout(() => {
                this.setState({ buttonState: '' });
              }, 2000);
            }
          });
        });
      }
    });
  }

  /**
    @param {}
    dispatches sticky state to redux to update state
  */
  _setStickHeader = () => {
    const { props } = this;
    const { owner, name } = props[props.sectionType];
    const sticky = 50;
    const isSticky = window.pageYOffset >= sticky;

    this.offsetDistance = window.pageYOffset;
    if (props.isSticky !== isSticky) {
      setStickyDate(owner, name, isSticky);
    }

    if (isSticky) {
      setMergeMode(owner, name, false, false);
    }
  }

  /**
    @param {boolean} branchesOpen
    @param {boolean} mergeFilter
    updates branchOpen state
  */
  _toggleBranchesView = (branchesOpen, mergeFilter) => {
    const { props } = this;
    const { owner, name } = props[props.sectionType];
    if (store.getState().containerStatus.status !== 'Running') {
      setMergeMode(owner, name, branchesOpen, mergeFilter);
    } else {
      setContainerMenuWarningMessage('Stop Project before switching branches. \n Be sure to save your changes.');
    }
  }

  /**
    @param {}
    updates branchOpen state
  */
  _toggleMigrationModal = () => {
    this.setState((state) => {
      const migrationModalVisible = !state.migrationModalVisible;
      return { migrationModalVisible };
    });
  }

  /**
    scrolls to top of window
    @return {boolean, string}
  */
  _getMigrationInfo = () => {
    const { props, state } = this;
    const isOwner = (localStorage.getItem('username') === props.labbook.owner);
    const {
      isDeprecated,
      shouldMigrate,
    } = state;
    const isPublished = typeof props.labbook.defaultRemote === 'string';

    let migrationText = '';
    let showMigrationButton = false;

    if ((isOwner && isDeprecated && shouldMigrate && isPublished)
        || (isDeprecated && !isPublished && shouldMigrate)) {
      migrationText = 'This Project needs to be migrated to the latest Project format';
      showMigrationButton = true;
    } else if (!isOwner && isDeprecated && shouldMigrate && isPublished) {
      migrationText = 'This Project needs to be migrated to the latest Project format. The project owner must migrate and sync this project to update.';
    } else if ((isDeprecated && !isPublished && !shouldMigrate)
      || (isDeprecated && isPublished && !shouldMigrate)) {
      migrationText = 'This project has been migrated. Master is the new primary branch. Old branches should be removed.';
    }

    return { showMigrationButton, migrationText };
  }

  // TODO move migration code into it's own component
  render() {
    const { props, state } = this;
    const { isBuilding, isPublishing, isSyncing } = props;
    const { owner, name } = props.labbook;
    const isLocked = isBuilding
      || isSyncing
      || isPublishing
      || state.isLocked;

    if (props.labbook) {
      const { labbook, branchesOpen } = props;
      const sidePanelVisible = !isLocked && props.sidePanelVisible;
      const branchName = '';
      const isDemo = (window.location.hostname === Config.demoHostName) || props.diskLow;
      const { migrationText, showMigrationButton } = this._getMigrationInfo();
      const oldBranches = labbook.branches.filter((branch => branch.branchName.startsWith('gm.workspace') && branch.branchName !== labbook.activeBranchName));
      const migrationModalType = state.migrateComplete ? 'large' : 'large-long';
      const { containerStatus } = props.labbook.environment;
      const labbookCSS = classNames({
        Labbook: true,
        'Labbook--detail-mode': props.detailMode,
        'Labbook--branch-mode': branchesOpen,
        'Labbook--demo-mode': isDemo,
        'Labbook--deprecated': state.isDeprecated,
        'Labbook--demo-deprecated': state.isDeprecated && isDemo,
        'Labbook--sidePanelVisible': sidePanelVisible,
        'Labbook--locked': state.isLocked,
      });
      const deprecatedCSS = classNames({
        Labbook__deprecated: true,
        'Labbook__deprecated--demo': isDemo,
      });
      const migrationButtonCSS = classNames({
        'Tooltip-data': state.isLocked,
      });

      return (
        <div className={labbookCSS}>
          <div id="labbook__cover" className="Labbook__cover hidden">
            <Loader />
          </div>
          <div className="Labbook__spacer flex flex--column">
            { state.isDeprecated
              && (
              <div className={deprecatedCSS}>
                {migrationText}
                <a
                  target="_blank"
                  href="https://docs.gigantum.com/docs/project-migration"
                  rel="noopener noreferrer"
                >
                  Learn More.
                </a>
                {
                  showMigrationButton
                  && (
                  <div
                    className={migrationButtonCSS}
                    data-tooltip="To migrate the project container must be Stopped."
                  >
                    <button
                      className="Button Labbook__deprecated-action"
                      onClick={() => this._toggleMigrationModal()}
                      disabled={state.migrationInProgress || state.isLocked}
                      type="button"
                    >
                    Migrate
                    </button>
                  </div>
                  )
                }
              </div>
              )
            }
            {
              (state.migrationModalVisible)
              && (
              <Modal
                header="Project Migration"
                handleClose={() => this._toggleMigrationModal()}
                size={migrationModalType}
                renderContent={() => (
                  <div className="Labbook__migration-modal">
                    {
                    !state.migrateComplete
                      ? (
                        <div className="Labbook__migration-container">
                          <div className="Labbook__migration-content">
                            <p className="Labbook__migration-p"><b>Migration will rename the current branch to 'master' and delete all other branches.</b></p>
                            <p>Before migrating, you should:</p>
                            <ul>
                              <li>
                          Make sure you are on the branch with your latest changes. This is most likely
                                <b style={{ whiteSpace: 'nowrap' }}>
                                  {` gm.workspace-${localStorage.getItem('username')}`}
                                </b>
                          . If you just imported this project from a zip file, you should migrate from
                                <b style={{ whiteSpace: 'nowrap' }}> gm.workspace</b>
                          .
                              </li>
                              <li>Export the project to a zip file as a backup, if desired.</li>
                            </ul>
                            <p>
                              <b>
                          Branch to be migrated:
                              </b>
                              {` ${labbook.activeBranchName}`}
                            </p>
                            <b>Branches to be deleted:</b>
                            {
                        oldBranches.length
                          ? (
                            <ul>
                              {
                            oldBranches.map(({ branchname }) => (
                              <li key={branchname}>{branchname}</li>
                            ))
                          }
                            </ul>
                          )
                          : (
                            <ul>
                              <li>No other branches to delete.</li>
                            </ul>
                          )
                      }
                          </div>
                          <div className="Labbook__migration-buttons">
                            <button
                              onClick={() => this._toggleMigrationModal()}
                              className="Btn--flat"
                              type="button"
                            >
                            Cancel
                            </button>
                            <ButtonLoader
                              buttonState={this.state.buttonState}
                              buttonText="Migrate Project"
                              className=""
                              params={{}}
                              buttonDisabled={false}
                              clicked={() => this._migrateProject()}
                            />
                          </div>
                        </div>
                      )
                      : (
                        <div className="Labbook__migration-container">
                          <div className="Labbook__migration-content">
                            <div className="Labbook__migration-center">
                              {
                          labbook.defaultRemote
                            ? (
                              <Fragment>
                            You should now click
                                <b> sync </b>
                            to push the new
                                <b> master </b>
                            branch to the cloud. This is the new primary branch to work from.
                              </Fragment>
                            )
                            : (
                              <Fragment>
                            Your work has been migrated to the
                                <b> master </b>
                            branch. This is the new primary branch to work from.
                              </Fragment>
                            )
                          }
                              <a
                                target="_blank"
                                href="https://docs.gigantum.com/docs/project-migration"
                                rel="noopener noreferrer"
                              >
                                Learn More.
                              </a>
                              <p>Remember to notify collaborators that this project has been migrated. They may need to re-import the project.</p>
                            </div>
                            <div className="Labbook__migration-buttons">
                              <button
                                type="button"
                                className="Labbook__migration--dismiss"
                                onClick={() => this._toggleMigrationModal()}
                              >
                              Dismiss
                              </button>
                            </div>
                          </div>
                        </div>
                      )
                    }
                  </div>
                )
                }
              />
              )
            }
            <Header
              {...props}
              owner={owner}
              name={name}
              ref={header => header}
              description={labbook.description}
              toggleBranchesView={this._toggleBranchesView}
              sectionType="labbook"
              containerStatus={labbook.environment.containerStatus}
              imageStatus={labbook.environment.imageStatus}
              isLocked={isLocked}
              collaborators={state.collaborators}
              canManageCollaborators={state.canManageCollaborators}
              visibility={labbook.visibility}
              defaultRemote={labbook.defaultRemote}
              branches={state.branches}
              setBranchUptodate={this._setBranchUptodate}
              isDeprecated={state.isDeprecated}
              updateMigationState={this._updateMigationState}
              sidePanelVisible={sidePanelVisible}
              showMigrationButton={showMigrationButton}
            />
            <div className="Labbook__routes flex flex-1-0-auto">
              <Switch>
                <Route
                  exact
                  path={`${props.match.path}`}
                  render={() => (
                    <ErrorBoundary type="labbookSectionError">
                      <Overview
                        {...props}
                        key={`${props.labbookName}_overview`}
                        labbook={labbook}
                        labbookId={labbook.id}
                        refetch={this._refetchSection}
                        isPublishing={isPublishing}
                        scrollToTop={scrollToTop}
                        sectionType="labbook"
                        owner={owner}
                        name={name}
                      />
                    </ErrorBoundary>
                  )}
                />

                <Route path={`${props.match.path}/:labbookMenu`}>

                  <Switch>

                    <Route
                      path={`${props.match.path}/overview`}
                      render={() => (

                        <ErrorBoundary
                          type="labbookSectionError"
                          key="overview"
                        >
                          <Overview
                            {...props}
                            key={`${props.labbookName}_overview`}
                            labbook={labbook}
                            description={labbook.description}
                            labbookId={labbook.id}
                            refetch={this._refetchSection}
                            isPublishing={isPublishing}
                            scrollToTop={scrollToTop}
                            sectionType="labbook"
                            owner={owner}
                            name={name}
                          />
                        </ErrorBoundary>
                      )}
                    />

                    <Route
                      path={`${props.match.path}/activity`}
                      render={() => (
                        <ErrorBoundary
                          type="labbookSectionError"
                          key="activity"
                        >
                          <Activity
                            key={`${props.labbookName}_activity`}
                            labbook={labbook}
                            diskLow={props.diskLow}
                            refetch={this._refetchSection}
                            activityRecords={props.activityRecords}
                            labbookId={labbook.id}
                            branchName={branchName}
                            description={labbook.description}
                            activeBranch={labbook.activeBranchName}
                            isMainWorkspace={branchName === 'master'}
                            sectionType="labbook"
                            isLocked={isLocked}
                            isDeprecated={state.isDeprecated}
                            owner={owner}
                            name={name}
                            {...props}
                          />
                        </ErrorBoundary>
                      )}
                    />

                    <Route
                      path={`${props.match.url}/environment`}
                      render={() => (
                        <ErrorBoundary
                          type="labbookSectionError"
                          key="environment"
                        >
                          <Environment
                            key={`${props.labbookName}_environment`}
                            labbook={labbook}
                            owner={owner}
                            name={name}
                            labbookId={labbook.id}
                            refetch={this._refetchSection}
                            overview={labbook.overview}
                            isLocked={isLocked}
                            packageLatestVersions={state.packageLatestVersions}
                            packageLatestRefetch={this._packageLatestRefetch}
                            cancelRefetch={this._cancelRefetch}
                            {...props}
                          />
                        </ErrorBoundary>
                      )}
                    />

                    <Route
                      path={`${props.match.url}/code`}
                      render={() => (
                        <ErrorBoundary
                          type="labbookSectionError"
                          key="code"
                        >
                          <Code
                            labbook={labbook}
                            labbookId={labbook.id}
                            refetch={this._refetchSection}
                            setContainerState={this._setContainerState}
                            isLocked={isLocked}
                            containerStatus={containerStatus}
                            section="code"
                            lockFileBrowser={state.lockFileBrowser}
                            owner={labbook.owner}
                            name={labbook.name}
                          />

                        </ErrorBoundary>
                      )}
                    />

                    <Route
                      path={`${props.match.url}/inputData`}
                      render={() => (
                        <ErrorBoundary
                          type="labbookSectionError"
                          key="input"
                        >
                          <InputData
                            labbook={labbook}
                            labbookId={labbook.id}
                            isLocked={isLocked}
                            refetch={this._refetchSection}
                            containerStatus={containerStatus}
                            lockFileBrowser={state.lockFileBrowser}
                            owner={labbook.owner}
                            name={labbook.name}
                            section="input"
                          />
                        </ErrorBoundary>
                      )}
                    />

                    <Route
                      path={`${props.match.url}/outputData`}
                      render={() => (
                        <ErrorBoundary
                          type="labbookSectionError"
                          key="output"
                        >
                          <OutputData
                            labbook={labbook}
                            labbookId={labbook.id}
                            isLocked={isLocked}
                            refetch={this._refetchSection}
                            containerStatus={containerStatus}
                            lockFileBrowser={state.lockFileBrowser}
                            owner={labbook.owner}
                            name={labbook.name}
                            section="output"
                          />
                        </ErrorBoundary>
                      )}
                    />

                  </Switch>

                </Route>

              </Switch>

            </div>

          </div>
          <div className="Labbook__veil" />
        </div>
      );
    }

    if (state.authenticated) {
      return (<Loader />);
    }

    return (<Login auth={props.auth} />);
  }
}

const mapStateToProps = (state, props) => {
  const { owner, name } = props.labbook;
  const namespace = `${owner}_${name}`;
  const namespaceState = state.labbook[namespace]
    ? state.labbook[namespace]
    : state.labbook;

  const { isUploading } = state.labbook;
  return {
    ...namespaceState,
    globalIsUploading: isUploading,
    owner,
    name,
  };
};

const mapDispatchToProps = () => ({ setBuildingState });

const LabbookContainer = connect(mapStateToProps, mapDispatchToProps)(Labbook);


const LabbookFragmentContainer = createRefetchContainer(
  LabbookContainer,
  {
    labbook: graphql`
      fragment Labbook_labbook on Labbook {
          id
          description
          defaultRemote
          owner
          name
          visibility @skip(if: $labbookSkip)
          activeBranchName

          environment{
            containerStatus
            imageStatus
            base{
              developmentTools
            }
          }

         branches {
           id
           owner
           name
           branchName
           isActive
           isLocal
           isRemote
         }
          ...Environment_labbook
          ...LabbookOverviewContainer_labbook
          ...LabbookActivityContainer_labbook
          ...Code_labbook
          ...Input_labbook
          ...Output_labbook

      }`,
  },
  graphql`
  query LabbookRefetchQuery($first: Int!, $cursor: String, $skipPackages: Boolean!, $labbookID: ID!, $environmentSkip: Boolean!, $overviewSkip: Boolean!, $activitySkip: Boolean!, $codeSkip: Boolean!, $inputSkip: Boolean!, $outputSkip: Boolean!, $labbookSkip: Boolean!){
    labbook: node(id: $labbookID){
      ... on Labbook {
        visibility @skip(if: $labbookSkip)
      }
      ...Environment_labbook
      ...LabbookOverviewContainer_labbook
      ...LabbookActivityContainer_labbook
      ...Code_labbook
      ...Input_labbook
      ...Output_labbook
    }
  }
  `,
);

/** *
  * @param {Object} manager
  * data object for reactDND
*/

const backend = (manager) => {
  const backend = HTML5Backend(manager);
  const orgTopDropCapture = backend.handleTopDropCapture;

  backend.handleTopDropCapture = (e) => {
    if (backend.currentNativeSource) {
      orgTopDropCapture.call(backend, e);
      backend.currentNativeSource.item.dirContent = getFilesFromDragEvent(e, { recursive: true }); // returns a promise
    }
  };

  return backend;
};

export default DragDropContext(backend)(LabbookFragmentContainer);
