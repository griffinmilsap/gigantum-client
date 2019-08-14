// vendor
import React, { PureComponent, Fragment } from 'react';
import classNames from 'classnames';
// components
import ErrorBoundary from 'Components/common/ErrorBoundary';
import ActivityCard from '../ActivityCard';
import Rollback from './Rollback';
// assets
import './CardWrapper.scss';

export default class CardWrapper extends PureComponent {
  render() {
    const { props } = this;
    const { record } = props;

    const rollbackableDetails = record.edge.node.detailObjects.filter(detailObjs => detailObjs.type !== 'RESULT' && detailObjs.type !== 'CODE_EXECUTED');
    const isLabbook = (props.sectionType === 'labbook');
    const hasRollbackDetails = !!rollbackableDetails.length;
    const isNotFirstIndex = (props.indexItem.i !== 0) || (props.indexItem.timestampIndex !== 0);
    const hasRollback = (isNotFirstIndex)
            && (hasRollbackDetails && isLabbook)
            && !props.isBaseRecord;


    const activityCardWrapperCSS = classNames({
      CardWrapper: true,
      'CardWrapper--rollback': hasRollback,
    });

    return (
      <Fragment key={record.edge.node.id}>
        <div className={activityCardWrapperCSS}>

          { hasRollback
              && (
              <Rollback
                setHoveredRollback={props.setHoveredRollback}
                hoveredRollback={props.hoveredRollback}
                toggleRollbackMenu={props.toggleRollbackMenu}
                record={record}
                sectionType={props.sectionType}
                isLocked={props.isLocked}
              />
              )
          }

          <ErrorBoundary
            type="activityCardError"
            key={`activityCard${record.edge.node.id}`}
          >
            <ActivityCard
              sectionType={props.sectionType}
              hoveredRollback={props.hoveredRollback}
              isFirstCard={props.indexItem.timestampIndex === 0}
              position={record.flatIndex}
              key={`${record.edge.node.id}_activity-card`}
              edge={record.edge}
              isLocked={props.isLocked}
            />
          </ErrorBoundary>


        </div>

      </Fragment>
    );
  }
}
