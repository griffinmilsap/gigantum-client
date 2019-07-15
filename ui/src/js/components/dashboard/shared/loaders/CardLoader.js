// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// assets
import './CardLoader.scss';

export default class CardLoader extends Component {
  render() {
    const { props } = this;


    const loaderCSS = classNames({
      [`Card Card--225 column-4-span-3 flex flex--column justify--space-between CardLoader CardLoader--${props.index}`]: props.isLoadingMore,
      'CardLoader--hidden': !props.isLoadingMore,
    });

    return (
      <div
        key={`Card__loader--${this.props.index}`}
        className={loaderCSS}
      >
        <div />
      </div>
    );
  }
}
