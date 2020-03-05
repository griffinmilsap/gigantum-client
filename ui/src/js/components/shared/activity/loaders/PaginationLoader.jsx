// vendor
import React, { PureComponent } from 'react';
import classNames from 'classnames';

type Props = {
  index: Number,
  isLoadingMore: Function,
}

class PaginationLoader extends PureComponent<Props> {
  render() {
    const { isLoadingMore, index } = this.props;
    // declare css here
    const PaginationLoaderCSS = classNames({
      [`ActivityCard ActivityCard__loader ActivityCard__loader--${index} card`]: isLoadingMore,
      'ActivityCard ActivityCard__loader-hidden': !isLoadingMore,
      'column-1-span-9': true,
    });
    return (
      <div
        key="Activity-loader-card"
        className={PaginationLoaderCSS}
      />
    );
  }
}

export default PaginationLoader;
