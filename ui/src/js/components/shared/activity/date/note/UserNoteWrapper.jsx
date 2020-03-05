// @flow
// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// components
import UserNote from './UserNote';
// assets
import './UserNoteWrapper.scss';

type Props = {
  editorFullscreen: Boolean,
  userNoteVisible: Boolean,
}

class UserNoteWrapper extends Component<Props> {
  state = {
    userNoteVisible: false,
  };

  /**
  *   @param {boolean} value
  *   sets state to show hide usernote
  *   @return {}
  */
  _toggleUserNote = (userNoteVisible) => {
    this.setState({ userNoteVisible });
  }

  render() {
    const {
      userNoteVisible,
    } = this.state;
    const {
      editorFullscreen,
    } = this.props;

    // declare css here
    const userActivityContainerCSS = classNames({
      UserNote__container: true,
      'UserNote__container--open': userNoteVisible,
      fullscreen: editorFullscreen,
    });
    const userNoteCardCSS = classNames({
      'UserNote__add UserNote__card column-1-span-10': true,
      hidden: !userNoteVisible,
    });
    const buttonCSS = classNames({
      'Btn Btn--feature Btn--feature--expanded--paddingLeft relative UserNote__button': true,
      'UserNote__button--close': userNoteVisible,
    });
    return (
      <div className={userActivityContainerCSS}>
        <button
          className={buttonCSS}
          onClick={() => this._toggleUserNote(!userNoteVisible)}
          type="submit"
        >
          Add Note
        </button>
        <div className={userNoteCardCSS}>
          { userNoteVisible
            && (
            <UserNote
              toggleUserNote={this._toggleUserNote}
              key="UserNote"
              {...this.props}
            />
            )
          }
        </div>
      </div>
    );
  }
}

export default UserNoteWrapper;
