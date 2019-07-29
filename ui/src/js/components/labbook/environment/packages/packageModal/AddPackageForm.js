// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import PropTypes from 'prop-types';
// componenets
import Dropdown from 'Components/common/Dropdown';
// assets
import './AddPackageForm.scss';

export default class AddPackageForm extends Component {

  state = {
    selectedManager: this.props.defaultManager,
    packageName: '',
    checkedValue: 'latest',
    version: '',
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
    @param {string} checkedValue
    sets version radio button
  */
  _setChecked = (checkedValue) => {
    this.setState((state) => {
      const version = (checkedValue === 'latest') ? '' : state.value;

      return { checkedValue, version };
    });

    if (checkedValue === 'latest') {
      this.packageVersionInput.value = '';
    }
  }

  /**
    @param {event} evt
    closes menu
  */
  _closeMenus = (evt) => {
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
  _setselectedPackageManager = (selectedManager) => {
    this.packageNameInput.focus();
    this.setState({ selectedManager, managerDropdownVisible: false });

    if (selectedManager === 'apt') {
      this.setState({ version: '' });
    }
  }

  /**
  *  @param {}
  *  sets manager dropdown visibility
  */
  _setManagerDropdownVisibility = () => {
    this.setState((state) => {
      const managerDropdownVisible = !state.managerDropdownVisible;
      return { managerDropdownVisible };
    });
  }

  /**
  *  @param {Object} evt
  *  updated packageName in state
  *  @return {}
  */
  _updatePackageName = (evt) => {
    if ((evt.key === 'Enter') && evt.target.value.length) {
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
  _clearPackageName = () => {
    this.setState({ packageName: '' });

    if (this.packageNameInput) {
      this.packageNameInput.value = '';
    }
  }

  /**
  *  @param {Object} evt
  *  updated version in state
  *  @return {}
  */
  _updatePackageVersion = (evt) => {
    const { state } = this;

    if (evt.target.id === 'latest_version') {
      this.setState({ version: '' });
    } else if (evt.target.id === 'specific_version') {
      if ((state.selectedManager === 'apt') && !state.aptTooltipVisible) {
        this.setState({ aptTooltipVisible: true });
      } else if (state.selectedManager !== 'apt') {
        this.setState({ version: this.packageVersionInput.value });
      }
    } else if ((evt.key === 'Enter') && evt.target.value.length) {
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
  _clearPackageVersion = () => {
    this.setState({ version: '' });
    if (this.packageVersionInput) {
      this.packageVersionInput.value = '';
    }
  }

  /**
  *  @param {}
  *  clears version in state
  *  @return {}
  */
  _sendQueuePackage = () => {
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
    const buttonsDisabled = (state.packageName.length === 0);
    // declare css here
    const specificVersionCSS = classNames({
      'Radio flex relative': true,
      'AddPackageForm__version--active': (state.version !== ''),
      'Radio--disabled': (state.selectedManager === 'apt'),
    });

    return (
      <div className="AddPackageForm flex justify--center flex--column align-items--center">
        <div className="AddPackageForm__container flex flex--column justify--space-between">
          <div className="AddPackageForm__manager flex align-items--center">
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
          <div className="AddPackageForm__name flex align-items--center">
            <div className="AddPackageForm__label">Package Name</div>
            <input
              type="text"
              ref={(packageNameInput) => { this.packageNameInput = packageNameInput; }}
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
                checked={state.checkedValue === 'latest'}
                onClick={() => this._setChecked('latest')}
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
                checked={state.checkedValue === 'specify'}
                onClick={() => { this._setChecked('specify'); }}
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
                value={state.version}
                ref={(packageVersionInput) => { this.packageVersionInput = packageVersionInput; }}
                onClick={() => { this._setChecked('specify'); }}
                onChange={evt => this._updatePackageVersion(evt)}
                onKeyDown={evt => this._updatePackageVersion(evt)}
              />
            </label>
          </div>
          <div
            className="AddPackageForm__entry-buttons align-self--end"
          >
            <button
              className="Btn Btn--flat Btn--width-80"
              disabled={buttonsDisabled}
              type="button"
              onClick={() => this._clearPackageName()}
            >
              Clear
            </button>
            <button
              className="Btn Btn__add"
              disabled={buttonsDisabled}
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
