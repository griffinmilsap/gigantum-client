// @flow
// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// components
import Tooltip from 'Components/common/Tooltip';
import CardWrapper from './CardWrapper';
// Styles
import './ClusterCardWrapper.scss';

type Props = {
  hoveredRollback: Boolean,
  isLocked: Boolean,
  record: {
    cluster: {
      expanded: Boolean,
    }
  },
  setHoveredRollback: Function,
  toggleSubmenu: Function,
}

class ClusterCardWrapper extends Component<Props> {
  state = {
    expanded: this.props.record.cluster.expanded,
    shrink: false,
  };

  /**
    @param {Object} evt
    toggles submenu
    @return {}
  */
  _toggleSubmenu = (evt) => {
    const { toggleSubmenu } = this.props;
    toggleSubmenu(evt);
  }

  /**
    @param {boolean} expanded
    sets state of cluster to expand or collapse
    @return {}
  */
  _toggleCluster = (expanded) => {
    this.setState({ expanded });
  }

  /**
    @param {Object} evt
    @param {boolean} shrink
    shrinks cards on mouseover to indicate collapse
    @return {}
  */
  _toggleShrink = (evt, shrink) => {
    this.setState({ shrink });
  }

  render() {
    const {
      shrink,
      expanded,
    } = this.state;
    const {
      hoveredRollback,
      isLocked,
      record,
      setHoveredRollback,
    } = this.props;
    const shouldBeFaded = hoveredRollback > record.flatIndex;

    // declare css here
    const clusterCSS = classNames({
      'ActivityCard--cluster': true,
      'column-1-span-9': true,
      faded: shouldBeFaded,
    });
    const clusterWrapperCSS = classNames({
      'ClusterCardWrapper flex justify--space-between flex--column': true,
      'ClusterCardWrapper--shrink': shrink,
    });

    if (!expanded) {
      return (
        <div className="CardWrapper CardWrapper--cluster">

          <Tooltip section="activityCluster" />

          <div
            className={clusterCSS}
            onClick={() => this._toggleCluster(true)}
            role="presentation"
          >
            <div className="ActivityCard__cluster--layer1 box-shadow">
              {`${record.cluster.length} Minor Activities`}
            </div>
            <div className="ActivityCard__cluster--layer2 box-shadow" />
            <div className="ActivityCard__cluster--layer3 box-shadow" />
          </div>
        </div>
      );
    }

    return (
      <div className={clusterWrapperCSS}>

        <div
          className="ClusterCard__sidebar-container"
          onMouseEnter={(evt) => { this._toggleShrink(evt, true); }}
          onMouseLeave={(evt) => { this._toggleShrink(evt, false); }}
          onClick={() => this._toggleCluster(false)}
          role="presentation"
        >
          <div className="ClusterCard__sidebar" />
        </div>
        {
          record.cluster.map(recordItem => (
            <CardWrapper
              {...this.props}
              key={`CardWrapper__${recordItem.edge.node.id}`}
              isLocked={isLocked}
              toggleCluster={this._toggleCluster}
              record={recordItem}
              setHoveredRollback={setHoveredRollback}
            />
          ))
        }
      </div>
    );
  }
}

export default ClusterCardWrapper;
