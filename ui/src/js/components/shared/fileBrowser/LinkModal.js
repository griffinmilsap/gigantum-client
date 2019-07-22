// vendor
import React, { Component } from 'react';
import { QueryRenderer, graphql } from 'react-relay';
import store from 'JS/redux/store';
import environment from 'JS/createRelayEnvironment';
import classNames from 'classnames';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
// mutations
import ModifyDatasetLinkMutation from 'Mutations/ModifyDatasetLinkMutation';
// component
import Modal from 'Components/common/Modal';
import Loader from 'Components/common/Loader';
import ButtonLoader from 'Components/common/ButtonLoader';
import AdvancedSearch from 'Components/common/AdvancedSearch';
import LinkCard from './LinkCard';
// assets
import './LinkModal.scss';

export const LinkModalQuery = graphql`
  query LinkModalQuery($first: Int!, $cursor: String, $orderBy: String $sort: String){
      datasetList{
        localDatasets(first: $first, after: $cursor, orderBy: $orderBy, sort: $sort)@connection(key: "LocalDatasets_localDatasets", filters: []){
            edges {
              node {
                id
                name
                description
                owner
                backendIsConfigured
                createdOnUtc
                modifiedOnUtc
                defaultRemote
                datasetType {
                    name
                    isManaged
                    icon
                }
                overview {
                  id
                  numFiles
                  totalBytes
                  localBytes
                }
              }
              cursor
            }
            pageInfo {
              endCursor
              hasNextPage
              hasPreviousPage
              startCursor
            }
          }
      }
  }`;

export default class LinkModal extends Component {
  constructor(props) {
    super(props);
    this.state = {
      selectedDataset: null,
      buttonState: '',
      tags: [],
    };
    this._linkDataset = this._linkDataset.bind(this);
    this._setTags = this._setTags.bind(this);
  }

  /**
    @param {Array} tags
    sets component tags from child
    */
  _setTags(tags) {
    this.setState({ tags });
  }

  /**
        @param {object} datasets
        determines filter criteria for dataset types
        @return {object} filters
    */
  _createFilters(datasets) {
    const filters = {
      'Dataset Type': [],
    };

    const datasetTypes = new Set();
    datasets.forEach(({ node }) => {
      if (!datasetTypes.has(node.datasetType.name) && node.datasetType.name) {
        datasetTypes.add(node.datasetType.name);
      }
    });
    filters['Dataset Type'] = Array.from(datasetTypes);
    return filters;
  }

  /**
    * @param {}
    * triggers link datraset mutation
  */
  _linkDataset() {
    const { owner, labbookName } = store.getState().routes;
    this.setState({ buttonState: 'loading' });
    ModifyDatasetLinkMutation(
      owner,
      labbookName,
      this.state.selectedDataset.owner,
      this.state.selectedDataset.name,
      'link',
      this.state.selectedUrl || null,
      (response, error) => {
        if (error) {
          setErrorMessage('Unable to link dataset', error);
          this.setState({ buttonState: 'error' });
          setTimeout(() => {
            this.setState({ buttonState: '' });
          }, 2000);
        } else {
          this.setState({ buttonState: 'finished' });
          setTimeout(() => {
            this.props.closeLinkModal();
          }, 2000);
        }
      },
    );
  }

  /**
    * @param {object} edge
    * sets update selected state
  */
  _updateSelected(edge) {
    this.setState({
      selectedDataset: {
        owner: edge.node.owner,
        name: edge.node.name,
      },
      selectedUrl: edge.node.defaultRemote,
    });
  }

  /**
    @param {Array} datasets
    filters datasets based on selected filters
  */
  _filterDatasets(datasets) {
    const tags = this.state.tags;
    return datasets.filter(({ node }) => {
      const lowercaseDescription = node.description.toLowerCase();
      const lowercaseName = node.name.toLowerCase();
      let isReturned = true;
      if (((tags.indexOf('Managed') > -1) && !node.isManaged)
            || ((tags.indexOf('Unmanaged') > -1) && node.isManaged)) {
        isReturned = false;
      }

      tags.forEach(({ text, className }) => {
        if (className === 'Dataset Type') {
          if (node.datasetType.name !== text) {
            isReturned = false;
          }
        } else if ((lowercaseDescription.indexOf(text.toLowerCase()) === -1) && (lowercaseName.indexOf(text.toLowerCase()) === -1)) {
          isReturned = false;
        }
      });
      return isReturned;
    });
  }

  render() {
    const { props } = this;
    return (

      <Modal
        handleClose={() => props.closeLinkModal()}
        size="large-long"
        noPadding
        noPaddingModal
        renderContent={() => (
          <div className="LinkModal">
            <div className="LinkModal__header">
              <div className="Icon--add--green" />
              <h4 className="LinkModal__header-text">Link Dataset</h4>
            </div>
            <div className="LinkModal__subheader">
              <h3 className="LinkModal__subheader-text">Select Dataset to Link</h3>
            </div>
            <div
              className="LinkModal__info Tooltip-data"
              data-tooltip="Linking a dataset will allow you to reference its files within the Project"
            />
            <div className="LinkModal__flex flex flex--column justify--space-between">
              <QueryRenderer
                environment={environment}
                query={LinkModalQuery}
                variables={{
                  first: 100,
                  cursor: null,
                  orderBy: 'modified_on',
                  sort: 'desc',
                }}
                render={({ error, props }) => {
                  if (error) {
                    console.log(error);
                  } else if (props) {
                    const existingDatasets = this.props.linkedDatasets.map(dataset => dataset.name);
                    const filteredDatasets = props.datasetList.localDatasets.edges.filter(dataset => existingDatasets.indexOf(dataset.node.name) === -1 && dataset.node.backendIsConfigured);
                    const localDatasetEdges = this._filterDatasets(filteredDatasets);
                    const colloboratorMessage = localDatasetEdges.length ? 'For collaborators to access a linked Dataset, the Dataset must be public or they must be added as a collaborator to the Dataset itself.' : 'You do not have any Local Datasets available to link to this project. To link a dataset you must first create or import a dataset.'
                    const filterCategories = this._createFilters(localDatasetEdges);
                    const messageCSS = classNames({
                      LinkModal__message: true,
                      'LinkModal__message--padded': localDatasetEdges.length === 0,
                    });
                    return (
                      <div className="LinkModal__container">
                        <AdvancedSearch
                          tags={this.state.tags}
                          setTags={this._setTags}
                          filterCategories={filterCategories}
                          withoutContext
                          showButton
                        />
                        <div className="LinkModal__dataset-container">
                          <p className={messageCSS}>
                            <b>
                              { colloboratorMessage }
                            </b>
                          </p>
                          {
                            localDatasetEdges.map((edge) => {
                              const node = edge.node;
                              return (
                                <div
                                  key={node.id}
                                  onClick={() => { this._updateSelected(edge); }}
                                  className="LinkModal__wrapper"
                                >
                                  <LinkCard
                                    node={node}
                                    selectedDataset={this.state.selectedDataset}
                                  />
                                </div>
                              );
                            })
                        }
                        </div>
                      </div>
                    );
                  }
                  return <Loader />;
                }}
              />
            </div>
            <div className="Link__buttonContainer">
              <button
                className="Btn--flat"
                onClick={() => this.props.closeLinkModal()}
                type="button"
              >
                Cancel
              </button>
              <ButtonLoader
                buttonState={this.state.buttonState}
                buttonText="Link Dataset"
                className="Btn Btn--last"
                params={{}}
                buttonDisabled={!this.state.selectedDataset}
                clicked={this._linkDataset}
              />
            </div>
          </div>
        )
        }
      />
    );
  }
}
