// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// store
import { setBuildingState } from 'JS/redux/actions/labbook/labbook';
// components
import AddPackageForm from './AddPackageForm';
import Requirements from './Requirements';
import PackageQueue from './PackageQueue';
// util
import PackageLookup from '../utils/PackageLookup';
// assets
import './AddPackages.scss';


/**
*  @param {object} state
*  gets Disabled state for the install button;
*/
const getDisableInstall = (state) => {
  const packageQueueLength = state.packageQueue.filter(pkg => pkg.verified && !pkg.error).length;
  const lengthEqual = packageQueueLength !== state.packageQueue.length;
  const lengthIsZero = (state.packageQueue.length === 0);
  return (lengthIsZero || lengthEqual);
};

export default class AddPackages extends Component {
  state = {
    selectedEntryMethod: 'manual',
    packageQueue: [],
  };

  /**
  *  @param {}
  *  installs packages in queue
  */
  _installPackages = () => {
    const { props, state } = this;
    const newPackages = state.packageQueue.slice();
    const duplicates = {};
    const seperatedNewPackages = {};
    const buildCb = (response, error, id) => {
      props.setBuildId(id);
    };

    newPackages.forEach((newPackage) => {
      if (seperatedNewPackages[newPackage.manager]) {
        seperatedNewPackages[newPackage.manager].push(newPackage);
      } else {
        seperatedNewPackages[newPackage.manager] = [newPackage];
      }
    });

    const managers = Object.keys(seperatedNewPackages);

    managers.forEach((manager, index) => {
      const isLast = (managers.length - 1) === index;

      const data = {
        packages: seperatedNewPackages[manager],
        duplicates: duplicates[manager] || [],
      };

      setBuildingState(true);

      const callback = (response) => {
        if (response && isLast) {
          props.buildCallback(buildCb);
        }
      };
      props.packageMutations.addPackages(data, callback);
    });
  }

  /**
  *  @param {String} selectedEntryMethod
  *  sets entry method state
  */
  _setSelectedEntryMethod = (selectedEntryMethod) => {
    this.setState({ selectedEntryMethod });
  }

  /**
  *  @param {Object} file
  *  parses requirements file
  *  @return {}
  */
  _parseFile = (file) => {
    const reader = new FileReader();

    reader.onload = (evt) => {
      const packages = evt.target.result.split('\n');
      packages.forEach((pkg) => {
        const splitPackage = pkg.split('==');

        this._queuePackage({
          manager: 'pip',
          package: splitPackage[0],
          version: splitPackage[1],
        });
      });
    };
    reader.readAsText(file);
  }

  /**
  *  @param {Object} packageData
  *  @param {Number} index
  *  runs verification on current entered package
  *  @return {}
  */
  _queuePackage = (packageData, index) => {
    const { state, props } = this;
    const newPackageData = [packageData];
    const newPackageQueue = state.packageQueue.slice();
    const currentPackages = newPackageQueue.concat(props.packages);
    const existingPackages = currentPackages.map((pkg) => {
      return `${pkg.package}${pkg.version}`;
    });
    let currentPosition = (index !== undefined) ? index : newPackageQueue.length;

    let overWriteExisiting = false;

    newPackageQueue.forEach((pkg, existingIndex) => {
      const hasSamePackage = (pkg.package === packageData.package);
      const hasSameManager = (pkg.manager === packageData.manager);

      if (hasSamePackage && hasSameManager) {
        currentPosition = existingIndex;
        overWriteExisiting = true;
      }
    });

    if ((index !== undefined) || overWriteExisiting) {
      newPackageQueue[currentPosition] = Object.assign({}, newPackageData[0], { verified: false, error: false });
    } else {
      newPackageQueue.push(Object.assign({}, newPackageData[0], { verified: false }));
    }
    this.setState({ packageQueue: newPackageQueue });

    PackageLookup.query(props.name, props.owner, newPackageData).then((response) => {
      const newState = this.state;
      const responsePackageQueue = newState.packageQueue.slice();
      if (response.errors) {
        responsePackageQueue[currentPosition].error = true;
        responsePackageQueue[currentPosition].verified = true;
        this.setState({ packageQueue: responsePackageQueue });
      } else {
        const {
          version,
          isValid,
          latestVersion,
          description,
        } = response.data.labbook.checkPackages[0];
        const packageName = response.data.labbook.checkPackages[0].package;
        if (responsePackageQueue[currentPosition]) {
          const existingPackageVersion = (existingPackages.indexOf(`${packageName}${version}`) > -1) && !overWriteExisiting;
          responsePackageQueue[currentPosition].latestVersion = latestVersion;
          responsePackageQueue[currentPosition].version = version;
          responsePackageQueue[currentPosition].description = description;
          responsePackageQueue[currentPosition].verified = true;
          responsePackageQueue[currentPosition].error = !isValid || existingPackageVersion;
          responsePackageQueue[currentPosition].duplicate = existingPackageVersion;

          this.setState({ packageQueue: responsePackageQueue });
        }
      }
    });
  }

  /**
  *  @param {Integer} index
  *  removes package from queue
  *  @return {}
  */
  _removePackageFromQueue = (index) => {
    const { state } = this;
    const newPackageQueue = state.packageQueue.slice();
    newPackageQueue.splice(index, 1);
    this.setState({ packageQueue: newPackageQueue });
  }

  render() {
    const { props, state } = this;
    const disableInstall = getDisableInstall(state);
    // declare css
    const manualEntryCSS = classNames({
      'AddPackages__header--manual flex-1': true,
      'AddPackages__header-title': true,
      'AddPackages__header--selected': (state.selectedEntryMethod === 'manual'),
    });
    const fileEntryCSS = classNames({
      'AddPackages__header--file flex-1': true,
      'AddPackages__header-title': true,
      'AddPackages__header--selected': (state.selectedEntryMethod === 'file'),
    });

    return (
      <div className="AddPackages">
        <div className="AddPackages__header--top">
          <h4>Add Packages</h4>
        </div>
        <div className="AddPackages__body flex">
          <div className="AddPackages__entry">
            <div className="AddPackages__header flex">
              <h5
                className={manualEntryCSS}
                onClick={() => this._setSelectedEntryMethod('manual')}
              >
                Enter Packages
              </h5>
              <h5
                className={fileEntryCSS}
                onClick={() => this._setSelectedEntryMethod('file')}
              >
                Add Requirements File
              </h5>
            </div>
            {
              (state.selectedEntryMethod === 'file') && (
                <Requirements
                  queuePackage={this._queuePackage}
                />
              )
            }
            {
              (state.selectedEntryMethod === 'manual') && (
                <AddPackageForm
                  queuePackage={this._queuePackage}
                  defaultManager={props.base.packageManagers[0]}
                  base={props.base}
                  buildCallback={props.buildCallback}
                />
              )
            }
          </div>
          <PackageQueue
            queuePackage={this._queuePackage}
            packageQueue={state.packageQueue}
            disableInstall={disableInstall}
            toggleModal={props.toggleModal}
            installPackages={this._installPackages}
            removePackageFromQueue={this._removePackageFromQueue}
            buildCallback={props.buildCallback}
          />
        </div>
      </div>
    );
  }
}
