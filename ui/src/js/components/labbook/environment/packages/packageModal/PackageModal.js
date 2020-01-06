// @flow
// vendor
import React, { Component } from 'react';
// components
import Modal from 'Components/common/Modal';
import BuildProgress from 'Components/common/BuildProgress';
import AddPackages from './AddPackages';

type Props = {
  togglePackageModal: Function
}

export default class PackageModal extends Component<Props> {
  state = {
    buildId: null,
  }

  /**
    @param {String} buildId
    updates buildId in state
  */
  _setBuildId = (buildId) => {
    this.setState({ buildId });
  }

  render() {
    const { togglePackageModal } = this.props;
    const { buildId } = this.state;
    return (
      <Modal
        size="large-full"
        handleClose={() => togglePackageModal(false)}
        renderContent={() => {
          if (!buildId) {
            return (
              <AddPackages
                {...this.props}
                setBuildId={this._setBuildId}
              />
            );
          }
          return (
            <BuildProgress
              {...this.props}
              toggleModal={togglePackageModal}
              headerText="Installing Packages"
              buildId={buildId}
            />
          );
        }}
      />
    );
  }
}
