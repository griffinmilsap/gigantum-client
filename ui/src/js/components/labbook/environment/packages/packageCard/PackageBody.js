// vendor
import React, { Component } from 'react';
// components
import PackageRow from './PackageRow';
// assets
import './PackageBody.scss';

export default (props) => {
  const { owner, name } = props;
  return (
    <div className="PackageBody">
      {
        props.packages.map(node => (
          <PackageRow
            key={node.id}
            {...node}
            packageNode={node}
            name={name}
            owner={owner}
            selectedPackages={props.selectedPackages}
            selectSinglePackage={props.selectSinglePackage}
            packageMutations={props.packageMutations}
            isLocked={props.isLocked}
            buildCallback={props.buildCallback}
            selectPackages={props.selectPackages}
            setBuildingState={props.setBuildingState}
          />
        ))
      }

      { (props.packages.length === 0) &&
        <p className="text-center">No packages have been added to this project</p>
      }
    </div>
  );
}
