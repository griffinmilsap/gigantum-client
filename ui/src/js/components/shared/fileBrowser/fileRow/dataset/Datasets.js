// vendor
import React, { PureComponent } from 'react';
import classNames from 'classnames';
// components
import DatasetCard from './DatasetCard';
// assets
import './Datasets.scss';

export default class Datasets extends PureComponent {
  render() {
    const { props } = this;
    const headerCSS = classNames({
      'DatasetsBrowser__header flex justify--space-between': true,
      'DatasetsBrowser__header--empty': props.linkedDatasets.length === 0,
    });

    return (
      <div className="DatasetsBrowser">
        <div className={headerCSS}>
          <h4 className="margin--0 regular">Datasets</h4>
          {
            (props.linkedDatasets.length === 0)
            && (
              <div className="DatasetsBrowser__empty">
                No datasets are linked.
              </div>
            )
          }
          <button
            className="Btn Btn__FileBrowserAction Btn__FileBrowserAction--link"
            type="button"
            onClick={() => props.showLinkModal(true)}
            disabled={props.isLocked}
          >
            Link Dataset
          </button>
        </div>
        {
          props.linkedDatasets.map(dataset => (
            <DatasetCard
              formattedFiles={props.files[dataset.name]}
              isLocal={props.checkLocal(props.files[dataset.name])}
              checkLocal={props.checkLocal}
              key={dataset.name}
              dataset={dataset}
              isLocked={props.isLocked}
              owner={props.owner}
              name={props.name}
              mutationData={props.mutationData}
              mutations={props.mutations}
              section={props.section}
            />
          ))
        }
      </div>
    );
  }
}
