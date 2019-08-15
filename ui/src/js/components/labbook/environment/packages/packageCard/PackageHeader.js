// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// components
import Tooltip from 'Components/common/Tooltip';
// assets
import './PackageHeader.scss';

export default class PackageHeader extends Component {
  /**
  *  @param{}
  *  removes all selected packages
  */
  _removePackages() {
    const { props } = this;
    const data = {
      packages: [...props.selectedPackages.values()],
    };
    const { owner, name } = props;
    props.setBuildingState(owner, name, true);
    const callback = () => {
      props.selectPackages(true);
      props.buildCallback();
    };
    props.packageMutations.removePackages(data, callback);
  }

  /**
  *  @param {Array} updateablePackages
  *  updates selected updateable packages
  */
  _updatePackages(updateablePackages) {
    const { props } = this;
    const { owner, name } = props;
    const duplicateArray = [];
    const newPackageData = updateablePackages.map((pkg) => {
      duplicateArray.push(pkg.id);
      return {
        ...pkg,
        version: pkg.latestVersion,
      };
    });
    const data = {
      packages: newPackageData,
      duplicates: duplicateArray,
    };
    const callback = () => {
      props.buildCallback();
    };

    props.selectPackages(true);
    props.setBuildingState(owner, name, true);
    props.packageMutations.addPackages(data, callback);
  }

  render() {
    const { props } = this;
    const packageValues = [...props.selectedPackages.values()];
    const updateablePackages = packageValues.filter(pkg => pkg.latestVersion && (pkg.version !== pkg.latestVersion));
    const multiSelectButtonCSS = classNames({
      CheckboxMultiselect: true,
      CheckboxMultiselect__check: props.multiSelect === 'all',
      CheckboxMultiselect__uncheck: props.multiSelect === 'none',
      CheckboxMultiselect__partial: props.multiSelect === 'partial',
    });
    const managerHeaderCSS = classNames({
      'Table__Header--sort Btn--noStyle': true,
      'Table__Header--asc': props.sort === 'manager' && !props.reverse,
      'Table__Header--desc': props.sort === 'manager' && props.reverse,
    });
    const nameHeaderCSS = classNames({
      'Table__Header--sort Btn--noStyle flex-1': true,
      'Table__Header--asc': props.sort === 'package' && !props.reverse,
      'Table__Header--desc': props.sort === 'package' && props.reverse,
    });
    return (
      <div className="Table__Header">
        {
          (props.selectedPackages.size !== 0)
          && (
          <div className="PackageHeader__toolbar flex align-items--center justify--space-between">
            <div className="PackageHeader__toolbar-text">
              {`${props.selectedPackages.size} packages selected`}
            </div>
            <div>
              {
                (updateablePackages.length !== 0)
                && (
                <button
                  className="Btn align-self--end Btn__upArrow-white Btn--background-left Btn--action Btn--padding-left"
                  type="button"
                  disabled={props.isLocked}
                  onClick={() => this._updatePackages(updateablePackages)}
                >
                  Update
                </button>
                )
              }
              <button
                type="button"
                className="Btn align-self--end Btn__delete-white Btn--background-left Btn--action Btn--padding-left"
                onClick={() => this._removePackages()}
                disabled={props.isLocked}
              >
                Delete
              </button>
            </div>
          </div>
          )
        }
        <div className="PackageHeader__row flex align-items--end">
          <div className="PackageHeader__multiselect">
            <button
              className={multiSelectButtonCSS}
              onClick={() => { props.selectPackages(); }}
              type="button"
            />
          </div>
          <div className="PackageHeader__manager">
            <button
              className={managerHeaderCSS}
              onClick={() => props.handleSort('manager')}
              type="button"
            >
              Package Manager
            </button>
          </div>
          <div className="PackageHeader__name">
            <button
              className={nameHeaderCSS}
              onClick={() => props.handleSort('package')}
              type="button"
            >
              Package Name
            </button>
          </div>
          <div className="PackageHeader__version">Version</div>
          <div className="PackageHeader__actions">Actions</div>
        </div>
      </div>
    );
  }
}
