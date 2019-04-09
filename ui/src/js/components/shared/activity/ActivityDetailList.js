// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// components
import DetailRecords from './DetailRecords';


export default class ActivityDefaultList extends Component {
  constructor(props) {
  	super(props);

    let show = true;

    props.edge.node.detailObjects.forEach((detail) => {
      if (detail.show) {
        show = false;
      }
    });

    this.state = {
      show: props.categorizedDetails.detailObjects[props.itemKey][0].show,
      showEllipsis: show,
      showDetails: props.show,
    };
    this._toggleDetailsList = this._toggleDetailsList.bind(this);
  }

  /**
  *   @param {}
  *  reverse state of showExtraInfo
  */
  _toggleDetailsList = () => {
    this.setState({ show: !this.state.show });
  }

  /**
   * @param {}
   * restarts refetch
   * @return {}
   */
  _toggleDetailsView = () => {
    const { props } = this;
    this.setState({ showDetails: true, showEllipsis: false });
    props.hideElipsis();
  }

  /**
    @param {string} timestamp
    if input is undefined. current time of day is used
    inputs a time stamp and return the time of day HH:MM am/pm
    @return {string}
  */
  _getTimeOfDay(timestamp) {
    const time = (timestamp !== undefined) ? new Date(timestamp) : new Date();
    const hour = (time.getHours() % 12 === 0) ? 12 : time.getHours() % 12;
    const unformatedMinutes = time.getMinutes();
    const minutes = (time.getMinutes() > 9) ? time.getMinutes() : `0${unformatedMinutes}`;
    const ampm = time.getHours() >= 12 ? 'pm' : 'am';
    return `${hour}:${minutes}${ampm}`;
  }

  /**
    @param {string} key
    formats key into a title
    @return {string}
  */
  _formatTitle(key) {
    const tempTitle = key.split('_').join(' ') && key.split('_').join(' ').toLowerCase();
    let title = tempTitle.charAt(0) && tempTitle.charAt(0).toUpperCase() + tempTitle.slice(1);
    title = title === 'Labbook' ? 'Project' : title;
    return `${title} (${this.props.categorizedDetails.detailObjects[this.props.itemKey].length})`;
  }

  render() {
    const { props, state } = this;
    console.log(props.categorizedDetails.detailObjects[this.props.itemKey][0].type, props.categorizedDetails.detailObjects);
    const keys = this.props.categorizedDetails.detailKeys[this.props.itemKey];


    const type = this.props.categorizedDetails.detailObjects[this.props.itemKey][0].type.toLowerCase();
    const activityDetailsCSS = classNames({
      ActivityDetail__details: true,
      note: type === 'note',
    });
    return (

      <div className={activityDetailsCSS}>
        {
            state.showDetails && type !== 'note'
              ? (
                <div
                  onClick={() => { this._toggleDetailsList(); }}
                  className={state.show ? 'ActivityDetail__details-title ActivityDetail__details-title--open' : 'ActivityDetail__details-title ActivityDetail__details-title--closed'}
                >
                  <div className="ActivityDetail__header">
                    <div className={`ActivityDetail__badge ActivityDetail__badge--${type}`} />
                    <div className="ActivityDetail__content">
                      <p>{this._formatTitle(props.itemKey)}</p>
                    </div>
                  </div>

                </div>
              )
              : <hr />
          }
        {state.show
        && (
        <div className="ActivtyDetail_list">
          <DetailRecords
            keys={keys}
            sectionType={props.sectionType}
          />
        </div>
        )
          }

        {props.showEllipsis

        && <div className="ActivityCard__ellipsis ActivityCard__ellipsis-detail" onClick={() => { this._toggleDetailsView(); }} />

          }
      </div>
    );
  }
}
