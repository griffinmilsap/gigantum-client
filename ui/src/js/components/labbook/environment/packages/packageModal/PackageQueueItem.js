// vendor
import React, { Component } from 'react';
// components
import PackageStatus from './PackageStatus';
// assets
import './PackageQueue.scss';

export default (props) => {
  return (
    <div className="PackageQueue__row-container">
      {
        props.packageQueue.map((pkg, index) => {
          const isEdited = props.editedPackageRows[pkg.manager] && props.editedPackageRows[pkg.manager].has(pkg.package);
          const newPackageName = isEdited && props.editedPackageRows[pkg.manager].get(pkg.package).newPackageName;
          const newPackageVersion = isEdited && props.editedPackageRows[pkg.manager].get(pkg.package).newPackageVersion;
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
                {isEdited
                  ? (
                    <input
                      type="text"
                      className="Input--smallText"
                      defaultValue={pkg.package}
                      onChange={evt => props.updatePackage(evt, pkg.manager, pkg.package, pkg.version, index, 'newPackageName')}
                      onKeyDown={evt => props.updatePackage(evt, pkg.manager, pkg.package, pkg.version, index, 'newPackageName')}
                    />
                  ) : pkg.package
                }
              </div>
              <div className="PackageQueue__version">
                {isEdited
                  ? (
                    <input
                      type="text"
                      className="Input--smallText"
                      disabled={pkg.manager === 'apt'}
                      onChange={evt => props.updatePackage(evt, pkg.manager, pkg.package, pkg.version, index, 'newPackageVersion')}
                      onKeyDown={evt => props.updatePackage(evt, pkg.manager, pkg.package, pkg.version, index, 'newPackageVersion')}
                      defaultValue={pkg.version}
                    />
                  ) : pkg.version
                }
              </div>
              <div className="PackageQueue__status">
                <PackageStatus
                  queuePackage={props.queuePackage}
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
                />
              </div>
            </div>
          );
        })
      }
    </div>
  );
}
