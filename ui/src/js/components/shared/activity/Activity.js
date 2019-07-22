// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import { setContainerMenuWarningMessage } from 'JS/redux/actions/labbook/environment/environment';
import { boundMethod } from 'autobind-decorator';
import shallowCompare from 'react-addons-shallow-compare';
// store
import store from 'JS/redux/store';
// config
import config from 'JS/config';
// Components
import Loader from 'Components/common/Loader';
import Tooltip from 'Components/common/Tooltip';
import CreateBranch from 'Components/shared/modals/CreateBranch';
import PaginationLoader from './loaders/PaginationLoader';
import ClusterCardWrapper from './wrappers/ClusterCardWrapper';
import CardWrapper from './wrappers/CardWrapper';
import UserNoteWrapper from './wrappers/UserNoteWrapper';

// utils
import NewActivity from './NewActivity';
// assets
import './Activity.scss';


/**
*   @param {array}
*   loops through activityRecords array and sorts into days
*   @return {Object}
*/
const transformActivity = (activityRecords, state) => {
  const activityTime = {};

  let count = 0;
  let previousTimeHash = null;
  let clusterIndex = 0;

  if (activityRecords) {
    activityRecords.edges.forEach((edge, index) => {
      if (edge && edge.node) {
        const date = (edge.node && edge.node.timestamp)
          ? new Date(edge.node.timestamp)
          : new Date();
        const year = date.getFullYear();
        const month = date.getMonth();
        const day = date.getDate();
        const timeHash = `${year}_${month}_${day}`;

        count = (edge.node.show || (previousTimeHash && (timeHash !== previousTimeHash)))
          ? 0
          : count + 1;

        if (count === 0) {
          clusterIndex = 0;
        }
        previousTimeHash = timeHash;

        const isExpandedHead = state && state.expandedClusterObject.has(index)
          && !state.expandedClusterObject.has(index - 1);
        const isExpandedEnd = state && state.expandedClusterObject.has(index)
          && !state.expandedClusterObject.has(index + 1);
        const isExpandedNode = state && state.expandedClusterObject.has(index);
        const attachedCluster = state && state.expandedClusterObject.has(index)
          && state.expandedClusterObject.get(index);
        const newActivityObject = {
          edge,
          date,
          collapsed: ((count > 2)
            && ((state && !state.expandedClusterObject.has(index))
            || (!state))),
          flatIndex: index,
          isExpandedHead,
          isExpandedEnd,
          isExpandedNode,
          attachedCluster,
        };

        if (count > 2 && ((state && !state.expandedClusterObject.has(index)) || (!state))) {
          if (count === 3) {
            const activityOne = activityTime[timeHash][activityTime[timeHash].length - 1];
            activityTime[timeHash][activityTime[timeHash].length - 1].collapsed = true;

            const activityTwo = activityTime[timeHash][activityTime[timeHash].length - 2];
            activityTime[timeHash][activityTime[timeHash].length - 2].collapsed = true;

            const clusterObject = {
              cluster: [activityTwo, activityOne, newActivityObject],
              attachedCluster,
              expanded: false,
              id: activityOne.edge.node.id,
            };

            activityTime[timeHash].pop();
            activityTime[timeHash].pop();

            if (activityTime[timeHash]) {
              activityTime[timeHash].push(clusterObject);
            } else {
              activityTime[timeHash] = [clusterObject];
            }

            clusterIndex = activityTime[timeHash].length - 1;
          } else {
            activityTime[timeHash][clusterIndex].cluster.push(newActivityObject);
          }
        } else {
          clusterIndex = 0;
          if (activityTime[timeHash]) {
            activityTime[timeHash].push(newActivityObject);
          } else {
            activityTime[timeHash] = [newActivityObject];
          }
        }
      }
    });
    return activityTime;
  }
  return [];
};


/**
*   @param {event} evt
*   assigns open-menu class to parent element and ActivityExtended to previous element
*   @return {}
*/
const toggleSubmenu = (evt) => {
  const submenu = evt.target.parentElement;
  const wrapper = submenu && submenu.parentElement;

  if (wrapper.previousSibling) {
    if (wrapper.previousSibling.className.indexOf('ActivityExtended') !== -1) {
      wrapper.previousSibling.classList.remove('ActivityExtended');
    } else {
      wrapper.previousSibling.classList.add('ActivityExtended');
    }
  } else if (wrapper.parentElement.previousSibling.className.indexOf('ActivityExtended') !== -1) {
    wrapper.parentElement.previousSibling.classList.remove('ActivityExtended');
  } else {
    wrapper.parentElement.previousSibling.classList.add('ActivityExtended');
  }

  if (submenu.className.indexOf('open-menu') !== -1) {
    submenu.classList.remove('open-menu');
  } else {
    submenu.classList.add('open-menu');
  }
};

class Activity extends Component {
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
    this.dates = [];
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
    const { props } = this;

    props.refetch('activity');
    this._isMounted = true;

    window.addEventListener('scroll', this._handleScroll);
    window.addEventListener('visibilitychange', this._handleVisibilityChange);

    if (props.sectionType === 'labbook') {
      window.addEventListener('focus', this._pollForActivity);
      this._pollForActivity();
    }
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
    const { props } = this;
    this._isMounted = false;

    window.removeEventListener('visibilitychange', this._handleVisibilityChange);
    window.removeEventListener('scroll', this._handleScroll);

    if (props.sectionType === 'labbook') {
      window.removeEventListener('focus', this._pollForActivity);
    }
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
  @boundMethod
  _scrollTo(evt) {
    if (document.documentElement.scrollTop === 0) {
      const { props } = this;
      const { relay } = props;
      const store = relay.environment.getStore();
      const section = props[props.sectionType];

      section.activityRecords.edges.forEach((edge) => {
        store._recordSource.delete(edge.node.id);
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
  @boundMethod
  _handleVisibilityChange() {
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
  @boundMethod
  _getNewActivities() {
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
  @boundMethod
  _setHoveredRollback(position) {
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
   @boundMethod
  _pollForActivity() {
    const self = this;
    const { props } = this;

    this.setState({ newActivityAvailable: false });

    const { labbookName, owner } = store.getState().routes;

    const getNewActivity = () => {
      NewActivity.getNewActivity(labbookName, owner).then((response) => {

        const firstRecordCommitId = (props.labbook && props.labbook.activityRecords)
          ? this.props.labbook.activityRecords.edges[0].node.commit
          : null;
        const newRecordCommitId = response.data.labbook.activityRecords.edges[0].node.commit;

        if ((firstRecordCommitId !== newRecordCommitId) && (firstRecordCommitId !== null)) {
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
  @boundMethod
   _refetch() {
     const { props } = this;
     const { relay } = props;

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
  @boundMethod
  _loadMore() {
    const { props } = this;
    const section = props[props.sectionType];
    const { activityRecords } = section;
    const cursor = activityRecords && activityRecords.pageInfo
      ? activityRecords.pageInfo.endCursor
      : null;

    if (props.relay.isLoading()) {
      return;
    }

    this.setState({ loadingMore: true });

    props.relay.loadMore(
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
  @boundMethod
  _countExpandedRecords() {
    const { props } = this;
    const section = props[props.sectionType];
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
  @boundMethod
  _setStickyDate() {
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
  *  @param {evt}
  *   handles scolls and passes off loading to pagination container
  *
  */
  @boundMethod
  _handleScroll(evt) {
    const { props, state } = this;
    const section = props[props.sectionType];
    const { activityRecords } = section;
    const root = document.getElementById('root');
    const distanceY = window.innerHeight + document.documentElement.scrollTop + 1000;
    const expandOn = root.scrollHeight;

    this._setStickyDate();

    if ((distanceY > expandOn) && activityRecords.pageInfo.hasNextPage) {
      this._loadMore(evt);
    }
    // has to be 3000 to accomodate for large monitors
    if (state.automaticRefetch !== (distanceY < 3000)) {
      this.setState({ automaticRefetch: (distanceY < 3000) });
    }
  }

  /**
  *   @param {}
  *   toggles activity visibility
  *   @return {}
  */
  @boundMethod
  _toggleActivity() {
    const { modalVisible } = this.state;
    this.setState({
      modalVisible: !modalVisible,
    });
  }

  /**
  *   @param {}
  *   hides add activity
  *   @return {}
  */
  @boundMethod
  _hideAddActivity() {
    this.setState({
      modalVisible: false,
    });
  }

  /**
  *   @param {}
  *   hides add activity
  *   @return {}
  */
  @boundMethod
  _toggleRollbackMenu(node) {
    const { status } = store.getState().containerStatus;
    const { props } = this;
    const canEditEnvironment = config.containerStatus.canEditEnvironment(status);
    if (canEditEnvironment) {
      const selectedNode = {
        activityNode: node,
        activeBranch: props.activeBranch,
        description: props.description,
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
  @boundMethod
  _toggleCreateModal() {
    const { createBranchVisible } = this.state;
    this.setState({ createBranchVisible: !createBranchVisible });
  }

  /**
  *   @param {}
  *   opens create branch modal and also sets selectedNode to null
  *   @return {}
  */
  @boundMethod
  _createBranch() {
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
  @boundMethod
  _changeFullscreenState(isFullscreen) {
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
  @boundMethod
  _expandCluster(indexItem) {
    const { state } = this;
    const { activityRecords } = state;
    activityRecords[indexItem.timestamp][indexItem.j].cluster = true;

    this.setState({ activityRecords });
  }

  /**
    *   @param {array} clusterElements
    *   modifies expandedClusterObject from state
    *   @return {}
  */
  @boundMethod
  _addCluster(clusterElements) {
    const { props, state } = this;
    const section = props[props.sectionType];
    const newExpandedClusterObject = new Map(state.expandedClusterObject);

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
  @boundMethod
  _compressExpanded(clusterElements, remove) {
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
    const { props, state } = this;
    const section = props[props.sectionType];

    const activityCSS = classNames({
      Activity: true,
      fullscreen: state.editorFullscreen,
    });
    const newActivityCSS = classNames({
      'Activity__new-record box-shadow': true,
      'is-demo': ((window.location.hostname === config.demoHostName) || props.diskLow),
      'is-deprecated': props.isDeprecated,
      'is-demo-deprecated': ((window.location.hostname === config.demoHostName) || props.diskLow) && props.isDeprecated,
    });

    if (section && section.activityRecords) {
      const recordDates = Object.keys(state.activityRecords);
      const stickyDateCSS = classNames({
        'Activity__date-tab': true,
        fixed: state.stickyDate,
        'is-demo': ((window.location.hostname === config.demoHostName) || props.diskLow),
        'is-deprecated': props.isDeprecated,
        'is-demo-deprecated': ((window.location.hostname === config.demoHostName) || props.diskLow) && props.isDeprecated,
      });

      return (
        <div
          key={props.sectionType}
          className={activityCSS}
        >
          {
            state.newActivityAvailable
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
            state.stickyDate
            && (
            <div className={stickyDateCSS}>
              <div className="Activity__date-day">{state.stickyDate.split('_')[2]}</div>
              <div className="Activity__date-sub">

                <div className="Activity__date-month">
                  {
                    config.months[parseInt(state.stickyDate.split('_')[1], 10)]
                  }
                </div>

                <div className="Activity__date-year">{state.stickyDate.split('_')[0]}</div>
              </div>
            </div>
            )

          }

          <div
            key={`${props.sectionType}_labbooks__container`}
            className="Activity__inner-container flex flex--row flex--wrap justify--flex-start"
          >
            <div
              key={`${props.sectionType}_labbooks__labook-id-container`}
              className="Activity__sizer flex-1-0-auto"
            >
              <Tooltip section="userNote" />
              <CreateBranch
                selected={state.selectedNode}
                activeBranch={props.activeBranch}
                modalVisible={state.createBranchVisible}
                toggleModal={this._toggleCreateModal}
                setBuildingState={props.setBuildingState}
              />
              {
                recordDates.map((timestamp, i) => {
                  const clusterElements = [];
                  const activityDateCSS = classNames({
                    'Activity__date-tab': true,
                    note: (i === 0),
                  });
                  const activityContainerCSS = classNames({
                    'Activity__card-container': true,
                    'Activity__card-container--last': recordDates.length === i + 1,
                  });

                  const dataSectionCSS = classNames({
                    [`Activity__date-section Activity__date-section--${i}`]: true,
                  });

                  return (
                    <div
                      key={timestamp}
                      className={dataSectionCSS}
                    >
                      <div
                        ref={evt => this.dates[i] = { e: evt, time: timestamp }}
                        className={activityDateCSS}
                      >

                        <div className="Activity__date-day">
                          { timestamp.split('_')[2] }
                        </div>

                        <div className="Activity__date-sub">

                          <div className="Activity__date-month">
                            { config.months[parseInt(timestamp.split('_')[1], 10)] }
                          </div>

                          <div className="Activity__date-year">
                            {timestamp.split('_')[0]}
                          </div>
                        </div>
                      </div>
                      {
                        (i === 0)
                        && (
                        <UserNoteWrapper
                          modalVisible={state.modalVisible}
                          hideLabbookModal={this._hideAddActivity}
                          changeFullScreenState={this._changeFullscreenState}
                          labbookId={section.id}
                          editorFullscreen={state.editorFullscreen}
                          {...props}
                        />
                        )
                      }
                      <div
                        key={`${timestamp}__card`}
                        className={activityContainerCSS}
                      >
                        {
                          state.activityRecords[timestamp].map((record, timestampIndex) => {
                            if (record.cluster) {
                              return (
                                <ClusterCardWrapper
                                  sectionType={props.sectionType}
                                  isMainWorkspace={props.isMainWorkspace}
                                  section={section}
                                  activityRecords={state.activityRecords}
                                  key={`ClusterCardWrapper_${timestamp}_${record.id}`}
                                  record={record}
                                  hoveredRollback={state.hoveredRollback}
                                  indexItem={{ i, timestampIndex, timestamp }}
                                  toggleSubmenu={toggleSubmenu}
                                  toggleRollbackMenu={this._toggleRollbackMenu}
                                  isLocked={props.isLocked}
                                  setHoveredRollback={this._setHoveredRollback}
                                />
                              );
                            }

                            return (
                              <CardWrapper
                                section={section}
                                isMainWorkspace={props.isMainWorkspace}
                                activityRecords={state.activityRecords}
                                clusterElements={clusterElements}
                                sectionType={props.sectionType}
                                record={record}
                                compressExpanded={this._compressExpanded}
                                clusterObject={state.clusterObject}
                                compressedElements={state.compressedElements}
                                hoveredRollback={state.hoveredRollback}
                                indexItem={{ i, timestampIndex, timestamp }}
                                addCluster={this._addCluster}
                                key={`VisibileCardWrapper_${record.flatIndex}`}
                                toggleSubmenu={toggleSubmenu}
                                toggleRollbackMenu={this._toggleRollbackMenu}
                                isLocked={props.isLocked}
                                setHoveredRollback={this._setHoveredRollback}
                              />
                            );
                          })
                        }
                      </div>
                    </div>
                  );
                })
              }
              {
                Array(5).fill(1).map((value, index) => (
                  <PaginationLoader
                    key={`Actvity_paginationLoader${index}`}
                    index={index}
                    isLoadingMore={state.loadingMore
                      || ((state.activityCardCount < 10)
                      && section.activityRecords.pageInfo.hasNextPage)
                    }
                  />
                ))
              }
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
