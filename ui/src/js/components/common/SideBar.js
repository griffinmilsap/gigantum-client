import React, { Component } from 'react';
import classNames from 'classnames';
import { Link } from 'react-router-dom';
// store
import { setCallbackRoute } from 'JS/redux/actions/routes';
// config
import config from 'JS/config';
// components
import Tooltip from 'Components/common/Tooltip';
import User from './User';
// assets
import './SideBar.scss';

export default class SideBar extends Component {
  constructor(props) {
    super(props);
    this.state = {
      authenticated: null,
    };
  }

  /*
    sets authentication response to the state
  */
  componentDidMount() {
    const { props, state } = this;
    props.auth.isAuthenticated().then((response) => {
      let isAuthenticated = response;
      if (isAuthenticated === null) {
        isAuthenticated = false;
      }
      if (isAuthenticated !== state.authenticated) {
        this.setState({ authenticated: isAuthenticated });
      }
    });
  }

  /**
    @param {}
    logout through Auth0
  */
  logout = () => {
    const { props } = this;
    props.auth.logout();
  }

  render() {
    const { props, state } = this;
    const isLabbooks = (window.location.href.indexOf('projects') > 0) || (window.location.href.indexOf('datasets') === -1);
    // declare css here
    const sidebarCSS = classNames({
      'SideBar col-sm-1': state.authenticated || state.authenticated === null,
      hidden: !(state.authenticated || state.authenticated === null),
      'SideBar--demo': (window.location.hostname === config.demoHostName) || props.diskLow,
    });
    const projectsCSS = classNames({
      SideBar__icon: true,
      'SideBar__icon--labbooks-selected': isLabbooks,
      'SideBar__icon SideBar__icon--labbooks': !isLabbooks,
    });
    const datasetCSS = classNames({
      SideBar__icon: true,
      'SideBar__icon SideBar__icon--datasets': isLabbooks,
      'SideBar__icon SideBar__icon--datasets-selected': !isLabbooks,
    });
    const labbookSideBarItemCSS = classNames({
      'SideBar__nav-item SideBar__nav-item--labbooks': true,
      'SideBar__nav-item--selected': isLabbooks,
    });
    const datasetSideBarItemCSS = classNames({
      'SideBar__nav-item SideBar__nav-item--datasets': true,
      'SideBar__nav-item--selected': !isLabbooks,
    });

    return (
      <div className={sidebarCSS}>
        <div className="SideBar__inner-container">
          <div className="SideBar__logo" />
          <ul className="SideBar__nav">
            <li
              className="SideBar__list-item Tooltip-data Tooltip-data--right relative"
              data-tooltip="View Project listing page"
            >
              <Link
                onClick={() => setCallbackRoute('/projects/local')}
                className={labbookSideBarItemCSS}
                to={{ pathname: '/projects/local' }}
              >
                <div className={projectsCSS} />
                Projects
              </Link>
              <Tooltip section="labbookListing" />
            </li>
            <li
              className="SideBar__list-item Tooltip-data Tooltip-data--right relative"
              data-tooltip="View Dataset listing page"
            >
              <Link
                onClick={() => setCallbackRoute('/datasets/local')}
                className={datasetSideBarItemCSS}
                to={{ pathname: '/datasets/local' }}
              >
                <div className={datasetCSS} />
                Datasets
              </Link>
              <Tooltip section="datasetsTooltip" />
            </li>
          </ul>

          {
            state.authenticated && (<User {...props} />)
          }
        </div>
      </div>
    );
  }
}
