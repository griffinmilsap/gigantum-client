// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// store
import {
  setSyncingState,
  setPublishingState,
  setExportingState,
  setModalVisible,
} from 'JS/redux/actions/labbook/labbook';
import { setIsSyncing, setIsExporting } from 'JS/redux/actions/dataset/dataset';
// config
import Config from 'JS/config';
// components
import ErrorBoundary from 'Components/common/ErrorBoundary';
import TitleSection from './titleSection/TitleSection';
import ActionsSection from './actionsSection/ActionsSection';
import BranchMenu from './branches/BranchMenu';
import Container from './container/Container';
import Navigation from './navigation/Navigation';
// assets
import './Header.scss';

/**
  @param {Object} branches
  @return {Array}
*/
const getBranches = (props) => {
  let branches = [];
  if (props.branches) {
    branches = props.branches;
  } else {
    const commitsBehind = (props.dataset && props.dataset.commitsBehind)
      ? props.dataset.commitsBehind
      : 0;
    const commitsAhead = (props.dataset && props.dataset.commitsAhead)
      ? props.dataset.commitsAhead
      : 0;
    branches = [{
      branchName: 'master',
      isActive: true,
      commitsBehind,
      commitsAhead,
    }];
  }

  if (props.showMigrationButton) {
    branches = branches.filter(({ branchName }) => branchName !== 'master');
  }
  return branches;
};

type Props = {
  branchName: string,
  branchesOpen: string,
  dataset: {
    name: string,
    owner: string,
  },
  diskLow: boolean,
  isDeprecated: boolean,
  isExporting: boolean,
  isPublishing: boolean,
  isSticky: boolean,
  isSyncing: boolean,
  labbook: {
    name: string,
    owner: string,
  },
  modalVisible: boolean,
  sectionType: string,
  toggleBranchesView: Function,
  mergeFilter: boolean,
  auth: Object,
  isLocked: boolean,
  setBranchUptodate: Function,
};

class Header extends Component<Props> {
  /** *******************
   * child functions
   *
   ******************** */
  /**
   @param {boolean} newIsExporting
   updates container status state
   updates labbook state
  */
  _setExportingState = (newIsExporting) => {
    const { sectionType, isExporting } = this.props;
    const { owner, name } = this.props[sectionType];

    if (isExporting !== newIsExporting) {
      setExportingState(owner, name, newIsExporting);
    }
    if (sectionType === 'dataset') {
      setIsExporting(owner, name, isExporting);
    }
  }

  /**
    @param {}
    updates html element classlist and labbook state
  */
  _showLabbookModal = () => {
    const { props } = this;
    const { owner, name } = props[props.sectionType];

    if (!props.modalVisible) {
      setModalVisible(owner, name, true);
    }
  }

  /**
    @param {}
    updates html element classlist and labbook state
  */
  _hideLabbookModal = () => {
    const { props } = this;
    const { owner, name } = props[props.sectionType];
    // TODO remove document to add classname, should use react state and classnames
    if (document.getElementById('labbookModal')) {
      document.getElementById('labbookModal').classList.add('hidden');
    }

    if (document.getElementById('modal__cover')) {
      document.getElementById('modal__cover').classList.add('hidden');
    }

    if (props.modalVisible) {
      setModalVisible(owner, name, false);
    }
  }

  /**
    @param {boolean} isPublishing
    updates container status state
    updates labbook state
  */
 _setPublishingState = (owner, name, isPublishing) => {
   const { props } = this;

   if ((props.isPublishing !== isPublishing)) {
     setPublishingState(owner, name, isPublishing);
   }

   if (props.sectionType === 'dataset') {
     setIsSyncing(owner, name, isPublishing);
   }
 }

 /** *
    @param {Node} element
    checks if element is too large for card area
    @return {boolean}
 */
 _checkOverflow = (element) => {
   if (element) {
     const curOverflow = element.style.overflow;

     if (!curOverflow || curOverflow === 'visible') {
       element.style.overflow = 'hidden';
     }

     const isOverflowing = (element.clientWidth < element.scrollWidth)
      || (element.clientHeight < element.scrollHeight);

     element.style.overflow = curOverflow;

     return isOverflowing;
   }

   return null;
 }

  /** ***
  *  @param {boolean} isSyncing
  *  updates container status state
  *  updates labbook state
  *  @return {}
  */
  _setSyncingState = (isSyncing) => {
    const { props } = this;
    const { owner, name } = props[props.sectionType];
    if (props.isSyncing !== isSyncing) {
      setSyncingState(owner, name, isSyncing);
    }
    if (props.sectionType === 'dataset') {
      setIsSyncing(owner, name, isSyncing);
    }
  }

  render() {
    const {
      labbook,
      branchName,
      dataset,
      isSticky,
      isDeprecated,
      branchesOpen,
      diskLow,
      sectionType,
      toggleBranchesView,
      mergeFilter,
      auth,
      isLocked,
      setBranchUptodate,
    } = this.props;
    const {
      visibility,
      description,
      collaborators,
      defaultRemote,
      id,
    } = labbook || dataset;
    const section = labbook || dataset;
    const isLabbookSection = sectionType === 'labbook';
    const branches = getBranches(this.props);

    // declare css here
    const headerCSS = classNames({
      Header: true,
      'Header--sticky': isSticky,
      'Header--demo': (window.location.hostname === Config.demoHostName) || diskLow,
      'Header--is-deprecated': isDeprecated,
      'Header--branchesOpen': branchesOpen,
    });
    const branchesErrorCSS = classNames({
      BranchesError: branchesOpen,
      hidden: !branchesOpen,
    });

    return (

      <div className="Header__wrapper">

        <div className={headerCSS}>
          <div className="Header__flex">
            <div className="Header__columnContainer Header__columnContainer--flex-1">

              <TitleSection
                self={this}
                {...this.props}
              />
              <ErrorBoundary
                type={branchesErrorCSS}
                key="branches"
              >
                <BranchMenu
                  {...this.props}
                  defaultRemote={section.defaultRemote}
                  branchesOpen={branchesOpen}
                  section={section}
                  branches={branches}
                  sectionId={section.id}
                  activeBranch={section.activeBranchName || 'master'}
                  toggleBranchesView={toggleBranchesView}
                  mergeFilter={mergeFilter}
                  isSticky={isSticky}
                  visibility={visibility}
                  sectionType={sectionType}
                  auth={auth}
                  setSyncingState={this._setSyncingState}
                  setPublishingState={this._setPublishingState}
                  setExportingState={this._setExportingState}
                  isLocked={isLocked}
                  setBranchUptodate={setBranchUptodate}
                />
              </ErrorBoundary>

            </div>

            <div className="Header__columnContainer Header__columnContainer--fixed-width">
              <ActionsSection
                visibility={visibility}
                description={description}
                collaborators={collaborators}
                defaultRemote={defaultRemote}
                labbookId={id}
                remoteUrl={defaultRemote}
                setSyncingState={this._setSyncingState}
                setExportingState={this._setExportingState}
                branchName={branchName}
                isSticky={isSticky}
                {...this.props}
              />

              { isLabbookSection
                && <Container {...this.props} />
              }
            </div>
          </div>

          <Navigation {...this.props} />

        </div>
      </div>
    );
  }
}

export default Header;
