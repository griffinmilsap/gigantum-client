// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// assets
import './User.scss';

export default class User extends Component {
  state = {
    username: localStorage.getItem('username') || '',
    dropdownVisible: false,
  };

  componentDidMount() {
    document.addEventListener('mousedown', this._handleClickOutside.bind(this));
  }

  componentWillUnmount() {
    document.removeEventListener('mousedown', this._handleClickOutside.bind(this));
  }

  /**
    @param {}
    logout through Auth0
  */
  logout = () => {
    const { props } = this;
    props.auth.logout();
    this._toggleDropdown();
  }

  /**
    @param {}
    handles click to update state
  */
  _handleClickOutside = (event) => {
    const { state } = this;
    const userElementIds = ['user', 'username', 'logout', 'profile'];
    if (state.dropdownVisible && (userElementIds.indexOf(event.target.id) < 0)) {
      const dropdownVisible = false;
      this.setState({ dropdownVisible });
    }
  }

  /**
    @param {}
    toggles dropdown state
  */
  _toggleDropdown = () => {
    this.setState((state) => {
      const dropdownVisible = !state.dropdownVisible;
      return {
        ...state,
        dropdownVisible,
      };
    });
  }

  render() {
    const { state } = this;
    // declare css here
    const usernameCSS = classNames({
      User__name: true,
      'User__name--active': state.dropdownVisible,
      'User__name--long': state.username.length >= 10,
    });
    const userDropdownCSS = classNames({
      User__dropdown: true,
      hidden: !state.dropdownVisible,
    });
    const arrowCSS = classNames({
      'User__dropdown--arrow': true,
      hidden: !state.dropdownVisible,
    });

    return (
      <div
        id="user"
        className="User"
        key="user"
      >
        <div className="User__image" />
        <h6
          id="username"
          onClick={() => { this._toggleDropdown(); }}
          className={usernameCSS}
          data-tooltip={state.username}
        >
          {state.username}
        </h6>

        <div className={arrowCSS} />

        <div className={userDropdownCSS}>
          <a
            id="profile"
            href="http://gigantum.com/profile"
            rel="noopener noreferrer"
            target="_blank"
            className="User__button"
          >
            Profile
          </a>
          <button
            type="button"
            id="logout"
            className="User__button Btn Btn--flat"
            onClick={this.logout.bind(this)}
          >
            Logout
          </button>
        </div>
      </div>
    );
  }
}
