// vendor
import React, { Component } from 'react';
import Highlighter from 'react-highlight-words';
import { Link } from 'react-router-dom';
import Moment from 'moment';
// store
import store from 'JS/redux/store';
// assets
import './LocalDatasetsPanel.scss';
// config
import config from 'JS/config';

/**
*  dataset panel is to only render the edge passed to it
*/
export default class LocalDatasetPanel extends Component {
  /** *
  * @param {} -
  * triggers parent function goToDataset
  * redirects to dataset
  */
  _goToDataset() {
    const { props } = this;
    const { edge } = props;
    if (props.goToDataset) {
      props.goToDataset(edge.node.name, edge.node.owner);
    }
  }

  render() {
    const { props } = this;
    const { edge } = props;
    const link = props.noLink ? '#' : `/datasets/${edge.node.owner}/${edge.node.name}`;
    const sizeText = `${edge.node.overview.numFiles} file${(edge.node.overview.numFiles === 1) ? '' : 's'}, ${config.humanFileSize(edge.node.overview.totalBytes)}`;
    return (
      <Link
        to={link}
        onClick={() => this._goToDataset()}
        key={`local${edge.node.name}`}
        className="Card Card--225 Card--text column-4-span-3 flex flex--column justify--space-between"
      >
        <div className="LocalDatasets__row--icons">
          { !(props.visibility === 'local')
            && (
            <div
              data-tooltip={`${props.visibility}`}
              className={`Tooltip LocalDatasetPanel__${props.visibility} Tooltip-data Tooltip-data--small`}
            />
            )
          }
          <div className="LocalDatasets__dataset-icon" />
        </div>
        <div className="LocalDatasets__row--text">
          <div>
            <h5
              className="LocalDatasets__panel-title"
              onClick={() => this._goToDataset()}
            >
              <Highlighter
                highlightClassName="LocalDatasets__highlighted"
                searchWords={[store.getState().datasetListing.filterText]}
                autoEscape={false}
                caseSensitive={false}
                textToHighlight={edge.node.name}
              />
            </h5>

          </div>

          <p className="LocalDatasets__paragraph LocalDatasets__paragraph--owner">{edge.node.owner}</p>
          <p className="LocalDatasets__paragraph LocalDatasets__paragraph--metadata">
            <span className="bold">Created:</span>
            {' '}
            {Moment(edge.node.createdOnUtc).format('MM/DD/YY')}
          </p>
          <p className="LocalDatasets__paragraph LocalDatasets__paragraph--metadata">
            <span className="bold">Modified:</span>
            {' '}
            {Moment(edge.node.modifiedOnUtc).fromNow()}
          </p>
          <p className="LocalDatasets__paragraph LocalDatasets__paragraph--metadata">
            <span className="bold">Size:</span>
            {' '}
            {sizeText}
          </p>

          <p className="LocalDatasets__paragraph LocalDatasets__paragraph--description">
            { (edge.node.description && edge.node.description.length)
              ? (
                <Highlighter
                  highlightClassName="LocalLabbooks__highlighted"
                  searchWords={[store.getState().labbookListing.filterText]}
                  autoEscape={false}
                  caseSensitive={false}
                  textToHighlight={edge.node.description}
                />
              )
              : <span className="LocalDatasets__description--blank">No description provided</span>
            }
          </p>

        </div>
      </Link>
    );
  }
}
