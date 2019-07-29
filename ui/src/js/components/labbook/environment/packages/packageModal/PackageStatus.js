// vendor
import React, { Component } from 'react';
// assets
import './PackageStatus.scss';


/**
*  @param {newPackageVersion} string
*  @param {version} string
*  gets new package version for rendering
*  @return {}
*/
const getVersionObject = (newPackageVersion, version) => {
  let versionObject = {};

  if (newPackageVersion || version) {
    const newVersion = (newPackageVersion !== undefined) ? newPackageVersion : version;
    versionObject = { version: newVersion };
  }

  return versionObject;
};

export default class PackageStatus extends Component {
  state = {
    statusModalVisible: false,
    modalXPosition: 0,
  }

  static getDerivedStateFromProps(props, state) {
    const statusModalVisible = !props.removePopups ? state.statusModalVisible : false;

    return {
      ...state,
      statusModalVisible,
    };
  }

  componentDidMount() {
    window.addEventListener('click', this._closePopup);
  }

  componentWillUnmount() {
    window.removeEventListener('click', this._closePopup);
  }

  /**
  *  @param {Event} evt
  *  sets statusModalVisible in state
  *  @return {}
  */
  _closePopup = (evt) => {
    const {
      packageName,
      packageManager,
    } = this.props;
    const dataId = evt.target.getAttribute('data-id');
    const statusId = `${packageName}-${packageManager}-status`;
    if (dataId !== statusId) {
      this.setState({ statusModalVisible: false });
    }
  }

  /**
  *  @param {Event} evt
  *  @param {Boolean} statusModalVisible
  *  sets statusModalVisible in state
  *  @return {}
  */
  _setStatusModalVisible = (evt, statusModalVisible) => {
    const { target } = evt;
    const rect = target.getBoundingClientRect();
    const modalXPosition = ((rect.top - 210) > 347)
      ? 347
      : (rect.top - 210);

    this.setState({ statusModalVisible, modalXPosition });
  }

  /**
  *  @param {String} packageName
  *  @param {String} packageManager
  *  calls queue package and sets edit state
  *  @return {}
  */
  _handleEditPackage = (packageName, packageManager) => {
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
  _handleQueuePackage = (packageData, index, packageName, packageManager) => {
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
      pkg,
      isEdited,
      newPackageName,
      newPackageVersion,
      packageCount,
    } = props;
    const styleObject = {
      top: `${state.modalXPosition}px`,
      left: (packageCount > 3) ? '637px' : '649px',
    };
    const versionObject = getVersionObject(newPackageVersion, version);
    const packageData = {
      package: newPackageName || packageName,
      manager: packageManager,
      ...versionObject,
    };

    const popupText = pkg.duplicate
      ? `${packageName} has already been installed at version ${version}. Edit or remove the package and try again.`
      : 'The package name or version is invalid. Edit or remove the package and try again.';
    if (isEdited) {
      return (
        <div className="flex">
          <button
            type="button"
            className="Btn Btn--small Btn--round Btn--smallMargin Btn__check"
            onClick={() => this._handleQueuePackage(
              packageData,
              index,
              packageName,
              packageManager,
            )}
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
        <div className="relative">
          <button
            data-id={`${packageName}-${packageManager}-status`}
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
                  {popupText}
                </p>
                <div className="flex">
                  <button
                    type="button"
                    className="Btn Btn--flat Btn--width-80"
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
