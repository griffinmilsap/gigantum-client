// @flow
// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// components
import DetailRecords from './DetailRecords';

/**
*  Returns boolean if details should be shown
*  @param {Object} props
*
*  @return{Boolean}
*/
const showDetail = (props) => {
  const { categorizedDetails, itemKey } = props;
  return (categorizedDetails.detailObjects[itemKey][0].show);
};


type Props = {
  categorizedDetails: {
    detailObjects: Object,
  },
  hideElipsis: Function,
  itemKey: String,
  name: String,
  owner: String,
  sectionType: String,
  showEllipsis: Boolean,
  show: Boolean,
};

class ActivityDetailsList extends Component<Props> {
  state = {
    show: showDetail(this.props),
    showDetails: this.props.show,
  };

  /**
  *   @param {}
  *  reverse state of showExtraInfo
  */
  _toggleDetailsList = () => {
    this.setState((state) => {
      const show = !state.show;
      return { show };
    });
  }

  /**
   * @param {}
   * restarts refetch
   * @return {}
   */
  _toggleDetailsView = () => {
    const { hideElipsis } = this.props;
    this.setState({ showDetails: true });
    hideElipsis();
  }

  /**
    @param {string} key
    formats key into a title
    @return {string}
  */
  _formatTitle = (key) => {
    const { props } = this;
    const tempTitle = key.split('_').join(' ') && key.split('_').join(' ').toLowerCase();
    let title = tempTitle.charAt(0) && tempTitle.charAt(0).toUpperCase() + tempTitle.slice(1);
    title = title === 'Labbook' ? 'Project' : title;
    return `${title} (${props.categorizedDetails.detailObjects[props.itemKey].length})`;
  }

  render() {
    const {
      show,
      showDetails,
    } = this.state;
    const {
      categorizedDetails,
      itemKey,
      name,
      owner,
      sectionType,
      showEllipsis,
    } = this.props;
    const keys = categorizedDetails.detailKeys[itemKey];
    const type = categorizedDetails.detailObjects[itemKey][0].type.toLowerCase();
    // decalre css here
    const activityDetailsCSS = classNames({
      ActivityDetail__details: true,
      note: type === 'note',
    });
    const activityDetailTitleCSS = classNames({
      'ActivityDetail__details-title': true,
      'ActivityDetail__details-title--open': show,
      'ActivityDetail__details-title--closed': !show,
    });
    return (

      <div className={activityDetailsCSS}>
        { showDetails && (type !== 'note')
          ? (
            <div
              className={activityDetailTitleCSS}
              onClick={() => { this._toggleDetailsList(); }}
              role="presentation"
            >
              <div className="ActivityDetail__header">
                <div className={`ActivityDetail__badge ActivityDetail__badge--${type}`} />
                <div className="ActivityDetail__content">
                  <p>{this._formatTitle(itemKey)}</p>
                </div>
              </div>

            </div>
          )
          : <hr />
        }
        { show
          && (
            <div className="ActivtyDetail_list">
              <DetailRecords
                keys={keys}
                sectionType={sectionType}
                owner={owner}
                name={name}
              />
            </div>
          )
        }

        { showEllipsis
          && (
            <div
              className="ActivityCard__ellipsis ActivityCard__ellipsis-detail"
              onClick={() => { this._toggleDetailsView(); }}
              role="presentation"
            />
          )
        }
      </div>
    );
  }
}

export default ActivityDetailsList;
