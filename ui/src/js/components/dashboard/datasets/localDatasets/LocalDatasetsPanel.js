// vendor
import React, { Component } from 'react';
import Highlighter from 'react-highlight-words';
import { Link } from 'react-router-dom';
import Moment from 'moment';
// muations
import StartContainerMutation from 'Mutations/StartContainerMutation';
import StopContainerMutation from 'Mutations/StopContainerMutation';
// store
import { setErrorMessage, setInfoMessage } from 'JS/redux/reducers/footer';
import store from 'JS/redux/store';
// assets
import './LocalDatasetsPanel.scss';
/**
*  dataset panel is to only render the edge passed to it
*/

export default class LocalDatasetPanel extends Component {
  constructor(props) {
    super(props);

    this.state = {
      datasetName: props.edge.node.name,
      owner: props.edge.node.owner,
    };
  }

  render() {
    const edge = this.props.edge;
    const status = this.state.status;
    const textStatus = this.state.textStatus;
    const link = this.props.noLink ? '#' : `/datasets/${edge.node.owner}/${edge.node.name}`;
    return (
      <Link
        to={link}
        onClick={() => {
          if (this.props.goToDataset) {
            this.props.goToDataset(edge.node.name, edge.node.owner);
          }
        }}
        key={`local${edge.node.name}`}
        className="Card Card--300 Card--text column-4-span-3 flex flex--column justify--space-between"
      >

        <div className="LocalDatasets__row--icons">

        </div>

        <div className="LocalDatasets__row--text">

          <div>

            <h6
              className="LocalDatasets__panel-title"
              onClick={() => {
                if (this.props.goToDataset) {
                  this.props.goToDataset(edge.node.name, edge.node.owner);
                }
              }}
            >

              <Highlighter
                highlightClassName="LocalDatasets__highlighted"
                searchWords={[store.getState().datasetListing.filterText]}
                autoEscape={false}
                caseSensitive={false}
                textToHighlight={edge.node.name}
              />

            </h6>

          </div>

          <p className="LocalDatasets__paragraph LocalDatasets__paragraph--owner ">{edge.node.owner}</p>
          <p className="LocalDatasets__paragraph LocalDatasets__paragraph--owner">{`Created on ${Moment(edge.node.createdOnUtc).format('MM/DD/YY')}`}</p>
          <p className="LocalDatasets__paragraph LocalDatasets__paragraph--owner">{`Modified ${Moment(edge.node.modifiedOnUtc).fromNow()}`}</p>

          <p
            className="LocalDatasets__paragraph LocalDatasets__paragraph--description"
          >
            {
              edge.node.description && edge.node.description.length ?
              <Highlighter
                highlightClassName="LocalLabbooks__highlighted"
                searchWords={[store.getState().labbookListing.filterText]}
                autoEscape={false}
                caseSensitive={false}
                textToHighlight={edge.node.description}
              />
              :
              <span
                className="LocalDatasets__description--blank"
              >
              No description provided
              </span>
            }

          </p>

        </div>
        { !(this.props.visibility === 'local') &&
          <div
            data-tooltip={`${this.props.visibility}`}
            className={`Tooltip LocalDatasetPanel__${this.props.visibility}`}
          />
        }
      </Link>);
  }
}
