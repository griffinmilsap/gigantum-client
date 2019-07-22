// vendor
import React, { Component, Fragment } from 'react';
import classNames from 'classnames';
import { boundMethod } from 'autobind-decorator';
// store
import store from 'JS/redux/store';
import { setContainerState } from 'JS/redux/actions/labbook/overview/overview';
import { setContainerStatus, setContainerMenuVisibility } from 'JS/redux/actions/labbook/containerStatus';
import { setContainerMenuWarningMessage, setCloseEnvironmentMenus } from 'JS/redux/actions/labbook/environment/environment';
import { setPackageMenuVisible } from 'JS/redux/actions/labbook/environment/packageDependencies';
import { setBuildingState, setMergeMode, updateTransitionState } from 'JS/redux/actions/labbook/labbook';
import { setErrorMessage, setInfoMessage, setWarningMessage } from 'JS/redux/actions/footer';
// assets
import './DevTools.scss';

class DevTools extends Component {
  state = {
    isMouseOver: false,
    selectedDevTool: (() => {
      const { owner, name } = this.props.labbook;
      const defaultFromApi = this.props.labbook.environment.base ? this.props.labbook.environment.base.developmentTools[0] : 'jupyterlab';
      const devToolConfig = localStorage.getItem('devToolConfig') ? JSON.parse(localStorage.getItem('devToolConfig')) : {};
      if (devToolConfig._timestamps && devToolConfig._timestamps[0]) {
        const oldestConfig = devToolConfig._timestamps[0].time;
        const timeStampedOwner = devToolConfig._timestamps[0].owner;
        const timeStampedName = devToolConfig._timestamps[0].name;
        const threeMonthsAgo = (new Date()).setMonth(new Date().getMonth() - 3);
        if (threeMonthsAgo > oldestConfig) {
          delete devToolConfig[timeStampedOwner][timeStampedName];
          if (Object.keys(devToolConfig[timeStampedOwner]).length === 0) {
            delete devToolConfig[timeStampedOwner];
          }
          devToolConfig._timestamps.shift();
          localStorage.setItem('devToolConfig', JSON.stringify(devToolConfig));
        }
      }
      if (devToolConfig[owner] && devToolConfig[owner][name]) {
        return devToolConfig[owner][name];
      }
      return defaultFromApi;
    })(),
    showDevList: false,
  }

  componentDidMount() {
    window.addEventListener('click', this._closeDevtoolMenu);
  }

  componentWillUnmount() {
    window.removeEventListener('click', this._closeDevtoolMenu);
  }

  /**
  *  @param {Object} evt
  *  closes dev tool
  *  @return {}
  */
  @boundMethod
  _closeDevtoolMenu(evt) {
    if (evt.target.className.indexOf('DevTool') < 0) {
      this.setState({ showDevList: false });
    }
  }

  /**
  *  @param {Object} evt
  *  upodates state if the conditions are met
  *  @return {}
  */
  @boundMethod
  _toggleDevtoolMenu(evt) {
    const { state } = this;
    this.setState({ showDevList: !state.showDevList });
  }

  /**
  *  @param {string} developmentTool
  *  @param {string} developmentTool
  *  mutation to trigger opening of development tool
  *  @return {}
  */
  @boundMethod
  _openDevToolMuation(developmentTool) {
    const { props } = this;
    const { containerStatus, imageStatus } = props;
    const { owner, name } = props.labbook;
    let tabName = `${developmentTool}-${owner}-${name}`;
    const labbookCreationDate = Date.parse(`${this.props.creationDateUtc}Z`);
    const timeNow = Date.parse(new Date());

    const timeDifferenceMS = timeNow - labbookCreationDate;

    let status = (containerStatus === 'RUNNING') ? 'Running' : containerStatus;
    status = (containerStatus === 'NOT_RUNNING') ? 'Stopped' : status;
    status = (imageStatus === 'BUILD_IN_PROGRESS' || imageStatus === 'BUILD_QUEUED') ? 'Building' : status;
    status = (imageStatus === 'BUILD_FAILED') ? 'Rebuild' : status;
    status = (imageStatus === 'DOES_NOT_EXIST') ? 'Rebuild' : status;
    status = ((imageStatus === 'DOES_NOT_EXIST') || (imageStatus === 'BUILD_IN_PROGRESS')) && (timeDifferenceMS < 15000) ? 'Building' : status;

    if (((status !== 'Stopped') && (status !== 'Running')) || (props.isExporting || props.isPublishing || props.isSyncing || props.isBuilding)) {
      setWarningMessage('Could not launch development environment as the project is not ready.');
    } else if (status === 'Stopped') {
      setInfoMessage('Starting Project container. When done working, click Stop to shutdown the container.');
      setMergeMode(false, false);
      updateTransitionState(name, 'Starting');

      props.containerMutations.startContainer({ devTool: developmentTool }, (response, error) => {
        if (error) {
          setErrorMessage('Error Starting Dev tool', error);
        }

        if (response.startDevTool) {
          tabName = `${developmentTool}-${owner}-${name}`;
          let path = `${window.location.protocol}//${window.location.hostname}${response.startDevTool.path}`;
          if (developmentTool === 'notebook') {
            if (path.includes('/lab/tree')) {
              path = path.replace('/lab/tree', '/tree');
            } else {
              path = `${path}/tree/code`;
            }
          }

          window[tabName] = window.open(path, tabName);
        }
      });
    } else if (window[tabName] && !window[tabName].closed) {
      window[tabName].focus();
    } else {
      const data = { devTool: developmentTool };
      setInfoMessage(`Starting ${developmentTool}, make sure to allow popups.`);

      props.containerMutations.startDevTool(
        data,
        (response, error) => {
          if (response.startDevTool) {
            tabName = `${developmentTool}-${owner}-${name}`;
            let path = `${window.location.protocol}//${window.location.hostname}${response.startDevTool.path}`;
            if (developmentTool === 'notebook') {
              if (path.includes('/lab/tree')) {
                path = path.replace('/lab/tree', '/tree');
              } else {
                path = `${path}/tree/code`;
              }
            }

            window[tabName] = window.open(path, tabName);
          }

          if (error) {
            setErrorMessage('Error Starting Dev tool', error);
          }
        },
      );
    }
  }

  /**
  *  @param {string} developmentTool
  *  mutation to trigger opening of development tool
  *  @return {}
  */
  @boundMethod
  _selectDevTool(developmentTool) {
    const { props } = this;
    const { owner, name } = props.labbook;
    const devToolConfig = localStorage.getItem('devToolConfig') ? JSON.parse(localStorage.getItem('devToolConfig')) : {};
    const ownerObject = devToolConfig[owner] || {};
    const newObject = {
      [owner]: {
        ...ownerObject,
        [name]: developmentTool,
      },
    };
    const newDevToolConfig = Object.assign({}, devToolConfig, newObject);
    if (newDevToolConfig._timestamps) {
      newDevToolConfig._timestamps.push({ time: (new Date()).getTime(), owner, name });
    } else {
      newDevToolConfig._timestamps = [{ time: (new Date()).getTime(), owner, name }];
    }
    localStorage.setItem('devToolConfig', JSON.stringify(newDevToolConfig));

    this.setState({ selectedDevTool: developmentTool, showDevList: false });
    this._openDevToolMuation(developmentTool);
  }

  render() {
    const { props, state } = this;
    const devTools = props.labbook.environment.base
      ? props.labbook.environment.base.developmentTools : [];

    const devtToolMenuCSS = classNames({
      'DevTools__dropdown-menu': true,
      hidden: !state.showDevList,
    });
    const buttonDropdownCSS = classNames({
      'DevTools__btn DevTools__btn--dropdown': true,
      'DevTools__btn--open': state.showDevList,
    });

    return (
      <div className="DevTools">
        <div className="DevTools__flex">
          <button
            type="submit"
            className="DevTools__btn DevTools__btn--launch Btn--columns Btn-last"
            onClick={() => { this._openDevToolMuation(state.selectedDevTool); }}
          >
            <div className="Btn--label">Launch:</div>
            <div className="Btn--text">{state.selectedDevTool}</div>
          </button>

          <button
            type="button"
            data-id="DevToolDropdown"
            className={buttonDropdownCSS}
            onClick={evt => this._toggleDevtoolMenu(evt)}
          />

        </div>

        <div className={devtToolMenuCSS}>
          <div className="DevTool__menu-title">Launch</div>
          <ul className="DevTool__list">
            {

                devTools.map((developmentTool) => {
                  const devToolsCss = classNames({
                    DevTools__item: true,
                    'DevTools__item--selected': (developmentTool === state.selectedDevTool),
                  });

                  return (
                    <li
                      key={developmentTool}
                      className={devToolsCss}
                      onClick={() => this._selectDevTool(developmentTool)}
                    >
                      <div className="DevTools__icon jupyter-icon" />
                      <div className="DevTools__text">{developmentTool}</div>
                    </li>
                  );
                })
              }
          </ul>
        </div>
      </div>
    );
  }
}

export default DevTools;
