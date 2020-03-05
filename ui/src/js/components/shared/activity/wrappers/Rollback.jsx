// @flow
// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// components
import Tooltip from 'Components/common/Tooltip';
// assets
import './Rollback.scss';

type Props = {
  isLocked: Boolean,
  record: {
    edge: {
      node: Object,
    }
  },
  setHoveredRollback: Function,
  toggleRollbackMenu: Function,
}

class Rollback extends Component<Props> {
  /**
    @param {} -
    shows rollback modal, and passes record node to the modal
    @return {}
  */
  _toggleRollback = () => {
    const { record, toggleRollbackMenu } = this.props;
    toggleRollbackMenu(record.edge.node);
  }

  render() {
    const {
      isLocked,
      record,
      setHoveredRollback,
    } = this.props;

    // declare css here
    const rollbackCSS = classNames({
      Rollback: true,
      'Rollback--locked': isLocked,
      'Tooltip-data Tooltip-data--right': isLocked,
    });

    return (
      <div
        className={rollbackCSS}
        data-tooltip="Can't rollback when the container is running."
      >
        <Tooltip section="activitySubmenu" />
        <button
          type="button"
          disabled={isLocked}
          onMouseEnter={() => setHoveredRollback(record.flatIndex)}
          onMouseLeave={() => setHoveredRollback(null)}
          className="Rollback__button"
          onClick={() => this._toggleRollback()}
        >
              Rollback
        </button>
      </div>
    );
  }
}

export default Rollback;
