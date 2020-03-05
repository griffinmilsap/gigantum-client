// @flow
// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// config
import config from 'JS/config';
// components
import ClusterCardWrapper from '../wrappers/ClusterCardWrapper';
import CardWrapper from '../wrappers/CardWrapper';
import UserNoteWrapper from './note/UserNoteWrapper';
// utils
import { toggleSubmenu } from '../utils/ActivityUtils';

type Props = {
  activityRecords: Array<Object>,
  clusterObject: Object,
  compressedElements: Array,
  editorFullscreen: Boolean,
  hoveredRollback: Boolean,
  index: Number,
  isLocked: Boolean,
  isMainWorkspace: Boolean,
  modalVisible: Boolean,
  name: String,
  owner: String,
  recordDates: Array<Object>,
  section: {
    id: String,
  },
  sectionType: string,
  timestamp: String,

  addCluster: Function,
  changeFullscreenState: Function,
  compressExpanded: Function,
  hideAddActivity: Function,
  getOrCreateRef: Function,
  setHoveredRollback: Function,
  toggleRollbackMenu: Function,
}


class DateSection extends Component<Props> {
  state = {
    modalVisible: false,
  }

  render() {
    const {
      modalVisible,
    } = this.state;
    const {
      activityRecords,
      changeFullscreenState,
      clusterObject,
      compressedElements,
      editorFullscreen,
      hideAddActivity,
      hoveredRollback,
      index,
      isLocked,
      isMainWorkspace,
      name,
      owner,
      recordDates,
      section,
      sectionType,
      timestamp,
      // functions
      addCluster,
      compressExpanded,
      getOrCreateRef,
      setHoveredRollback,
      toggleRollbackMenu,
    } = this.props;
    const clusterElements = [];
    // declare css here
    const activityDateCSS = classNames({
      'Activity__date-tab': true,
      note: (index === 0),
    });
    const activityContainerCSS = classNames({
      'Activity__card-container': true,
      'Activity__card-container--last': recordDates.length === index + 1,
    });
    const dataSectionCSS = classNames({
      [`Activity__date-section Activity__date-section--${index}`]: true,
    });

    return (
      <div className={dataSectionCSS}>
        <div
          ref={evt => getOrCreateRef(timestamp, index, evt)}
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
          (index === 0)
          && (
          <UserNoteWrapper
            modalVisible={modalVisible}
            hideLabbookModal={hideAddActivity}
            changeFullScreenState={changeFullscreenState}
            labbookId={section.id}
            editorFullscreen={editorFullscreen}
            {...this.props}
          />
          )
        }
        <div
          key={`${timestamp}__card`}
          className={activityContainerCSS}
        >
          {
            activityRecords[timestamp].map((record, timestampIndex) => {
              const isBaseRecord = !section.activityRecords.pageInfo.hasNextPage
                && (section.activityRecords.edges.length - 1 === record.flatIndex);
              if (record.cluster) {
                return (
                  <ClusterCardWrapper
                    sectionType={sectionType}
                    isMainWorkspace={isMainWorkspace}
                    section={section}
                    activityRecords={activityRecords}
                    key={`ClusterCardWrapper_${timestamp}_${record.id}`}
                    record={record}
                    hoveredRollback={hoveredRollback}
                    indexItem={{ index, timestampIndex, timestamp }}
                    toggleSubmenu={toggleSubmenu}
                    toggleRollbackMenu={toggleRollbackMenu}
                    isLocked={isLocked}
                    setHoveredRollback={setHoveredRollback}
                    owner={owner}
                    name={name}
                  />
                );
              }
              const { edge } = record;
              return (
                <CardWrapper
                  section={section}
                  isBaseRecord={isBaseRecord}
                  isMainWorkspace={isMainWorkspace}
                  activityRecords={activityRecords}
                  clusterElements={clusterElements}
                  sectionType={sectionType}
                  record={record}
                  compressExpanded={compressExpanded}
                  clusterObject={clusterObject}
                  compressedElements={compressedElements}
                  hoveredRollback={hoveredRollback}
                  indexItem={{ index, timestampIndex, timestamp }}
                  addCluster={addCluster}
                  key={`VisibileCardWrapper_${edge.node.id}`}
                  toggleSubmenu={toggleSubmenu}
                  toggleRollbackMenu={toggleRollbackMenu}
                  isLocked={isLocked}
                  setHoveredRollback={setHoveredRollback}
                  owner={owner}
                  name={name}
                />
              );
            })
          }
        </div>
      </div>
    );
  }
}

export default DateSection;
