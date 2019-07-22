// vendor
import React, { Component } from 'react';
import { boundMethod } from 'autobind-decorator';
// components
import PackageStatus from './PackageStatus';
import PackageQueueItem from './PackageQueueItem';
// assets
import './PackageQueue.scss';

export default class PackageModal extends Component {
  state = {
    editedPackageRows: {},
  }

  /**
  *  @param {String} - packageName
  *  @param {String} - packageManager
  *  sets which packages are being edited
  *  @return {}
  */
  @boundMethod
  _setEditedPackageRows(packageName, packageManager) {
    const { state } = this;
    const newEditedPackageRows = Object.assign({}, state.editedPackageRows);
    if (newEditedPackageRows[packageManager]) {
      newEditedPackageRows[packageManager].set(packageName, {});
    } else {
      newEditedPackageRows[packageManager] = new Map([[packageName, {}]]);
    }
    this.setState({ editedPackageRows: newEditedPackageRows });
  }

  /**
  *  @param {String} - packageName
  *  @param {String} - packageManager
  *  removes which packages are being edited
  *  @return {}
  */
  @boundMethod
  _removeEditedPackageRows(packageName, packageManager) {
    const { state } = this;
    const newEditedPackageRows = Object.assign({}, state.editedPackageRows);
    if (newEditedPackageRows[packageManager]) {
      newEditedPackageRows[packageManager].delete(packageName);
    }
    this.setState({ editedPackageRows: newEditedPackageRows });
  }

  /**
  *  @param {Object} evt
  *  @param {String} pkgManager
  *  @param {String} pkgName
  *  @param {String} pkgVersion
  *  @param {Number} index
  *  @param {String} packageValue
  *  updated packageName in state
  *  @return {}
  */
  @boundMethod
  _updatePackage(evt, pkgManager, pkgName, pkgVersion, index, packageValue) {
    const { props, state } = this;
    if (evt.key === 'Enter') {
      const { newPackageName } = state.editedPackageRows[pkgManager].get(pkgName);
      const { newPackageVersion } = state.editedPackageRows[pkgManager].get(pkgName);
      const versionObject = (newPackageVersion || pkgVersion) ? { version: newPackageVersion !== undefined ? newPackageVersion : pkgVersion } : {};
      const packageData = {
        package: newPackageName || pkgName,
        manager: pkgManager,
        ...versionObject,
      };
      props.queuePackage(packageData, index);
      this._removeEditedPackageRows(pkgName, pkgManager);
    } else {
      const newEditedPackageRows = Object.assign({}, state.editedPackageRows);
      const currentObject = newEditedPackageRows[pkgManager].get(pkgName);
      const newPackageValue = evt.target.value;
      currentObject[packageValue] = newPackageValue;
      newEditedPackageRows[pkgManager].set(pkgName, currentObject);

      this.setState({ editedPackageRows: newEditedPackageRows });
    }
  }

  /**
  *  returns valid and invalid package count
  *  @return {Boolean}
  */
  _countValiditiy = (packageName, packageManager) => {
    const { props } = this;
    let validCount = 0;
    let invalidCount = 0;
    props.packageQueue.forEach((pkg) => {
      if (pkg.verified && !pkg.error) {
        validCount += 1;
      } else if (pkg.error) {
        invalidCount += 1;
      }
    });
    return {
      validCount,
      invalidCount,
    };
  }

  render() {
    const { props, state } = this;
    const { validCount, invalidCount } = this._countValiditiy();

    return (
      <div className="PackageQueue flex flex--column justify--space-between">
        <div className="PackageQueue--empty flex flex--column">
          <div className="PackageQueue__header">
            <h5>Packages to Install</h5>
          </div>
          {
          (props.packageQueue.length === 0) && (
            <div className="PackageQueue__container--empty">
              Enter packages, then press the
              {' '}
              <div className="Btn Btn--fake">
                <div className="Btn--fake-content">
                  Add
                  <div className="Icon--add"></div>
                </div>
              </div>
              {' '}
              button to add a package to the install list, or upload a requirements.txt file.
            </div>
          )
          }
          {
            (props.packageQueue.length > 0) && (
            <div className="PackageQueue__container">
              <div className="PackageQueue__tableHeader flex align-items--end justify--right">
                <div className="PackageQueue__manager">Package Manager</div>
                <div className="PackageQueue__name flex--1">Package Name</div>
                <div className="PackageQueue__version">Version</div>
                <div className="PackageQueue__status">Status</div>
              </div>
              <PackageQueueItem
                {...props}
                editedPackageRows={state.editedPackageRows}
                updatePackage={this._updatePackage}
                setEditedPackageRows={this._setEditedPackageRows}
                removeEditedPackageRows={this._removeEditedPackageRows}
              />
            </div>
            )
          }
          {
            (validCount > 0)
            && (
              <div className="PackageQueue__validCount flex justify--right align-items--center">
                <div className="Icon--add" />
                {`${validCount} added`}
              </div>
            )
          }
          {
            (invalidCount > 0)
            && (
              <div className="PackageQueue__invalidCount flex justify--right align-items--center">
                <div className="Icon--error" />
                {`${invalidCount} invalid`}
              </div>
            )
          }
        </div>
        <div className="PackageQueue__buttons align-self--end">
          <button
            className="Btn Btn--flat"
            type="button"
            onClick={() => props.toggleModal(false)}
          >
            Cancel
          </button>
          <button
            className="Btn"
            disabled={props.disableInstall}
            type="button"
            onClick={() => props.installPackages()}
          >
            Install All
          </button>
        </div>
      </div>
    );
  }
}
