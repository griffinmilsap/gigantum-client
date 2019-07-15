// vendor
import React, { Component } from 'react';
// components
import Tooltip from 'Components/common/Tooltip';
// assets
import './PackageActions.scss';

export default class PackageActions extends Component {

  /**
  *  @param{}
  *  removes singular package
  */
  _updatePackage() {
    const { props } = this;
    const data = {
      packages: [{
        ...props.packageNode,
        version: props.packageNode.latestVersion,
      }],
      duplicates: [props.id],
    };
    props.selectPackages(true);
    props.setBuildingState(true);
    const callback = () => {
      props.buildCallback();
    };
    props.packageMutations.addPackages(data, callback);
  }

  /**
  *  @param{}
  *  removes singular package
  */
  _removePackage() {
    const { props } = this;
    const data = {
      packages: [props.packageNode],
    };
    props.selectPackages(true);
    props.setBuildingState(true);
    const callback = () => {
      props.buildCallback();
    };
    props.packageMutations.removePackages(data, callback);
  }

  /**
  *  @param {}
  *  returns tooltip info
  *  @return {}
  */
  _getTooltip() {
    const { props } = this;
    let deleteTooltip = 'Delete Package';
    deleteTooltip = props.isLocked ? 'Cannot modify while environment is in use' : deleteTooltip;
    deleteTooltip = props.fromBase ? 'Cannot modify base packages' : deleteTooltip;
    let updateTooltip = 'Update Package';
    updateTooltip = props.isLocked ? 'Cannot modify while environment is in use' : updateTooltip;
    updateTooltip = (!props.latestVersion) ? 'Please wait while latest version is fetched' : updateTooltip;
    updateTooltip = (props.version === props.latestVersion) ? 'Up to date' : updateTooltip;
    updateTooltip = props.fromBase ? 'Cannot modify base packages' : updateTooltip;
    return {
      deleteTooltip,
      updateTooltip,
    }
  }

  render() {
    const { props } = this;
    const disableUpdate = (!props.latestVersion) || (props.version === props.latestVersion) || props.isLocked || props.fromBase;
    const disableDelete = (props.fromBase) || (props.isLocked);
    const { deleteTooltip, updateTooltip } = this._getTooltip();


    return (
      <div className="PackageActions flex flex--column justify--space-between">
        <button
          className="Btn Btn--medium Btn--round Btn__upArrow-secondary Tooltip-data"
          type="button"
          onClick={() => this._updatePackage()}
          data-tooltip={updateTooltip}
          disabled={disableUpdate}
        />
        <button
          className="Btn Btn--medium Btn--round Btn__delete-secondary Tooltip-data"
          type="button"
          data-tooltip={deleteTooltip}
          onClick={() => this._removePackage()}
          disabled={disableDelete}
        />
      </div>
    );
  }
}
