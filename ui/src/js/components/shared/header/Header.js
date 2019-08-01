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
import { setIsSynching } from 'JS/redux/actions/dataset/dataset';
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

  if (props.branhces) {
    branches = props.branches;
  } else {
    branches = [{
      branchName: 'master',
      isActive: true,
      commitsBehind: 0,
      commitsAhead: 0,
    }];
  }

  if (props.showMigrationButton) {
    branches = branches.filter(({ branchName }) => branchName !== 'master');
  }
  return branches;
};

class Header extends Component {
  /** *******************
   * child functions
   *
   ******************** */
  /**
   @param {boolean} isExporting
   updates container status state
   updates labbook state
  */
  _setExportingState = (isExporting) => {
    const { props } = this;

    if (this.refs.ContainerStatus) {
      this.refs.ContainerStatus.setState({ isExporting });
    }
    if (props.isExporting !== isExporting) {
      setExportingState(isExporting);
    }
  }

  /**
    @param {}
    updates html element classlist and labbook state
  */
  _showLabbookModal = () => {
    if (!this.props.modalVisible) {
      setModalVisible(true);
    }
  }

  /**
    @param {}
    updates html element classlist and labbook state
  */
  _hideLabbookModal = () => {
    const { props } = this;
    // TODO remove document to add classname, should use react state and classnames
    if (document.getElementById('labbookModal')) {
      document.getElementById('labbookModal').classList.add('hidden');
    }

    if (document.getElementById('modal__cover')) {
      document.getElementById('modal__cover').classList.add('hidden');
    }

    if (props.modalVisible) {
      setModalVisible(false);
    }
  }

  /**
    @param {boolean} isPublishing
    updates container status state
    updates labbook state
  */
 _setPublishingState = (isPublishing) => {
   const { props } = this;

   if (this.refs.ContainerStatus) {
     this.refs.ContainerStatus.setState({ isPublishing });
   }

   if ((props.isPublishing !== isPublishing)) {
     setPublishingState(isPublishing);
   }

   if (props.sectionType === 'dataset') {
     const { owner, name } = props.dataset;
     setIsSynching(owner, name, isPublishing);
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

    if (this.refs.ContainerStatus) {
      this.refs.ContainerStatus.setState({ isSyncing });
    }

    if (props.isSyncing !== isSyncing) {
      setSyncingState(isSyncing);
    }
    if (props.sectionType === 'dataset') {
      const { owner, name } = props.dataset;
      setIsSynching(owner, name, isSyncing);
    }
  }

  render() {
    const { props } = this;
    const {
      labbook,
      branchName,
      dataset,
    } = props;
    const {
      visibility,
      description,
      collaborators,
      defaultRemote,
      id,
    } = labbook || dataset;
    const section = labbook || dataset;
    const isLabbookSection = props.sectionType === 'labbook';
    const branches = getBranches(props);

    // declare css here
    const headerCSS = classNames({
      Header: true,
      'Header--sticky': props.isSticky,
      'Header--demo': (window.location.hostname === Config.demoHostName) || props.diskLow,
      'Header--is-deprecated': props.isDeprecated,
      'Header--branchesOpen': props.branchesOpen,
    });
    const branchesErrorCSS = classNames({
      BranchesError: props.branchesOpen,
      hidden: !props.branchesOpen,
    });


    return (

      <div className="Header__wrapper">

        <div className={headerCSS}>
          <div className="Header__flex">
            <div className="Header__columnContainer Header__columnContainer--flex-1">

              <TitleSection
                self={this}
                {...props}
              />
              <ErrorBoundary
                type={branchesErrorCSS}
                key="branches"
              >
                <BranchMenu
                  {...props}
                  defaultRemote={section.defaultRemote}
                  branchesOpen={props.branchesOpen}
                  section={section}
                  branches={branches}
                  sectionId={section.id}
                  activeBranch={section.activeBranchName || 'master'}
                  toggleBranchesView={props.toggleBranchesView}
                  mergeFilter={props.mergeFilter}
                  isSticky={props.isSticky}
                  visibility={props.visibility}
                  sectionType={props.sectionType}
                  auth={props.auth}
                  setSyncingState={this._setSyncingState}
                  setPublishingState={this._setPublishingState}
                  setExportingState={this._setExportingState}
                  isLocked={props.isLocked}
                  setBranchUptodate={props.setBranchUptodate}
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
                isSticky={props.isSticky}
                {...props}
              />

              { isLabbookSection
                && <Container {...props} />
              }
            </div>
          </div>

          <Navigation {...props} />

        </div>
      </div>
    );
  }
}

export default Header;
