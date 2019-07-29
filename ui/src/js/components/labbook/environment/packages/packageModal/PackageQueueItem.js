// vendor
import React, { Component } from 'react';
// components
import PackageStatus from './PackageStatus';
// assets
import './PackageQueue.scss';

/**
*  @param {Object} props
*  @param {Object} pkg
*  sets which packages are being edited
*  @return {}
*/
const getRenderingData = (props, pkg) => {
  const isEdited = props.editedPackageRows[pkg.manager]
    && props.editedPackageRows[pkg.manager].has(pkg.package);
  const newPackageName = isEdited
    && props.editedPackageRows[pkg.manager].get(pkg.package).newPackageName;
  const newPackageVersion = isEdited
    && props.editedPackageRows[pkg.manager].get(pkg.package).newPackageVersion;

  return {
    isEdited,
    newPackageName,
    newPackageVersion,
  };
};

class PackageQueueItem extends Component {
  state = {
    removePopups: false,
  }
  /**
  *  @param {Object} evt
  *  @param {Object} pkg
  *  @param {Number} index
  *  @param {String} type
  *  sets which packages are being edited
  *  @return {}
  */

  componentDidMount() {
    this.rowContainer.addEventListener('scroll', this._handleScroll);
  }

  componentWillUnmount() {
    this.rowContainer.removeEventListener('scroll', this._handleScroll);
  }

  /**
  *  @param {} -
  *  sets which packages are being edited
  *  @return {}
  */
  _handleScroll = () => {
    this.setState({ removePopups: true });

    setTimeout(() => {
      this.setState({ removePopups: false });
    }, 250);
  }

  /**
  *  @param {Object} evt
  *  @param {Object} pkg
  *  @param {Number} index
  *  @param {String} type
  *  updates package
  *  @calls {updatePackage}
  *  @return {}
  */
  _updatePackage(evt, pkg, index, type) {
    const { updatePackage } = this.props;

    updatePackage(evt, pkg.manager, pkg.package, pkg.version, index, type);
  }

  render() {
    const { props, state } = this;
    return (
      <div
        className="PackageQueue__row-container"
        ref={(rowContainer) => { this.rowContainer = rowContainer; }}
      >
        {
          props.packageQueue.map((pkg, index) => {
            const {
              isEdited,
              newPackageName,
              newPackageVersion,
            } = getRenderingData(props, pkg);

            return (
              <div
                className="PackageQueue__row flex align-items--center justify--right"
                key={`${pkg.manager}-${pkg.package}`}
              >
                <button
                  className="Btn Btn--round Btn--small Btn__subtract"
                  type="button"
                  onClick={() => props.removePackageFromQueue(index)}
                />
                <div className="PackageQueue__manager">
                  {pkg.manager}
                </div>
                <div className="PackageQueue__name flex--1">
                  { isEdited
                    ? (
                      <input
                        type="text"
                        className="Input--smallText"
                        defaultValue={pkg.package}
                        onChange={evt => this._updatePackage(evt, pkg, index, 'newPackageName')}
                        onKeyDown={evt => this._updatePackage(evt, pkg, index, 'newPackageName')}
                      />
                    )
                    : pkg.package
                  }
                </div>
                <div className="PackageQueue__version">
                  { isEdited
                    ? (
                      <input
                        type="text"
                        className="Input--smallText"
                        disabled={pkg.manager === 'apt'}
                        onChange={evt => this._updatePackage(evt, pkg, index, 'newPackageVersion')}
                        onKeyDown={evt => this._updatePackage(evt, pkg, index, 'newPackageVersion')}
                        defaultValue={pkg.version}
                      />
                    )
                    : pkg.version
                  }
                </div>
                <div className="PackageQueue__status">
                  <PackageStatus
                    queuePackage={props.queuePackage}
                    pkg={pkg}
                    verified={pkg.verified}
                    version={pkg.version}
                    error={pkg.error}
                    packageManager={pkg.manager}
                    packageName={pkg.package}
                    setEditedPackageRows={props.setEditedPackageRows}
                    index={index}
                    newPackageName={newPackageName}
                    newPackageVersion={newPackageVersion}
                    removePackageFromQueue={props.removePackageFromQueue}
                    isEdited={isEdited}
                    removeEditedPackageRows={props.removeEditedPackageRows}
                    removePopups={state.removePopups}
                    packageCount={props.packageQueue.length}
                  />
                </div>
              </div>
            );
          })
        }
      </div>
    );
  }
}

export default PackageQueueItem;
