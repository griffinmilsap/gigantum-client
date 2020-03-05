// @flow
// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import { connect } from 'react-redux';
// redux
import { setPauseUpload } from 'JS/redux/actions/shared/fileBrowser/fileBrowserWrapper';
import * as footerActionsRedux from 'JS/redux/actions/footer';
// components
import FooterNotificationList from './FooterNotificationList';
import FooterUploadBar from './FooterUploadBar';
// assets
import './Footer.scss';


type Props = {
  messageListOpen: Boolean,
  viewHistory: Boolean,
  history: Object,
  labbookName: string,
  footerActions: {
    setToggleMessageList: Function,
  },
}

class Footer extends Component<Props> {
  /**
    subscribe to store to update state
  */
  componentDidMount() {
    window.addEventListener('resize', this._resize);
  }

  componentDidUpdate() {
    const {
      messageListOpen,
      viewHistory,
      footerActions,
    } = this.props;
    const setTimeoutFunc = () => {
      this.timeout = setTimeout(() => {
        footerActions.setToggleMessageList(false, true);
      }, 10 * 1000);
    };

    if (messageListOpen && !viewHistory && !this.timeout) {
      setTimeoutFunc();
    } else if (this.timeout && (messageListOpen && !viewHistory)) {
      clearTimeout(this.timeout);
      this.timeout = null;
      setTimeoutFunc();
    } else {
      clearTimeout(this.timeout);
      this.timeout = null;
    }
  }

  /**
    unsubscribe from event listeners
  */
  componentWillUnmount() {
    window.removeEventListener('resize', this._resize);
  }

  /**
    @param {} -
    opens project in view
  */
  _openLabbook = () => {
    const {
      history,
      labbookName,
    } = this.props;
    this._clearState();
    history.replace(`/projects/${labbookName}`);
  }

  /**
    @param {}
    add scroll listener to pop up footer
  */
  _clearState = () => {
    const { props } = this;
    document.getElementById('footerProgressBar').style.opacity = 0;

    props.footerActions.setResetFooter();

    setTimeout(() => {
      document.getElementById('footerProgressBar').style.width = '0%';
      setTimeout(() => {
        document.getElementById('footerProgressBar').style.opacity = 1;
      }, 1000);
    }, 1000);
  }

  /**
   @param {}
   stops user and pops a modal prompting them to cancel continue or save changes
  */
  _pauseUpload = () => {
    setPauseUpload(true);
  }

  /**
    @param {}
    gets upload message which tracks progess
  */
  _closeFooter = () => {
    const { props } = this;
    props.footerActions.setUploadMessageRemove('', '', 0);
  }

  /**
    @param {object} messageItem
    gets upload message which tracks progess
  */
  _removeMessage = (messageItem) => {
    const { props } = this;
    props.footerActions.setRemoveMessage(messageItem.id);
  }

  /**
    @param {}
    toggles messages list to collapsed or expanded
    updates redux store
    @return {}
  */
  _toggleMessageList = () => {
    const { props } = this;
    props.footerActions.setToggleMessageList(!props.messageListOpen, true);
  }

  /**
    @param {number}
    toggles view of message body for a stack item
    updates redux store
    @return {}
   */
  _showMessageBody = (index) => {
    const { props } = this;
    const {
      viewHistory,
    } = this.props;
    if (!viewHistory) {
      props.footerActions.setUpdateMessageStackItemVisibility(index);
    } else {
      props.footerActions.setUpdateHistoryStackItemVisibility(index);
    }
  }

  /**
    * @param {}
    * update store to risize component
  */
  _resize = () => {
    const { props } = this;
    props.footerActions.setResizeFooter();
  }

  render() {
    const { props } = this;
    const bodyWidth = document.body.clientWidth;

    const footerClass = classNames({
      Footer: true,
      'Footer--uploading': props.uploadOpen,
      'Footer--expand': (props.open) || props.uploadOpen,
      'Footer--expand-extra': (props.open && props.uploadOpen),

    });
    const footerButtonClass = classNames({
      'Footer__disc-button': true,
      'Footer__disc-button--open': props.messageListOpen,
      'Footer__dist-button--side-view': bodyWidth < 1600,
      'Footer__disc-button--helper-open': props.helperVisible,
      'Footer__disc-button--bottom': !props.messageListOpen && props.uploadOpen,
    });

    return (
      <div className="Footer__container">
        <div id="footer" className={footerClass}>

          <FooterNotificationList
            showMessageBody={this._showMessageBody}
            parentState={this.props}
            toggleMessageList={this._toggleMessageList}
          />

          <FooterUploadBar
            closeFooter={this._closeFooter}
            openLabbook={this._openLabbook}
            parentState={this.props}
          />

          <button
            type="button"
            onClick={() => this._toggleMessageList()}
            className={footerButtonClass}
          />

        </div>
      </div>
    );
  }
}

const mapStateToProps = state => state.footer;

const mapDispatchToProps = () => ({
  footerActions: footerActionsRedux,
});

export default connect(mapStateToProps, mapDispatchToProps)(Footer);
