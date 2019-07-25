// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import PropTypes from 'prop-types';
// store
import { setUpdateHistoryView } from 'JS/redux/actions/footer';
// componenets
import FooterMessage from './FooterMessage';
// assets
import './FooterNotificationList.scss';
import './FooterMessage.scss';

type Props = {
  toggleMessageList: PropTypes.func,
  parentState: PropTypes.object,
}

/**
*  @param {Array} messageList
*  @param {Array} messageListOpenItems
*  sets selectedBuildId in state
*/
const getHeight = (messageList, messageListOpenItems) => {
  let height = (messageList.length > 6) ? 260 : messageList.length * 60;
  height = (messageListOpenItems.length > 0) ? 'auto' : height;
  height = (height === 'auto') ? 'auto' : `${height}px`;

  return height;
};

export default class FooterNotificationList extends Component<Props> {
  props: Props;

  state = { selectedBuildId: '' }

  /**
  *  @param {Boolean} selectedBuildId
  *  sets selectedBuildId in state
  */
  _setBuildId = (selectedBuildId) => {
    this.setState({ selectedBuildId });
    this.props.toggleMessageList();
  }

  render() {
    const { state } = this;
    const { parentState } = this.props;
    const messageList = parentState.viewHistory
      ? parentState.messageStackHistory
      : parentState.messageStack;
    const messageListOpenItems = messageList.filter(message => message.messageBodyOpen);
    const height = getHeight(messageList, messageListOpenItems);
    // declare css here
    const footerMessageSectionClass = classNames({
      Footer__messageContainer: true,
      'Footer__messageContainer--collapsed': !parentState.messageListOpen,
      'Footer__messageContainer--helper-open': parentState.helperVisible,
    });
    const footerMessageListClass = classNames({
      Footer__messageList: true,
      'Footer__messageList--collapsed': !parentState.messageListOpen,
    });
    const viewAllButtonClass = classNames({
      'Btn Btn--feature Btn--feature--expanded Btn--feature--noPadding': true,
      hidden: (parentState.viewHistory || !parentState.messageListOpen),
    });

    return (
      <div className={footerMessageSectionClass}>
        <button
          type="button"
          className={viewAllButtonClass}
          onClick={() => setUpdateHistoryView()}
        >
          View All
        </button>
        <div
          className={footerMessageListClass}
          style={{ height }}
        >
          <ul>
            {
              messageList.map(messageItem => (
                <FooterMessage
                  key={messageItem.id}
                  messageItem={messageItem}
                  selectedBuildId={state.selectedBuildId}
                  setBuildId={this._setBuildId}
                />
              ))
            }

            { (messageList.length === 0)
              && (
                <li className="FooterMessage">
                  <div className="FooterMessage__body">
                    <div className="FooterMessage__flex">
                      <div className="FooterMessage__item">
                        <p className="FooterMessage__title">No Notifications</p>
                      </div>
                    </div>
                  </div>
                </li>
              )
            }
          </ul>
        </div>
      </div>
    );
  }
}
