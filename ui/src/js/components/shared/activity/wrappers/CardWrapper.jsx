// @flow
// vendor
import React, { PureComponent, Fragment } from 'react';
import classNames from 'classnames';
// components
import ErrorBoundary from 'Components/common/ErrorBoundary';
import ActivityCard from './card/ActivityCard';
import Rollback from './Rollback';
// assets
import './CardWrapper.scss';

type Props = {
  hoveredRollback: Function,
  indexItem: {
    timestampIndex: Number,
  },
  isLocked: Function,
  name: String,
  owner: String,
  record: {
    edge: {
      node: {
        detailObjects: Array<Object>,
      }
    }
  },
  sectionType: String,
  setHoveredRollback: Function,
  toggleRollbackMenu: Function,
}

/**
* Returns if the record has a rollback option
* @param {Object} props
*
* @return {Boolean}
*/

const getHasRollback = (props) => {
  const {
    isBaseRecord,
    indexItem,
    record,
    sectionType,
  } = props;
  const rollbackDetails = record.edge && record.edge.node.detailObjects.filter(detailObjs => (detailObjs.type !== 'RESULT') && (detailObjs.type !== 'CODE_EXECUTED'));
  const isLabbook = (sectionType === 'labbook');
  const hasRollbackDetails = !!rollbackDetails.length;
  const isNotFirstIndex = (indexItem.i !== 0) || (indexItem.timestampIndex !== 0);
  const hasRollback = (isNotFirstIndex)
          && (hasRollbackDetails && isLabbook)
          && !isBaseRecord;

  return hasRollback;
};

class CardWrapper extends PureComponent<Props> {
  render() {
    const {
      hoveredRollback,
      indexItem,
      isLocked,
      name,
      owner,
      record,
      sectionType,
      setHoveredRollback,
      toggleRollbackMenu,
    } = this.props;
    const hasRollback = getHasRollback(this.props);
    // declare css here
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
                setHoveredRollback={setHoveredRollback}
                hoveredRollback={hoveredRollback}
                toggleRollbackMenu={toggleRollbackMenu}
                record={record}
                sectionType={sectionType}
                isLocked={isLocked}
              />
            )
          }

          <ErrorBoundary
            type="activityCardError"
            key={`activityCard${record.edge.node.id}`}
          >
            <ActivityCard
              sectionType={sectionType}
              hoveredRollback={hoveredRollback}
              isFirstCard={indexItem.timestampIndex === 0}
              position={record.flatIndex}
              key={`${record.edge.node.id}_activity-card`}
              edge={record.edge}
              isLocked={isLocked}
              owner={owner}
              name={name}
            />
          </ErrorBoundary>

        </div>

      </Fragment>
    );
  }
}

export default CardWrapper;
