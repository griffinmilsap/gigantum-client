// @flow
// vendor
import React, { Component } from 'react';
import ActivityDetailList from './ActivityDetailList';

type Props = {
  edge: Object,
  name: String,
  node: {
    show: Boolean,
  },
  owner: String,
  sectionType: String,
  show: Boolean,
};

class ActivtyDetails extends Component<Props> {
  state = {
    showExtraInfo: this.props.node.show,
    showEllispsis: !this.props.node.show,
  };

  /**
  *  @param {} -
  *  reverse state of showExtraInfo
  *  @param {}
  */
  _toggleExtraInfo = () => {
    this.setState((state) => {
      const showExtraInfo = !state.showExtraInfo;
      return { showExtraInfo };
    });
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
    const unformatedMinutes = time.getMinutes();
    const minutes = (time.getMinutes() > 9) ? time.getMinutes() : `0${unformatedMinutes}`;
    const ampm = time.getHours() >= 12 ? 'pm' : 'am';
    return `${hour}:${minutes}${ampm}`;
  }

  /**
    @param {Object} node
    loobest through detailObjects array to get format an object of details
    @return {Object} categories
  */
  _catagorizeDetails = (node) => {
    const categories = {
      detailObjects: {},
      detailKeys: {},
    };

    node.detailObjects.forEach((detail) => {
      if (categories.detailObjects[detail.type] === undefined) {
        categories.detailObjects[detail.type] = [detail];
        categories.detailKeys[detail.type] = [detail.key];
      } else {
        categories.detailObjects[detail.type].push(detail);
        categories.detailKeys[detail.type].push(detail.key);
      }
    });

    return categories;
  }

  /**
    @param {}
    sets state to hide ellipsis for shortening
    @return {}
  */
  _hideElipsis = () => {
    this.setState({ showEllispsis: false });
  }

  render() {
    const { showEllispsis } = this.state;
    const {
      edge,
      name,
      node,
      owner,
      sectionType,
      show,
    } = this.props;
    const categorizedDetails = this._catagorizeDetails(node);

    return (
      <div className="ActivityDetail">
        {
          Object.keys(categorizedDetails.detailObjects).map((key, index) => (
            <ActivityDetailList
              sectionType={sectionType}
              hideElipsis={this._hideElipsis}
              edge={edge}
              categorizedDetails={categorizedDetails}
              itemKey={key}
              key={`${key}${index}`}
              siblingCount={node.detailObjects.length}
              show={show}
              showEllispsis={showEllispsis}
              owner={owner}
              name={name}
            />
          ))
        }
      </div>
    );
  }
}

export default ActivtyDetails;
