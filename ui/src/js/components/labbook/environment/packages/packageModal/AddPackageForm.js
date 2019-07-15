// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import { boundMethod } from 'autobind-decorator';
import Dropdown from 'Components/common/Dropdown';
// assets
import './AddPackageForm.scss';

export default class AddPackageForm extends Component {
  state = {
    selectedManager: this.props.defaultManager,
    packageName: '',
    version: null,
    aptTooltipVisible: false,
    managerDropdownVisible: false,
  }

  /**
   * attach window listener evetns here
  */
  componentDidMount() {
    window.addEventListener('click', this._closeMenus);
  }

  /**
   * detach window listener evetns here
  */
  componentWillUnmount() {
    window.removeEventListener('click', this._closeMenus);
  }

  /**
    @param {event} evt
    closes menu
  */
  @boundMethod
  _closeMenus(evt) {
    const { state } = this;
    const isDropdown = (evt.target.className.indexOf('Dropdown') > -1);
    const disabledRadio = (evt.target.hasAttribute('data-apt-popup'));
    if (!isDropdown && state.managerDropdownVisible) {
      this.setState({ managerDropdownVisible: false });
    }
    if (!disabledRadio && state.aptTooltipVisible) {
      this.setState({ aptTooltipVisible: false });
    }
  }

  /**
  *  @param {String} selectedManager
  *  sets selected package manager
  */
  @boundMethod
  _setselectedPackageManager(selectedManager) {
    document.getElementById('packageNameInput').focus();
    this.setState({ selectedManager, managerDropdownVisible: false });
    if (selectedManager === 'apt') {
      this.setState({ version: null });
    }
  }

  /**
  *  @param {}
  *  sets manager dropdown visibility
  */
  @boundMethod
  _setManagerDropdownVisibility() {
    const { state } = this;
    this.setState({ managerDropdownVisible: !state.managerDropdownVisible });
  }

  /**
  *  @param {Object} evt
  *  updated packageName in state
  *  @return {}
  */
  @boundMethod
  _updatePackageName(evt) {
    if (evt.key === 'Enter' && evt.target.value.length) {
      this._sendQueuePackage();
    } else {
      const packageName = evt.target.value;
      this.setState({ packageName });
    }
  }

  /**
  *  @param {}
  *  clears packageName in state
  *  @return {}
  */
  @boundMethod
  _clearPackageName() {
    this.setState({ packageName: '' });
    if (document.getElementById('packageNameInput')) {
      document.getElementById('packageNameInput').value = '';
    }
  }

  /**
  *  @param {Object} evt
  *  updated version in state
  *  @return {}
  */
  @boundMethod
  _updatePackageVersion(evt) {
    evt.stopPropagation();
    const { state } = this;
    if (evt.target.id === 'latest_version') {
      this.setState({ version: null });
    } else if (evt.target.id === 'specific_version') {
      if (state.selectedManager === 'apt' && !state.aptTooltipVisible) {
        this.setState({ aptTooltipVisible: true });
      } else if (state.selectedManager !== 'apt') {
        this.setState({ version: document.getElementById('packageVersionInput').value });
      }
    } else if (evt.key === 'Enter' && evt.target.value.length) {
      this._sendQueuePackage();
    } else {
      const version = evt.target.value;
      this.setState({ version });
    }
  }

  /**
  *  @param {}
  *  clears version in state
  *  @return {}
  */
  @boundMethod
  _clearPackageVersion() {
    this.setState({ version: null });
    if (document.getElementById('packageVersionInput')) {
      document.getElementById('packageVersionInput').value = '';
    }
  }

  /**
  *  @param {}
  *  clears version in state
  *  @return {}
  */
  @boundMethod
  _sendQueuePackage() {
    const { props, state } = this;
    const versionObject = state.version ? { version: state.version } : {};
    props.queuePackage({
      manager: state.selectedManager,
      package: state.packageName,
      ...versionObject,
    });
    this._clearPackageName();
    this._clearPackageVersion();
  }

  render() {
    const { props, state } = this;
    const { packageManagers } = props.base;
    const managerDropdownCSS = classNames({
      'Dropdown--addPackages Dropdown relative': true,
      'Dropdown--open': state.managerDropdownVisible,
      'Dropdown--collapsed': !state.managerDropdownVisible,
    });
    const specificVersionCSS = classNames({
      'Radio flex relative': true,
      'AddPackageForm__version--active': state.version !== null,
      'Radio--disabled': state.selectedManager === 'apt',
    });
    return (
      <div className="AddPackageForm flex justify--center flex--column align-items--center">
        <div className="AddPackageForm__container flex flex--column justify--space-between">
          <div
            className="AddPackageForm__manager flex align-items--center"
          >
            <div className="AddPackageForm__label">Package Manager</div>
            <Dropdown
              customStyle="addPackages margin--0"
              listItems={packageManagers}
              visibility={state.managerDropdownVisible}
              listAction={this._setManagerDropdownVisibility}
              itemAction={this._setselectedPackageManager}
              label={state.selectedManager}
            />
          </div>
          <div
            className="AddPackageForm__name flex align-items--center"
          >
            <div className="AddPackageForm__label">Package Name</div>
            <input
              type="text"
              id="packageNameInput"
              onChange={evt => this._updatePackageName(evt)}
              onKeyDown={evt => this._updatePackageName(evt)}
            />
          </div>
          <div
            className="AddPackageForm__version flex align-items--center"
          >
            <span className="AddPackageForm__version-title">Version</span>
            <label
              className="Radio"
              htmlFor="latest_version"
            >
              <input
                name="selectVersion"
                type="radio"
                id="latest_version"
                checked={state.version === null}
                onChange={evt => this._updatePackageVersion(evt)}
              />
              <span>Latest</span>
            </label>
            <label
              className={specificVersionCSS}
              htmlFor="specific_version"
            >
              <input
                name="selectVersion"
                type="radio"
                id="specific_version"
                checked={state.version !== null}
                onChange={evt => this._updatePackageVersion(evt)}
              />
              <span
                className="align-self--center"
                data-apt-popup
              >
              Specify
              </span>
              {
                state.aptTooltipVisible && (
                  <div className="InfoTooltip apt">
                    apt packages are always installed at the latest version.
                    {' '}
                    <a
                      target="_blank"
                      href="https://docs.gigantum.com"
                      rel="noopener noreferrer"
                    >
                      Learn more here
                    </a>
                  </div>
                )
              }
              <input
                type="text"
                disabled={state.version === null}
                id="packageVersionInput"
                onChange={evt => this._updatePackageVersion(evt)}
                onKeyDown={evt => this._updatePackageVersion(evt)}
              />
            </label>
          </div>
          <div
            className="AddPackageForm__entry-buttons align-self--end"
          >
            <button
              className="Btn Btn--flat"
              disabled={state.packageName.length === 0}
              type="button"
              onClick={() => this._clearPackageName()}
            >
              Clear
            </button>
            <button
              className="Btn Btn__add"
              disabled={state.packageName.length === 0}
              type="button"
              onClick={() => this._sendQueuePackage()}
            >
              Add
            </button>
          </div>
        </div>
      </div>
    );
  }
}
