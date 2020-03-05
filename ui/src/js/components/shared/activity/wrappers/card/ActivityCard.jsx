// @flow
// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// components
import ActivityDetails from './ActivityDetails';
// assets
import './ActivityCard.scss';

/**
  @param {Object} props
  logic if the card should show by default or not
  @return {Boolean}
*/
const shouldShowDetails = (props) => {
  const { node } = props.edge;
  const { show, detailObjects } = node;
  const detailsHasShow = detailObjects.filter(details => details.show).length !== 0;

  return (show && detailsHasShow);
};

/**
  @param {Object} props
  @param {Object} state
  gets varibales for render function
  @return {Object}
*/
const getRenderVariables = (props, state) => {
  const { node } = props.edge;
  const type = node.type && node.type.toLowerCase();
  const expandedHeight = props.attachedCluster
    ? 110 * (props.attachedCluster.length - 1)
    : 0;
  const expandedBarHeight = state.isOver
    ? expandedHeight - ((props.attachedCluster.length - 1) * 15)
    : expandedHeight;
  const margin = state.isOver
    ? ((props.attachedCluster.length - 1) * 7.5)
    : 0;

  // declare style here
  const expandedStyle = props.attachedCluster && {
    height: `${expandedBarHeight}px`,
    margin: `${margin}px 0 0 0`,
  };
  const firstInitial = props.edge.node.username.charAt(0).toUpperCase();

  if (props.isFirstCard && props.attachedCluster) {
    expandedStyle.top = '2px';
  }

  return {
    expandedBarHeight,
    expandedHeight,
    expandedStyle,
    firstInitial,
    margin,
    type,
  };
};


type Props = {
  attachedCluster: Array,
  compressExpanded: Function,
  edge: {
    node: {
      message: String,
      username: String,
    },
  },
  hoveredRollback: Boolean,
  isCompressed: Boolean,
  isExpandedHead: Boolean,
  isExpandedEnd: Boolean,
  isExpandedNode: Boolean,
  name: string,
  owner: string,
  position: Number,
  sectionType: String,
};

class ActivityCard extends Component<Props> {
  state = {
    showExtraInfo: shouldShowDetails(this.props),
    show: true,
    isOver: false,
  }

  /**
    @param {string} timestamp
    if input is undefined. current time of day is used
    inputs a time stamp and return the time of day HH:MM am/pm
    @return {string}
  */
  _getTimeOfDay = (timestamp) => {
    const time = (timestamp !== undefined) ? new Date(timestamp) : new Date();
    const hour = (time.getHours() % 12 === 0) ? 12 : time.getHours() % 12;
    const minutes = (time.getMinutes() > 9) ? time.getMinutes() : `0${time.getMinutes()}`;
    const ampm = time.getHours() >= 12 ? 'pm' : 'am';

    return `${hour}:${minutes}${ampm}`;
  }

  /**
    @param {}
    * determines the appropriate margins for cards when compressing
    @return {object}
  */
  _processCardStyle = () => {
    const activityCardStyle = {};
    const {
      attachedCluster,
      isCompressed,
      isExpandedHead,
      isExpandedEnd,
    } = this.props;

    if (isCompressed) {
      if (!isExpandedHead && !isExpandedEnd) {
        activityCardStyle.marginTop = '-7.5px';
        activityCardStyle.marginBottom = '-7.5px';
      } else if (isExpandedHead) {
        const distance = attachedCluster.length - 1;
        const calculatedMargin = distance * 7.5;

        activityCardStyle.marginTop = `${calculatedMargin}px`;
        activityCardStyle.marginBottom = '-7.5px';
      } else if (isExpandedEnd) {
        const distance = attachedCluster.length - 1;
        const calculatedMargin = distance * 7.5;

        activityCardStyle.marginTop = '-7.5px';
        activityCardStyle.marginBottom = `${calculatedMargin}px`;
      }
    }

    return activityCardStyle;
  }

  /**
    @param {Boolean} isOver
    sets state for side bar to compress on hover
  */
  _expandCollapseSideBar = (isOver) => {
    const { attachedCluster, compressExpanded } = this.props;
    compressExpanded(attachedCluster, !isOver);

    this.setState({ isOver });
  }

  /**
    @param {} isOver
    toggles show and showExtraInfo
  */
  _toggleDetails = () => {
    this.setState((state) => {
      const show = !state.show;
      const showExtraInfo = !state.showExtraInfo;
      return { show, showExtraInfo };
    });
  }

  render() {
    const {
      show,
      showExtraInfo,
    } = this.state;
    const {
      edge,
      hoveredRollback,
      isCompressed,
      isExpandedEnd,
      isExpandedNode,
      name,
      owner,
      position,
      sectionType,
    } = this.props;
    const { node } = edge;
    const activityCardStyle = this._processCardStyle();
    const {
      firstInitial,
      type,
    } = getRenderVariables(this.props, this.state);
    // declare css here
    const activityCardCSS = classNames({
      'ActivityCard card': showExtraInfo,
      'ActivityCard ActivityCard--collapsed card': !showExtraInfo,
      'ActivityCard--faded': hoveredRollback > position,
      ActivityCard__expanded: isExpandedNode,
      ActivityCard__compressed: isCompressed && !isExpandedEnd,
    });
    const titleCSS = classNames({
      'ActivityCard__title flex flex--row justify--space-between': true,
      open: showExtraInfo || (type === 'note' && show),
      closed: !showExtraInfo || (type === 'note' && !show),
    });

    return (
      <div className="ActivityCard__container column-1-span-9">
        <div className={activityCardCSS} style={activityCardStyle}>

          <div
            className={`ActivityCard__badge ActivityCard__badge--${type}`}
            title={type}
          />

          <div className="ActivityCard__content">

            <div
              className={titleCSS}
              onClick={() => this._toggleDetails()}
              role="presentation"
            >
              <div className="ActivityCard__stack">

                <p className="ActivityCard__time">
                  {this._getTimeOfDay(edge.node.timestamp)}
                </p>

                <div className="ActivityCard__user">{firstInitial}</div>
              </div>

              <h6 className="ActivityCard__commit-message">
                <b>{`${edge.node.username} - `}</b>
                { edge.node.message }
              </h6>
            </div>
            {
              (showExtraInfo && ((type !== 'note') || show))
                && (
                  <ActivityDetails
                    sectionType={sectionType}
                    edge={edge}
                    show={showExtraInfo}
                    key={`${node.id}_activity-details`}
                    node={node}
                    owner={owner}
                    name={name}
                  />
                )
            }
          </div>
        </div>
      </div>
    );
  }
}


export default ActivityCard;
