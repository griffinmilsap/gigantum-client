// vendor
import React, { Component } from 'react';
import { boundMethod } from 'autobind-decorator';
// assets
import './PackageStatus.scss';

export default class PackageStatus extends Component {
  state = {
    statusModalVisible: false,
    modalXPosition: 0,
  }

  /**
  *  @param {Event} evt
  *  @param {Boolean} statusModalVisible
  *  sets statusModalVisible in state
  *  @return {}
  */
  @boundMethod
  _setStatusModalVisible(evt, statusModalVisible) {
    const { target } = evt;
    const rect = target.getBoundingClientRect();
    const modalXPosition = (rect.top - 150) > 347 ? 347 : (rect.top - 150);
    this.setState({ statusModalVisible, modalXPosition });
  }

  /**
  *  @param {String} packageName
  *  @param {String} packageManager
  *  calls queue package and sets edit state
  *  @return {}
  */
  @boundMethod
  _handleEditPackage(packageName, packageManager) {
    const { props } = this;
    this.setState({ statusModalVisible: false, modalXPosition: 0 });
    props.setEditedPackageRows(packageName, packageManager);
  }

  /**
  *  @param {Object} packageData
  *  @param {Number} index
  *  @param {String} packageName
  *  @param {String} packageManager
  *  calls edit package and closes modal
  *  @return {}
  */
  @boundMethod
  _handleQueuePackage(packageData, index, packageName, packageManager) {
    const { props } = this;
    props.queuePackage(packageData, index);
    props.removeEditedPackageRows(packageName, packageManager);
  }

  render() {
    const { props, state } = this;
    const {
      verified,
      version,
      error,
      packageName,
      packageManager,
      index,
      isEdited,
      newPackageName,
      newPackageVersion,
    } = props;
    const styleObject = {
      top: `${state.modalXPosition}px`,
      left: '644px',
    };
    const versionObject = (newPackageVersion || version) ? { version: newPackageVersion !== undefined ? newPackageVersion : version } : {};
    const packageData = {
      package: newPackageName || packageName,
      manager: packageManager,
      ...versionObject,
    };
    if (isEdited) {
      return (
        <div className="flex">
          <button
            type="button"
            className="Btn Btn--small Btn--round Btn--smallMargin Btn__check"
            onClick={() => this._handleQueuePackage(packageData, index, packageName, packageManager)}
          />
          <button
            type="button"
            className="Btn Btn--small Btn--round Btn--smallMargin Btn__remove"
            onClick={() => props.removeEditedPackageRows(packageName, packageManager)}
          />
        </div>
      );
    }
    if (verified && error) {
      return (
        <div>
          <button
            type="button"
            className="Btn Btn--small Btn--round Btn__warning"
            onClick={evt => this._setStatusModalVisible(evt, !state.statusModalVisible)}
          />
          {
            state.statusModalVisible
            && (
              <div
                className="Popup Popup--fixed"
                style={styleObject}
              >
                <p className="Popup__header">Package Invalid</p>
                <p className="Popup__small-text">
                  The package name or version is invalid. Edit or remove the pacakge and try again.
                </p>
                <div className="flex">
                  <button
                    type="button"
                    className="Btn--flat"
                    onClick={() => { props.removePackageFromQueue(index); }}
                  >
                  Remove
                  </button>
                  <button
                    type="button"
                    onClick={() => this._handleEditPackage(packageName, packageManager)}
                  >
                  Edit
                  </button>
                </div>
              </div>
            )
          }
        </div>
      );
    }
    if (verified && !error) {
      return (<div className="PackageStatus PackageStatus--verified" />);
    }
    return (<div className="PackageStatus PackageStatus--verifying" />);
  }
}
