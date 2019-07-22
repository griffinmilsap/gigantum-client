// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import Moment from 'moment';
import PropTypes from 'prop-types';
// components
import BuildModal from 'Components/shared/modals/BuildModal';
// store
import store from 'JS/redux/store';
import { setUpdateHistoryView } from 'JS/redux/actions/footer';
// assets
import './FooterNotificationList.scss';

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
  let height = messageList.length > 6 ? 260 : messageList.length * 60;
  height = messageListOpenItems.length > 0 ? 'auto' : height;
  height = height === 'auto' ? 'auto' : `${height}px`;

  return height;
};

export default class FooterNotificationList extends Component<Props> {
  props: Props;

  state = { selectedBuildId: null }

  /**
  *  @param {Boolean} selectedBuildId
  *  sets selectedBuildId in state
  */
  _setBuildId = (selectedBuildId) => {
    this.setState({ selectedBuildId });
    this.props.toggleMessageList();
  }

  render() {
    const { props, state } = this;
    const { parentState } = this.props;
    const messageList = parentState.viewHistory
      ? parentState.messageStackHistory
      : parentState.messageStack;
    // no other reference to owner and labbookname
    const { owner, labbookName } = store.getState().routes;
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
              messageList.map((messageItem, index) => {
                const messageBodyClasses = classNames({
                  'Footer__message-body-content': true,
                  hidden: !messageItem.messageBodyOpen || messageItem.buildProgress,
                });

                const toggleButton = classNames({
                  'Btn Btn__toggle': true,
                  'Btn__toggle--open': messageItem.messageBodyOpen,
                  hidden: messageItem.buildProgress,
                });

                const bodyCSS = classNames({
                  'height-auto': messageItem.messageBodyOpen,
                  [messageItem.className]: true,
                });
                const messageTitleCSS = classNames({
                  'Footer__message-title': true,
                  'Footer__message-title--collapsed': !messageItem.messageBodyOpen,
                });

                return (
                  <li
                    key={messageItem.id + index}
                    className={bodyCSS}
                  >
                    <div className="Footer__message-body">
                      <div className="Footer__flex-container">
                        <div className="Footer__message-icon" />

                        <div className="Footer__message-time">{ `${Moment(messageItem.date).fromNow()}:` }</div>
                        <div className="Footer__message-item">
                          <p className={messageTitleCSS}>{messageItem.message}</p>
                        </div>

                        { (messageItem.messageBody.length > 0)
                          && (
                          <div className="Footer__message-expand">
                            <button
                              type="button"
                              className={toggleButton}
                              onClick={() => { props.showMessageBody(index); }}
                            />
                          </div>
                          )

                        }
                        {
                          messageItem.buildProgress
                          && (
                            <button
                              className="Btn Btn--inverted Btn--inverted--white no-wrap align-self--center"
                              onClick={() => this._setBuildId(messageItem.id)}
                              type="button"
                            >
                              View Build Output
                            </button>
                          )
                        }
                      </div>
                      {
                        (state.selectedBuildId === messageItem.id)
                        && (
                          <BuildModal
                            setBuildId={this._setBuildId}
                            buildId={state.selectedBuildId}
                            keepOpen={messageItem.isLast}
                            owner={owner}
                            name={labbookName}
                          />
                        )
                      }
                      <div className={messageBodyClasses}>

                        <ul>
                          {
                            messageItem.messageBody && messageItem.messageBody.map((item, index) => (
                              <li key={`${messageItem.id}${index}`}>
                                <div
                                  className="Footer__message-body-content--text"
                                  dangerouslySetInnerHTML={{ __html: item.message }}
                                />
                              </li>
                            ))
                          }
                        </ul>
                      </div>
                    </div>

                  </li>
                );
              })
            }

            { (messageList.length === 0)
              && (
              <li className="Footer__message">
                <div className="Footer__message-body">
                  <div className="Footer__flex-container">
                    <div className="Footer__message-item">
                      <p className="Footer__message-title">No Notifications</p>
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
