// @flow
// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import { setContainerMenuWarningMessage } from 'JS/redux/actions/labbook/environment/environment';
import shallowCompare from 'react-addons-shallow-compare';
import InfiniteScroll from 'react-infinite-scroller';
// store
import store from 'JS/redux/store';
// config
import config from 'JS/config';
// Components
import Loader from 'Components/common/Loader';
import Tooltip from 'Components/common/Tooltip';
import CreateBranch from 'Components/shared/modals/CreateBranch';
import PaginationLoader from './loaders/PaginationLoader';
import DateSection from './date/DateSection';
// utils
import NewActivity from './utils/NewActivity';
import { transformActivity } from './utils/ActivityUtils';
// assets
import './Activity.scss';

type Props = {
  activeBranch: String,
  description: String,
  diskLow: Boolean,
  isDeprecated: Boolean,
  isLocked: Boolean,
  name: String,
  owner: String,
  refetch: Function,
  relay: {
    environment: {
      getStore: Function,
    },
    refetchConnection: Function,
  },
  sectionType: string,
  setBuildingState: Function,
};


class Activity extends Component<Props> {
  dates = [];

  constructor(props) {
    super(props);
    const section = props[props.sectionType];
    this.state = {
      loadingMore: false,
      modalVisible: false,
      automaticRefetch: true,
      selectedNode: null,
      createBranchVisible: false,
      activityCardCount: 0,
      newActivityAvailable: false,
      editorFullscreen: false,
      hoveredRollback: null,
      expandedClusterObject: new Map(),
      activityRecords: section.activityRecords
        ? transformActivity(section.activityRecords)
        : [],
      stickyDate: false,
      compressedElements: new Set(),
    };
  }

  static getDerivedStateFromProps(nextProps, state) {
    const section = nextProps[nextProps.sectionType];
    const propsActivityRecords = nextProps[nextProps.sectionType].activityRecords;
    let expandableClusterObject = state.expandedClusterObject;
    let activityCardCount = 0;
    let { activityRecords } = state;

    const previousSection = nextProps[nextProps.sectionType];
    const prevCommit = previousSection && previousSection.activityRecords
      && previousSection.activityRecords.edges
      && section.activityRecords.edges[0].node && false;
    const newcommit = section && section.activityRecords
      && section.activityRecords.edges
      && section.activityRecords.edges[0]
      && section.activityRecords.edges[0].node;

    if (prevCommit && (prevCommit !== newcommit)) {
      expandableClusterObject = new Map();
    }

    activityRecords = transformActivity(propsActivityRecords, state);

    if (propsActivityRecords
        && propsActivityRecords.pageInfo
        && propsActivityRecords.pageInfo.hasNextPage) {
      const stateActivityRecords = state.activityRecords;

      const keys = Object.keys(stateActivityRecords);
      keys.forEach((key) => {
        activityCardCount += stateActivityRecords[key].length;
      });
    }

    return {
      ...state,
      activityRecords,
      activityCardCount,
      expandableClusterObject,
    };
  }

  /**
  *  @param {}
  *   add scroll listener
  *   add interval to poll for new activityRecords
  */
  componentDidMount() {
    const { refetch } = this.props;

    refetch('activity');
    this._isMounted = true;
    window.addEventListener('visibilitychange', this._handleVisibilityChange);

    window.addEventListener('focus', this._pollForActivity);
    window.addEventListener('scroll', this._handleScroll);
    this._pollForActivity();
  }

  shouldComponentUpdate(nextProps, nextState) {
    return shallowCompare(this, nextProps, nextState);
  }

  componentDidUpdate(previousProps) {
    const { activityRecords } = previousProps[previousProps.sectionType];
    if (activityRecords && activityRecords.pageInfo
      && activityRecords.pageInfo.hasNextPage
      && (this._countExpandedRecords() < 10)) {
      this._loadMore();
    }
  }

  componentWillUnmount() {
    this._isMounted = false;

    window.removeEventListener('visibilitychange', this._handleVisibilityChange);
    window.removeEventListener('focus', this._pollForActivity);
    window.removeEventListener('scroll', this._handleScroll);
  }

  /**
   * @param {}
   * scroll to top of page
   * deletes activity feed in the relay store
   * resets counter
   * calls restart function
   * removes scroll listener
   * @return {}
   */
  _scrollTo = () => {
    if (document.documentElement.scrollTop === 0) {
      const { relay, sectionType } = this.props;
      const relayStore = relay.environment.getStore();
      const section = this.props[sectionType];

      section.activityRecords.edges.forEach((edge) => {
        relayStore._recordSource.delete(edge.node.id);
      });

      this._refetch();

      window.removeEventListener('scroll', this._scrollTo);
    }
  }

  /**
   * @param {}
   * handles refiring new activity query if visibility changes back to visible
   * @return {}
   */
  _handleVisibilityChange = () => {
    if (document.hasFocus()) {
      this._pollForActivity();
    }
  }

  /**
   * @param {}
   * sets scroll listener
   * kicks off scroll to top
   * @return {}
   */
  _getNewActivities = () => {
    window.addEventListener('scroll', this._scrollTo);

    this.setState({ newActivityAvailable: false });

    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    });
  }

  /**
   * @param {}
   * sets hovered rollback position
   * @return {}
   */
  _setHoveredRollback = (position) => {
    const { props } = this;
    if (!props.isLocked) {
      this.setState({ hoveredRollback: position });
    }
  }

  /**
   * @param {}
   * stops refetch from firing
   * @return {}
   */
  _pollForActivity = () => {
    const self = this;
    const {
      sectionType,
      name,
      owner,
    } = this.props;

    this.setState({ newActivityAvailable: false });

    const getNewActivity = () => {
      NewActivity.getNewActivity(
        name,
        owner,
        sectionType,
      ).then((response) => {
        const section = this.props[sectionType];
        const firstRecordCommitId = (section && section.activityRecords)
          ? section.activityRecords.edges[0].node.commit
          : null;
        const newRecordCommitId = response.data[sectionType].activityRecords.edges[0].node.commit;

        if ((firstRecordCommitId !== newRecordCommitId)
          && (firstRecordCommitId !== null)) {
          const { automaticRefetch } = self.state;
          if (automaticRefetch) {
            this._refetch();
          } else {
            this.setState({ newActivityAvailable: true });
          }
        }

        if (self._isMounted && document.hasFocus()) {
          setTimeout(() => { getNewActivity(); }, 3000);
        }
      }).catch(error => console.log(error));
    };

    getNewActivity();
  }

  /**
  * @param {}
  * refetches component looking for new edges to insert at the top of the activity feed
  * @return {}
  */
   _refetch = () => {
     const { relay } = this.props;

     this.setState({ newActivityAvailable: false });

     relay.refetchConnection(
       5,
       (response, error) => {
         if (error) {
           console.log(response, error);
         }
       },
       {
         filters: [],
       },
     );
   }

  /**
  *  @param {}
  *  pagination container loads more items
  */
  _loadMore = () => {
    const { loadingMore } = this.state;
    const { sectionType, relay } = this.props;
    const section = this.props[sectionType];
    const { activityRecords } = section;
    const cursor = activityRecords && activityRecords.pageInfo
      ? activityRecords.pageInfo.endCursor
      : null;

    if (relay.isLoading() || loadingMore) {
      return;
    }

    this.setState({ loadingMore: true });

    relay.loadMore(
      5, // Fetch the next 5 feed items
      (error) => {
        if (error) {
          console.error(error);
        }
        this.setState({ loadingMore: false });
      }, {
        name: section,
        cursor,
        filters: [],
      },
    );
  }

  /**
  *  @param {}
  *  counts visible non clustered activity records
  */
  _countExpandedRecords = () => {
    const { sectionType } = this.props;
    const section = this.props[sectionType];
    const records = (section.activityRecords !== undefined) ? section.activityRecords.edges : [];

    let hiddenCount = 0;
    let recordCount = 0;

    const visibleRecords = records.filter((record) => {
      if (record) {
        if (!record.node.show) {
          hiddenCount += 1;
        } else if (hiddenCount > 2) {
          hiddenCount = 0;
          recordCount += 1;
        }
      }

      return record && record.node && record.node.show;
    });

    if (hiddenCount > 0) {
      recordCount += 1;
    }

    return visibleRecords.length + recordCount;
  }

  /**
    *  @param {}
    *   determines value of stickyDate by checking vertical offset and assigning it to the state
    *
  */
  _setStickyDate = () => {
    const { props, state } = this;
    let offsetAmount = ((window.location.hostname === config.demoHostName) || props.diskLow)
      ? 50 : 0;
    offsetAmount = props.isDeprecated ? offsetAmount + 70 : offsetAmount;
    const upperBound = offsetAmount + 120;
    let stickyDate = null;

    this.offsetDistance = window.pageYOffset;
    this.dates.forEach((date) => {
      if (date && date.e) {
        const bounds = date.e.getBoundingClientRect();

        if (bounds.top < upperBound) {
          stickyDate = date.time;
          date.e.classList.add('not-visible');
          if (date.e.nextSibling) {
            date.e.nextSibling.classList.add('next-element');
          }
        } else {
          date.e.classList.remove('not-visible');
          if (date.e.nextSibling) {
            date.e.nextSibling.classList.remove('next-element');
          }
        }
      }
    });

    if (stickyDate !== state.stickyDate) {
      this.setState({ stickyDate });
    }
  }

  /**
   * @param {String} timestamp
   * @param {Number} index
   * @param {Object} timestamp
   */
  _getOrCreateRef = (timestamp, index, evt) => {
    if (!this.dates[index]) {
      this.dates.push({ time: timestamp, e: evt });
    }
    return this.dates[timestamp];
  }

  /**
  *  @param {evt}
  *   handles scolls and passes off loading to pagination container
  *
  */
  _handleScroll = () => {
    const { automaticRefetch } = this.state;
    const distanceY = window.innerHeight + document.documentElement.scrollTop + 1000;

    this._setStickyDate();
    // has to be 3000 to accomodate for large monitors
    if (automaticRefetch !== (distanceY < 3000)) {
      console.log(automaticRefetch);
      this.setState({ automaticRefetch: (distanceY < 3000) });
    }
  }

  /**
  *   @param {}
  *   hides add activity
  *   @return {}
  */
  _hideAddActivity = () => {
    this.setState({
      modalVisible: false,
    });
  }

  /**
  *   @param {}
  *   hides add activity
  *   @return {}
  */
  _toggleRollbackMenu = (node) => {
    const { status } = store.getState().containerStatus;
    const { activeBranch, description } = this.props;
    const canEditEnvironment = config.containerStatus.canEditEnvironment(status);

    if (canEditEnvironment) {
      const selectedNode = {
        activityNode: node,
        activeBranch,
        description,
      };
      this.setState({ selectedNode, createBranchVisible: true });
    } else {
      setContainerMenuWarningMessage('Stop Project before editing the environment. \n Be sure to save your changes.');
    }
  }

  /**
  *   @param {}
  *   toggle create branch modal visibility
  *   @return {}
  */
  _toggleCreateModal = () => {
    const { createBranchVisible } = this.state;
    this.setState({ createBranchVisible: !createBranchVisible });
  }

  /**
  *   @param {}
  *   opens create branch modal and also sets selectedNode to null
  *   @return {}
  */
  _createBranch = () => {
    const { status } = store.getState().containerStatus;
    const canEditEnvironment = config.containerStatus.canEditEnvironment(status);
    if (canEditEnvironment) {
      this.setState({ createBranchVisible: true, selectedNode: null });
    } else {
      setContainerMenuWarningMessage('Stop Project before creating branches. \n Be sure to save your changes.');
    }
  }

  /**
  *   @param {boolean} isFullscreen
  *   Changes editorFullscreen in state to true if
  *   isFullscreen is true, else it swaps existing state
  *   @return {}
  */
  _changeFullscreenState = (isFullscreen) => {
    if (isFullscreen) {
      this.setState({ editorFullscreen: isFullscreen });
    } else {
      const { editorFullscreen } = this.state;
      this.setState({ editorFullscreen: !editorFullscreen });
    }
  }

  /**
  *   @param {array} clusterElements
  *   modifies expandedClusterObject from state
  *   @return {}
  */
  _expandCluster = (indexItem) => {
    const { activityRecords } = this.state;
    activityRecords[indexItem.timestamp][indexItem.j].cluster = true;

    this.setState({ activityRecords });
  }

  /**
    *   @param {array} clusterElements
    *   modifies expandedClusterObject from state
    *   @return {}
  */
  _addCluster = (clusterElements) => {
    const { sectionType } = this.props;
    const { expandedClusterObject } = this.state;
    const section = this.props[sectionType];
    const newExpandedClusterObject = new Map(expandedClusterObject);

    if (newExpandedClusterObject !== {}) {
      clusterElements.forEach((val) => {
        newExpandedClusterObject.delete(val);
      });
    }

    this.setState({ expandedClusterObject: newExpandedClusterObject }, () => {
      this.setState({ activityRecords: transformActivity(section.activityRecords) });
      this._compressExpanded(clusterElements, true);
    });
  }

  /**
  *   @param {array} clusterElements
  *   @param {boolean} remove
  *   adds or removes elements to cluster on expand and collapse
  *   @return {}
  */
  _compressExpanded = (clusterElements, remove) => {
    const { compressedElements } = this.state;
    const newCompressedElements = new Set(compressedElements);

    if (remove) {
      clusterElements.forEach((val) => {
        newCompressedElements.delete(val);
      });
    } else {
      clusterElements.forEach((val) => {
        newCompressedElements.add(val);
      });
    }
    this.setState({ compressedElements: newCompressedElements });
  }

  render() {
    const {
      activityRecords,
      clusterObject,
      compressedElements,
      createBranchVisible,
      editorFullscreen,
      hoveredRollback,
      isMainWorkspace,
      modalVisible,
      newActivityAvailable,
      selectedNode,
      stickyDate,
    } = this.state;
    const {
      owner,
      name,
      activeBranch,
      diskLow,
      sectionType,
      isDeprecated,
      setBuildingState,
    } = this.props;
    const section = this.props[sectionType];
    const isDemo = (window.location.hostname === config.demoHostName);
    // declare css here
    const activityCSS = classNames({
      Activity: true,
      fullscreen: editorFullscreen,
    });
    const newActivityCSS = classNames({
      'Activity__new-record box-shadow': true,
      'is-demo': (isDemo || diskLow),
      'is-deprecated': isDeprecated,
      'is-demo-deprecated': (isDemo || diskLow) && isDeprecated,
    });

    if (section && section.activityRecords) {
      const recordDates = Object.keys(activityRecords);
      const stickyDateCSS = classNames({
        'Activity__date-tab': true,
        fixed: stickyDate,
        'is-demo': (isDemo || diskLow),
        'is-deprecated': isDeprecated,
        'is-demo-deprecated': (isDemo || diskLow) && isDeprecated,
      });

      return (
        <div
          key={sectionType}
          className={activityCSS}
        >
          {
            newActivityAvailable
            && (
            <div className="Activity__new-record-wrapper column-1-span-9">
              <button
                type="button"
                onClick={() => this._getNewActivities()}
                className={newActivityCSS}
              >
                New Activity
              </button>
            </div>
            )
          }
          {
            stickyDate
            && (
            <div className={stickyDateCSS}>
              <div className="Activity__date-day">{stickyDate.split('_')[2]}</div>
              <div className="Activity__date-sub">

                <div className="Activity__date-month">
                  {
                    config.months[parseInt(stickyDate.split('_')[1], 10)]
                  }
                </div>

                <div className="Activity__date-year">{stickyDate.split('_')[0]}</div>
              </div>
            </div>
            )

          }

          <div
            key={`${sectionType}_labbooks__container`}
            className="Activity__inner-container flex flex--row flex--wrap justify--flex-start"
          >
            <div
              key={`${sectionType}_labbooks__labook-id-container`}
              className="Activity__sizer flex-1-0-auto"
            >
              <Tooltip section="userNote" />
              <CreateBranch
                owner={owner}
                name={name}
                selected={selectedNode}
                activeBranch={activeBranch}
                modalVisible={createBranchVisible}
                toggleModal={this._toggleCreateModal}
                setBuildingState={setBuildingState}
              />
              <InfiniteScroll
                pageStart={0}
                loadMore={this._loadMore}
                hasMore={section.activityRecords.pageInfo.hasNextPage}
                loader={<PaginationLoader key="paginationLoader" index={0} isLoadingMore />}
                useWindow
              >
                {
                  recordDates.map((timestamp, index) => (
                    <DateSection
                      key={timestamp}
                      {...this.props}
                      activityRecords={activityRecords}
                      clusterObject={clusterObject}
                      compressedElements={compressedElements}
                      editorFullscreen={editorFullscreen}
                      hoveredRollback={hoveredRollback}
                      index={index}
                      isMainWorkspace={isMainWorkspace}
                      modalVisible={modalVisible}
                      recordDates={recordDates}
                      section={section}
                      timestamp={timestamp}

                      addCluster={this._addCluster}
                      changeFullscreenState={this._changeFullscreenState}
                      compressExpanded={this._compressExpanded}
                      getOrCreateRef={this._getOrCreateRef}
                      hideAddActivity={this._hideAddActivity}
                      setHoveredRollback={this._setHoveredRollback}
                      toggleRollbackMenu={this._toggleRollbackMenu}

                    />
                  ))
                }
              </InfiniteScroll>
            </div>
          </div>
        </div>
      );
    }
    return (
      <Loader />
    );
  }
}

export default Activity;
