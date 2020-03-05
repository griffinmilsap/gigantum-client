// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import { connect } from 'react-redux';
import uuidv4 from 'uuid/v4';
// store
import {
  setErrorMessage,
  setWarningMessage,
  setMultiInfoMessage,
} from 'JS/redux/actions/footer';
import { setSidepanelVisible } from 'JS/redux/actions/labbook/labbook';
// queries
import UserIdentity from 'JS/Auth/UserIdentity';
import LinkedLocalDatasetsQuery from 'Components/shared/header/actionsSection/queries/LinkedLocalDatasetsQuery';
// componenets
import CreateBranch from 'Components/shared/modals/CreateBranch';
import ForceSync from 'Components/shared/modals/ForceSync';
import Branches from 'Components/shared/sidePanel/Branches';
import VisibilityModal from 'Components/shared/modals/VisibilityModal';
import PublishDatasetsModal from 'Components/shared/modals/publishDataset/PublishDatasetsModal';
import LoginPrompt from 'Components/shared/modals/LoginPrompt';
// utils
import BranchMutations from '../../utils/BranchMutations';
// assets
import './BranchMenu.scss';


/**
  @param {Array} branches
  filters array branhces and return the active branch node
  @return {Object} activeBranch
*/
const extraxtActiveBranch = (branches) => {
  const activeBranch = branches.filter(branch => branch.isActive)[0] || {};
  const filteredBranches = branches.filter(branch => !branch.isActive);
  const branchMenuList = (filteredBranches.length > 3)
    ? filteredBranches.slice(0, 3) : filteredBranches;
  const otherBranchCount = filteredBranches.length - branchMenuList.length;

  return ({
    activeBranch,
    filteredBranches,
    branchMenuList,
    otherBranchCount,
  });
};

/**
  @param {Object} props
  @param {Object} data
  Gets sync tooltip
  @return {String}
*/
const getSyncTooltip = (props, data) => {
  const {
    hasWriteAccess,
    syncOrPublish,
    sectionCollabs,
    activeBranch,
  } = data;
  let syncTooltip = !hasWriteAccess ? 'Pull changes from Gignatum Hub' : 'Sync changes to Gigantum Hub';
  syncTooltip = !props.defaultRemote ? 'Click Publish to push branch to Gigantum Hub' : syncTooltip;
  syncTooltip = props.isLocked ? `Cannot ${syncOrPublish} while Project is in use` : syncTooltip;
  syncTooltip = (activeBranch.branchName !== 'master' && !props.defaultRemote) ? 'Must publish Master branch first' : syncTooltip;
  syncTooltip = props.defaultRemote && !sectionCollabs ? 'Please wait while Project data is being fetched' : syncTooltip;

  return syncTooltip;
};

/**
  @param {Object} props
  @param {Object} data
  Gets managed tooltip
  @return {String}
*/
const getManagedToolip = (props, data) => {
  const { state, defaultDatasetMessage } = data;
  let managedTooltip = props.isLocked ? 'Cannot Manage Branches while Project is in use' : 'Manage Branches';
  managedTooltip = state.isDataset ? defaultDatasetMessage : 'Manage Branches';

  return managedTooltip;
};


/**
  @param {Object} result
  @param {Object} data
  Gets managed tooltip
  @return {String}
*/
const getLocalDatasets = (result) => {
  const { data } = result;
  let localDataset = [];

  if (data && data.labbook) {
    const { linkedDatasets } = data.labbook;
    localDataset = linkedDatasets.filter((linkedDataset) => {
      const { defaultRemote } = linkedDataset;
      return (defaultRemote && (defaultRemote.slice(0, 4) !== 'http'));
    });
  }

  return localDataset;
};


/**
*  @param {Object} - activeBranch
*  determines whether or not user has write access
*  @return {}
*/
const checkForWriteAccess = (activeBranch, defaultRemote, collaborators, sectionName) => {
  const username = localStorage.getItem('username');

  if (!defaultRemote) {
    return true;
  }

  if (!collaborators
    || (collaborators && !collaborators[sectionName])) {
    return false;
  }
  const collaboratorsSection = collaborators[sectionName];
  const filteredArr = collaboratorsSection.filter(collaborator => collaborator.collaboratorUsername === username);

  if (filteredArr.length === 0) {
    return false;
  } if ((filteredArr[0].permission === 'READ_ONLY')
    || ((filteredArr[0].permission === 'READ_WRITE')
    && (activeBranch.branchName === 'master'))) {
    return false;
  }
  return true;
};


type Props = {
  auth: {
    renewToken: Function,
  },
  branches: string,
  collaborators: Object,
  defaultRemote: string,
  isExporting: boolean,
  isLocked: boolean,
  isSticky: boolean,
  name: string,
  owner: string,
  sectionId: string,
  section: {
    name: string,
    owner: string,
    description: string,
  },
  sectionType: string,
  setBranchUptodate: Function,
  setSyncingState: Function,
  setPublishingState: Function,
  updateMigationState: Function,
};

class BranchMenu extends Component<Props> {
  state = {
    switchMenuVisible: false,
    createBranchVisible: false,
    branchMutations: new BranchMutations({
      parentId: this.props.sectionId,
      name: this.props.section.name,
      owner: this.props.section.owner,
    }),
    switchingBranch: false,
    forceSyncModalVisible: false,
    publishModalVisible: false,
    publishDatasetsModalVisible: false,
    publishDatasetsModalAction: 'Publish',
    syncMenuVisible: false,
    showLoginPrompt: false,
    isDataset: (this.props.sectionType !== 'labbook'),
    action: null,
  };

  componentDidMount() {
    window.addEventListener('click', this._closePopups);
  }

  componentWillUnmount() {
    window.removeEventListener('click', this._closePopups);
  }

  /**
  *  @param {}
  *  returns UserIdentityQeury promise
  *  @return {promise}
  */
  _checkSessionIsValid = () => (UserIdentity.getUserIdentity())

  /**
    @param {}
    calls reset branch on activebranch
  */
  _resetBranch = () => {
    const { setBranchUptodate, section } = this.props;
    const { owner, name } = section;
    this._toggleCover('Resetting Branch');
    this.state.branchMutations.resetBranch((response, error) => {
      if (error) {
        setErrorMessage(owner, name, 'Failed to reset branch.', error);
      }
      this._toggleCover(null);
      setBranchUptodate();
    });
    this.setState({ popupVisible: false });
  }

  /**
  *  @param {Array} branches
  *  filters array branhces and return the active branch node
  *  @return {Object} activeBranch
  */
  _setModalState = (key) => {
    const { state } = this;
    const { isLocked } = this.props;

    const value = !state[key];
    if (!isLocked && !state.isDataset) {
      this.setState({ [key]: value });
    }
  }

  /**
    @param {String} action
    handles labbook cover toggle
    @return {}
  */
  _toggleCover = (action) => {
    // TODO don't use getElementById to set classNames
    if (action) {
      this.setState({ action });
      if (document.getElementById('labbook__cover')) {
        document.getElementById('labbook__cover').classList.remove('hidden');
      }
    } else {
      this.setState({ action: false });
      if (document.getElementById('labbook__cover')) {
        document.getElementById('labbook__cover').classList.add('hidden');
      }
    }
  }

  /**
    @param {Array} branches
    filters array branhces and return the active branch node
    @return {Object} activeBranch
  */
  _switchBranch = (branch) => {
    const { branchMutations } = this.state;
    const { section, updateMigationState } = this.props;
    const { owner, name } = section;
    const self = this;
    const data = {
      branchName: branch.branchName,
    };

    this.setState({
      switchingBranch: branch.branchName,
      switchMenuVisible: false,
    });

    this._toggleCover('Switching Branches');

    branchMutations.switchBranch(data, (response, error) => {
      if (error) {
        setErrorMessage(owner, name, 'Failed to switch branches.', error);
      }
      self.setState({ switchingBranch: false });
      updateMigationState(response);

      branchMutations.buildImage((response, error) => {
        setTimeout(() => {
          this._toggleCover(null);
        }, 3000);
        if (error) {
          setErrorMessage(owner, name, 'Failed to switch branches.', error);
        }
      });
    });
  }

  /**
  *  @param {Boolean} queryForLocalDatasets
  *  @param {Boolean} closePublishDatasetsModal
  *  adds remote url to labbook
  *  @return {string}
  */
  _togglePublishModal = (queryForLocalDatasets, closePublishDatasetsModal) => {
    const { isExporting, section } = this.props;

    if (isExporting) {
      const { owner, name } = section;
      setWarningMessage(owner, name, 'Publishing is currently only available on the main workspace branch.');
      this.setState({ publishWarningVisible: true });
    } else if (queryForLocalDatasets && (typeof queryForLocalDatasets === 'boolean')) {
      LinkedLocalDatasetsQuery.getLocalDatasets({
        owner: section.owner,
        name: section.name,
      }).then((res) => {
        const localDatasets = res.data && res.data.labbook.linkedDatasets.filter(linkedDataset => linkedDataset.defaultRemote && linkedDataset.defaultRemote.slice(0, 4) !== 'http');
        if (localDatasets.length === 0) {
          this.setState((state) => {
            const publishModalVisible = !state.publishModalVisible;
            return { publishModalVisible };
          });
        } else {
          this.setState((state) => {
            const publishDatasetsModalVisible = !state.publishDatasetsModalVisible;
            return {
              localDatasets,
              publishDatasetsModalVisible,
              publishDatasetsModalAction: 'Publish',
            };
          });
        }
      });
    } else if (closePublishDatasetsModal) {
      this.setState((state) => {
        const publishDatasetsModalVisible = !state.publishDatasetsModalVisible;
        return { publishDatasetsModalVisible };
      });
    } else {
      this.setState((state) => {
        const publishModalVisible = !state.publishModalVisible;
        return { publishModalVisible };
      });
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
    @param {} -
    sets state to toggle the switch dropdown
    @return {}
  */
  _toggleBranchSwitch = () => {
    const { isLocked } = this.props;
    const { isDataset } = this.state;

    if (!isLocked && !isDataset) {
      this.setState((state) => {
        const switchMenuVisible = !state.switchMenuVisible;
        return { switchMenuVisible };
      });
    }
  }

  /**
    @param {} -
    sets state to toggle the switch dropdown
    @return {}
  */
  _closePopups = (evt) => {
    if (evt.target.className.indexOf('BranchMenu') < 0) {
      this.setState({
        switchMenuVisible: false,
      });
    }
    if (evt.target.className.indexOf('Btn--branch--sync-dropdown') < 0) {
      this.setState({
        syncMenuVisible: false,
      });
    }
  }

  /**
    @param {} -
    sets state to toggle the switch dropdown
    @return {}
  */
  _toggleSidePanel = (sidePanelVisible) => {
    const { props } = this;
    const { isLocked, sectionType } = this.props;
    const { owner, name } = props[sectionType];
    const { isDataset } = this.state;

    if (!isLocked && !isDataset) {
      this.setState({ switchMenuVisible: false });
      setSidepanelVisible(owner, name, sidePanelVisible);
    }
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
  *  @param {Boolean} - commitsHovered
  *  sets hoverstate for committs
  *  @return {}
  */
  _hovercommits = (commitsHovered) => {
    this.setState({ commitsHovered });
  }

  /**
  *  @param {Boolean} blockReset
  *  toggles reset popup
  *  @return {}
  */
  _toggleResetPopup = (blockReset) => {
    if (!blockReset) {
      this.setState((state) => {
        const popupVisible = !state.popupVisible;
        return { popupVisible };
      });
    }
  }

  /**
    sets state to toggle the switch dropdown
    @return {}
  */
  _toggleSyncDropdown = () => {
    this.setState((state) => {
      const syncMenuVisible = !state.syncMenuVisible;
      return { syncMenuVisible };
    });
  }

  /**
  *  @param {}
  *  resets state after publish
  *  @return {}
  */
  _setRemoteSession = () => {
    const { owner, labbookName } = this.state;
    this.setState({
      addedRemoteThisSession: true,
      remoteUrl: `https://gigantum.com/${owner}/${labbookName}`,
    });
  }

  /**
  *  @param {Boolean} - pullOnly
  *  @param {Boolean} - allowSync
  *  @param {Boolean} - allowSyncPull
  *  handles syncing or publishing the project
  *  @calls {_handleSyncButton}
  */
  _renewToken = (pullOnly, allowSync, allowSyncPull) => {
    const { auth } = this.props;

    auth.renewToken(true, () => {
      this.setState({ showLoginPrompt: true });
    }, () => {
      this._handleSyncButton(pullOnly, allowSync, allowSyncPull);
    });
  }

  /**
  * @param {Object} data
  * syncs dataset
  */
  _syncDataset = (data) => {
    const { branchMutations } = this.state;
    const { setSyncingState } = this.props;

    setSyncingState(true);
    branchMutations.syncDataset(data, (response, error) => {
      if (error) {
        data.failureCall(error);
      }
    });
  }

  /**
  * @param {Object} data
  * @param {function} passedSuccessCall
  * @param { Boolean} pullOnly
  * checks if project has a any published datasets and pops modal to sync them
  * or syncs project if none present
  */
  _syncLabbook = (data, passedSuccessCall, pullOnly) => {
    const { props, state } = this;
    const { syncLabbook } = state.branchMutations;
    const { owner, name } = props.section;

    props.setSyncingState(true);

    LinkedLocalDatasetsQuery.getLocalDatasets({
      owner,
      name,
    }).then((linkedQueryResponse) => {
      const localDatasets = getLocalDatasets(linkedQueryResponse);

      if ((localDatasets.length === 0) || pullOnly) {
        props.setSyncingState(true);

        syncLabbook(data, (response, error) => {
          if (error) {
            data.failureCall(error);
          }
          if (passedSuccessCall) {
            passedSuccessCall();
          }
        });
      } else {
        this.setState({
          localDatasets,
          publishDatasetsModalVisible: !state.publishDatasetsModalVisible,
          publishDatasetsModalAction: 'Sync',
        });

        props.setSyncingState(false);
      }
    });
  }

  /**
  *  @param {Boolean} - pullOnly
  *  @param {Boolean} - allowSync
  *  @param {Boolean} - allowSyncPull
  *  @param {Function} - passedSuccessCall
  *  handles syncing or publishing the project
  *  @return {}
  */
  _handleSyncButton = (pullOnly, allowSync, allowSyncPull, passedSuccessCall) => {
    // TODO refactor this function

    const {
      defaultRemote,
      section,
      sectionType,
      setBranchUptodate,
      setSyncingState,
    } = this.props;
    const { owner } = section;
    const { isDataset } = this.state;
    const { buildImage } = this.state.branchMutations;

    this.setState({ syncMenuVisible: false });

    if (allowSync || (pullOnly && allowSyncPull)) {
      if (!defaultRemote) {
        this._togglePublishModal(!isDataset, false);
      } else {
        const self = this;
        const data = {
          successCall: () => {
            if (sectionType === 'labbook') {
              buildImage((response, error) => {
                if (error) {
                  console.error(error);
                  const messageData = {
                    id: uuidv4(),
                    message: `ERROR: Failed to build ${section.name}`,
                    isLast: null,
                    error: true,
                    messageBody: error,
                  };
                  setMultiInfoMessage(owner, section.name, messageData);
                }
              });
              setBranchUptodate();
            }
            setSyncingState(false);
          },
          failureCall: (errorMessage) => {
            setSyncingState(false);
            if (errorMessage.indexOf('Merge conflict') > -1) {
              self._toggleSyncModal();
              this.setState({ pullOnly });
            }
          },
          pullOnly: pullOnly || false,
        };

        this._checkSessionIsValid().then((response) => {
          if (!navigator.onLine) {
            self.setState({ showLoginPrompt: true });
          } else if (!(response.data
              && response.data.userIdentity
              && response.data.userIdentity.isSessionValid)) {
            this._renewTotken(pullOnly, allowSync, allowSyncPull);
          } else if (sectionType !== 'labbook') {
            this._syncDataset(data);
          } else {
            this._syncLabbook(data, passedSuccessCall, pullOnly);
          }
        });
      }
    }
  }

  /**
    *  @param {Object} activeBranch
    *  @param {Boolean} hasWriteAccess
    *  @param {Boolean} upToDate
    *  returns tooltip info
    *  @return {string}
    */
  _getTooltipText = (activeBranch, hasWriteAccess, upToDate) => {
    // destructure here
    const { props, state } = this;
    const {
      collaborators,
      defaultRemote,
      isLocked,
      section,
    } = this.props;
    // other variables
    const sectionCollabs = (collaborators && collaborators[section.name]) || null;
    const defaultDatasetMessage = 'Datasets currently does not support branching features';
    const isPullOnly = defaultRemote && !hasWriteAccess && sectionCollabs;
    let syncOrPublish = defaultRemote ? 'Sync' : 'Publish';
    syncOrPublish = isPullOnly ? 'Pull' : syncOrPublish;

    let createTooltip = state.isDataset ? defaultDatasetMessage : 'Create Branch';
    createTooltip = isLocked ? 'Cannot Create Branch while Project is in use' : createTooltip;

    let resetTooltip = 'Reset Branch to Remote';
    resetTooltip = upToDate ? 'Branch up to date' : resetTooltip;
    resetTooltip = activeBranch.commitsAhead === undefined ? 'Please wait while branch data is being fetched' : resetTooltip;
    resetTooltip = !activeBranch.isRemote ? 'Cannot reset a branch until it has been published' : resetTooltip;
    resetTooltip = (!activeBranch.isRemote && (activeBranch.branchName !== 'master')) ? 'The master branch must be published first' : resetTooltip;
    resetTooltip = state.isLocked ? 'Cannot Reset Branch while Project is in use' : resetTooltip;
    resetTooltip = state.isDataset ? defaultDatasetMessage : resetTooltip;
    let switchTooltip = props.isLocked ? 'Cannot switch branches while Project is in use' : 'Switch Branches';
    switchTooltip = state.isDataset ? defaultDatasetMessage : switchTooltip;

    const commitsBehindText = activeBranch.commitsBehind ? `${activeBranch.commitsBehind} Commits Behind, ` : '';
    const commitsAheadText = activeBranch.commitsAhead ? `${activeBranch.commitsAhead} Commits Ahead` : '';
    const commitTooltip = `${commitsBehindText} ${commitsAheadText}`;

    const data = {
      defaultDatasetMessage,
      hasWriteAccess,
      syncOrPublish,
      sectionCollabs,
      activeBranch,
      state,
    };
    // TODO FIX this, nesting ternary operations is bad
    return {
      syncTooltip: getSyncTooltip(props, data),
      manageTooltip: getManagedToolip(props, data),
      createTooltip,
      resetTooltip,
      switchTooltip,
      commitTooltip,
    };
  }

  /**
  *  @param {}
  *  toggles sync modal
  *  @return {string}
  */
 _toggleSyncModal = () => {
   this.setState((state) => {
     const forceSyncModalVisible = !state.forceSyncModalVisible;
     return {
       forceSyncModalVisible,
       publishDatasetsModalVisible: false,
     };
   });
 }

 render() {
   const { props, state } = this;
   const {
     branches,
     defaultRemote,
     owner,
     name,
     isLocked,
     isSticky,
     section,
     collaborators,
     setPublishingState,
   } = this.props;
   const {
     activeBranch,
     filteredBranches,
     branchMenuList,
     otherBranchCount,
   } = extraxtActiveBranch(branches);
   // declare vars here
   const sectionCollabs = (collaborators && collaborators[section.name])
      || null;
   const waitingOnCollabs = !sectionCollabs;
   const hasWriteAccess = checkForWriteAccess(activeBranch, defaultRemote, collaborators, section.name);
   const upToDate = (activeBranch.commitsAhead === 0)
    && (activeBranch.commitsBehind === 0);
   const allowSync = !((activeBranch.branchName !== 'master') && !defaultRemote)
    && !isLocked && hasWriteAccess;
   const allowSyncPull = !((activeBranch.branchName !== 'master') && !defaultRemote)
    && !isLocked && defaultRemote;
   const allowReset = !isLocked
    && !upToDate
    && activeBranch.isRemote
    && (activeBranch.commitsAhead !== undefined);
   const statusText = activeBranch.isRemote
     ? 'Local & Remote'
     : 'Local only';
   const showPullOnly = defaultRemote && !hasWriteAccess && !waitingOnCollabs;
   const disableDropdown = !allowSyncPull || !defaultRemote || showPullOnly;
   const syncButtonDisabled = (showPullOnly && !allowSyncPull)
    || (!defaultRemote && !allowSync)
    || (defaultRemote && !allowSync && !showPullOnly);
   const {
     syncTooltip,
     manageTooltip,
     createTooltip,
     resetTooltip,
     switchTooltip,
     commitTooltip,
   } = this._getTooltipText(activeBranch, hasWriteAccess, upToDate);
   const syncButtonText = defaultRemote
     ? showPullOnly
     ? 'Pull'
     : 'Sync'
     : 'Publish';

   // declare css here
   const switchDropdownCSS = classNames({
     'BranchMenu__dropdown-menu': true,
     hidden: !state.switchMenuVisible,
   });
   const branchMenuCSS = classNames({
     BranchMenu: true,
     hidden: isSticky,
   });
   const drodownButtonCSS = classNames({
     'BranchMenu__dropdown-btn': true,
     'BranchMenu__dropdown-btn--disabled': isLocked || state.isDataset,
     'BranchMenu__dropdown-btn--open': state.switchMenuVisible,
     'Tooltip-data Tooltip-data': isLocked || state.isDataset,
   });
   const branchNameCSS = classNames({
     'BranchMenu__branch-name': !state.switchingBranch,
     hidden: state.switchingBranch,
   });
   const branchSwitchingNameCSS = classNames({
     'BranchMenu__branch-name BranchMenu__branch-name--switching': state.switchingBranch,
     hidden: !state.switchingBranch,
   });
   const syncMenuDropdownCSS = classNames({
     'BranchMenu__dropdown-menu': state.syncMenuVisible && !disableDropdown,
     hidden: !state.syncMenuVisible,
   });
   const syncMenuDropdownButtonCSS = classNames({
     'Btn--branch Btn--action Btn--branch--sync-dropdown': true,
     'Btn--branch--sync-open': state.syncMenuVisible,
   });
   const syncCSS = classNames({
     'Btn--branch Btn--action Btn--branch--sync': true,
     'Btn--branch--sync--publish': !defaultRemote,
     'Btn--branch--sync--pull': showPullOnly,
     'Btn--branch--sync--upToDate': defaultRemote && (upToDate || (activeBranch.commitsAhead === undefined) || isLocked) && !showPullOnly,
     'Tooltip-data': !state.commitsHovered,
   });
   const manageCSS = classNames({
     'Btn--branch Btn--action Btn--branch--manage': true,
     'Tooltip-data': true,
   });
   const resetCSS = classNames({
     'Btn--branch Btn--action Btn--branch--reset': true,
     'Tooltip-data': true,
   });
   const createCSS = classNames({
     'Btn--branch Btn--action Btn--branch--create': true,
     'Tooltip-data': true,
   });
   const popupCSS = classNames({
     BranchMenu__popup: true,
     hidden: !state.popupVisible,
   });

   return (
     <div className={branchMenuCSS}>
       <div className="BranchMenu__dropdown">
         <div
           onClick={() => this._toggleBranchSwitch()}
           data-tooltip={switchTooltip}
           className={drodownButtonCSS}
           role="presentation"
         >
           <div className={branchNameCSS}>
             <div className="BranchMenu__dropdown-label">Branch:</div>
             <div className="BranchMenu__dropdown-text">{activeBranch.branchName}</div>
           </div>

           <div className={branchSwitchingNameCSS}>
             <span className="BranchMenu__dropdown-label">Branch:</span>
             <span className="BranchMenu__dropdown-text ">
               {`switching to ${state.switchingBranch}...`}
             </span>
           </div>
           <div
             className="BranchMenu__status Tooltip-data Tooltip-data--small"
             data-tooltip={statusText}
           >
             { activeBranch.isLocal
               ? <div className="BranchMenu__status--local" />
               : <div />
             }
             { activeBranch.isRemote
               ? <div className="BranchMenu__status--remote" />
               : <div />
             }
           </div>
         </div>
         <div className={switchDropdownCSS}>
           <h5 className="BranchMenu__h5">Quick Switch</h5>
           <ul className="BranchMenu__ul">
             { branchMenuList.map((branch) => {
               const cloudIconCSS = classNames({
                 BranchMenu__icon: true,
                 'BranchMenu__icon--cloud': branch.isRemote,
                 'BranchMenu__icon--empty': !branch.isRemote,
               });
               const localIconCSS = classNames({
                 BranchMenu__icon: true,
                 'BranchMenu__icon--local': branch.isLocal,
                 'BranchMenu__icon--empty': !branch.isLocal,
               });

               return (
                 <li
                   onClick={() => this._switchBranch(branch)}
                   key={branch.branchName}
                   className="BranchMenu__list-item"
                   role="presentation"
                 >
                   <div className="BranchMenu__text">{branch.branchName}</div>
                   <div className="BranchMenu__icons">
                     <div className={cloudIconCSS} />
                     <div className={localIconCSS} />
                   </div>
                 </li>
               );
             })
             }

             { (otherBranchCount > 0)
               && <div className="BranchMenu__other-text">{`+${otherBranchCount} others` }</div>
             }

             { (filteredBranches.length === 0)
                && (
                  <li
                    className="BranchMenu__list-item BranchMenu__list-item--create"
                    onClick={() => this._setModalState('createBranchVisible')}
                    role="presentation"
                  >
                    No other branches.
                    <button
                      type="button"
                      className="Btn--flat"
                    >
                    Create a new branch?
                    </button>
                  </li>
                )
              }
           </ul>
           <div className="BranchMenu__menu-button">
             <button
               type="button"
               onClick={() => this._toggleSidePanel(true)}
               className="BranchMenu__button Btn--flat"
             >
               Manage Branches
             </button>
           </div>
         </div>
       </div>
       { !state.action
         ? (
           <div className="BranchMenu__buttons">
             <button
               onClick={() => this._toggleSidePanel(true)}
               className={manageCSS}
               disabled={isLocked || state.isDataset}
               data-tooltip={manageTooltip}
               type="button"
             />
             <button
               className={createCSS}
               type="button"
               disabled={isLocked || state.isDataset}
               data-tooltip={createTooltip}
               onClick={() => this._setModalState('createBranchVisible')}
             />
             <div className="BranchMenu__reset-container">
               <button
                 className={resetCSS}
                 type="button"
                 disabled={!allowReset || state.isDataset}
                 data-tooltip={resetTooltip}
                 onClick={() => this._toggleResetPopup(!allowReset || state.isDataset)}
               />
               <div className={popupCSS}>
                 <p>You are about to reset this branch. Resetting a branch will get rid of local changes. Click 'Confirm' to proceed.</p>
                 <div className="flex justify--space-around">
                   <button
                     type="button"
                     className="Btn--flat"
                     onClick={() => { this._toggleResetPopup(); }}
                   >
                    Cancel
                   </button>
                   <button
                     type="button"
                     className="BranchMenu__reset-confirm"
                     onClick={() => this._resetBranch()}
                   >
                    Confirm
                   </button>
                 </div>
               </div>
             </div>
             <div className="BranchMenu__sync-container">
               <button
                 className={syncCSS}
                 onClick={() => { this._handleSyncButton(showPullOnly, allowSync, allowSyncPull); }}
                 disabled={syncButtonDisabled}
                 data-tooltip={syncTooltip}
                 type="button"
               >
                 { !upToDate && allowSync && (activeBranch.commitsAhead !== undefined)
                  && (
                    <div
                      className="BranchMenu__sync-status Tooltip-data Tooltip-data--small"
                      data-tooltip={commitTooltip}
                      onMouseEnter={() => this._hovercommits(true)}
                      onMouseLeave={() => this._hovercommits(false)}
                    >
                      { (activeBranch.commitsBehind !== 0)
                        && (
                          <div className="BranchMenu__sync-status--commits-behind">
                            { activeBranch.commitsBehind }
                          </div>
                        )
                      }
                      { (activeBranch.commitsAhead !== 0)
                        && (
                          <div className="BranchMenu__sync-status--commits-ahead">
                            { activeBranch.commitsAhead }
                          </div>
                        )
                      }
                    </div>
                  )
                 }
                 <div className="Btn--branch--text">{syncButtonText}</div>
               </button>

               <button
                 className={syncMenuDropdownButtonCSS}
                 disabled={disableDropdown}
                 onClick={() => { this._toggleSyncDropdown(); }}
                 type="submit"
               />

               <div className={syncMenuDropdownCSS}>
                 <h5 className="BranchMenu__h5">Remote Action</h5>
                 <ul className="BranchMenu__ul">
                   { allowSync
                      && (
                      <li
                        className="BranchMenu__list-item"
                        onClick={() => this._handleSyncButton(false, allowSync, allowSyncPull)}
                        role="presentation"
                      >
                        Sync (Pull then Push)
                      </li>
                      )
                   }
                   <li
                     className="BranchMenu__list-item"
                     onClick={() => this._handleSyncButton(true, allowSync, allowSyncPull)}
                     role="presentation"
                   >
                    Pull (Pull-only)
                   </li>
                 </ul>
               </div>
             </div>
           </div>
         )
         : <div className="BranchMenu__action">{state.action}</div>
       }

       <CreateBranch
         owner={owner}
         name={name}
         modalVisible={state.createBranchVisible}
         description={section.description}
         toggleModal={this._setModalState}
       />

       <Branches
         sidePanelVisible={props.sidePanelVisible}
         toggleSidePanel={this._toggleSidePanel}
         defaultRemote={props.defaultRemote}
         diskLow={props.diskLow}
         branches={props.branches}
         disableDropdown={disableDropdown}
         activeBranch={activeBranch}
         toggleModal={this._setModalState}
         isSticky={isSticky}
         branchMutations={state.branchMutations}
         isLocked={isLocked}
         handleSyncButton={this._handleSyncButton}
         waitingOnCollabs={waitingOnCollabs}
         allowSync={allowSync}
         allowSyncPull={allowSyncPull}
         sectionId={props.sectionId}
         syncTooltip={syncTooltip}
         switchBranch={this._switchBranch}
         toggleCover={this._toggleCover}
         isDeprecated={props.isDeprecated}
         setBranchUptodate={props.setBranchUptodate}
         showPullOnly={showPullOnly}
         labbookName={section.name}
         owner={owner}
         name={name}
       />
       {
        state.publishModalVisible
        && (
          <VisibilityModal
            owner={section.owner}
            name={section.name}
            labbookId={props.sectionId}
            remoteUrl={defaultRemote}
            auth={props.auth}
            buttonText="Publish"
            header="Publish"
            modalStateValue="visibilityModalVisible"
            sectionType={props.sectionType}
            setPublishingState={props.setPublishingState}
            checkSessionIsValid={this._checkSessionIsValid}
            toggleModal={this._togglePublishModal}
            resetState={this._resetState}
            resetPublishState={this._resetPublishState}
            setRemoteSession={this._setRemoteSession}
          />
        )
       }
       { state.publishDatasetsModalVisible
        && (
          <PublishDatasetsModal
            owner={props.section.owner}
            name={props.section.name}
            labbookId={props.sectionId}
            remoteUrl={props.remoteUrl}
            auth={props.auth}
            buttonText="Publish All"
            header={state.publishDatasetsModalAction}
            pullOnly={state.pullOnly}
            modalStateValue="visibilityModalVisible"
            sectionType={props.sectionType}
            setSyncingState={props.setSyncingState}
            setPublishingState={props.setPublishingState}
            toggleSyncModal={this._toggleSyncModal}
            checkSessionIsValid={this._checkSessionIsValid}
            toggleModal={this._togglePublishModal}
            resetState={this._resetState}
            resetPublishState={this._resetPublishState}
            setRemoteSession={this._setRemoteSession}
            handleSync={this._handleSyncButton}
            localDatasets={state.localDatasets || []}
          />
        )
       }

       { state.forceSyncModalVisible
        && (
          <ForceSync
            toggleSyncModal={this._toggleSyncModal}
            sectionType={props.sectionType}
            pullOnly={state.pullOnly}
            owner={owner}
            name={name}
          />
        )
       }

       { state.showLoginPrompt
        && <LoginPrompt closeModal={this._closeLoginPromptModal} />
       }
     </div>
   );
 }
}

const mapStateToProps = state => ({
  collaborators: state.collaborators.collaborators,
});

const mapDispatchToProps = () => ({});

export default connect(mapStateToProps, mapDispatchToProps)(BranchMenu);
