// vendor
import React, { Component } from 'react';
import { QueryRenderer, graphql } from 'react-relay';
import classNames from 'classnames';
import { boundMethod } from 'autobind-decorator';
// environment
import environment from 'JS/createRelayEnvironment';
// components
import Loader from 'Components/common/Loader';
import AdvancedSearch from 'Components/common/AdvancedSearch';
import BaseCard from './BaseCard';
import BaseDatasetCard from './BaseDatasetCard';
// utilities
import {
  createProjectFilters,
  filterProjects,
  createDatasetFilters,
  filterDatasets,
} from './utils/SelectBaseUtils';
// assets
import './SelectBase.scss';

const BaseQuery = graphql`query SelectBaseQuery($first: Int!, $cursor: String){
  availableBases(first: $first, after: $cursor)@connection(key: "SelectBase_availableBases"){
    edges{
      node{
        id
        schema
        repository
        componentId
        revision
        name
        description
        readme
        tags
        icon
        osClass
        osRelease
        license
        url
        languages
        developmentTools
        installedPackages
        packageManagers
        dockerImageServer
        dockerImageNamespace
        dockerImageRepository
        dockerImageTag
        cudaVersion
      }
      cursor
    }
    pageInfo{
      endCursor
      hasNextPage
      hasPreviousPage
      startCursor
    }
  }
}`;

const DatasetQuery = graphql`query SelectBase_DatasetQuery{
  availableDatasetTypes {
    id
    name
    storageType
    description
    isManaged
    readme
    tags
    icon
  }
}`;

export default class SelectBase extends Component {
  state = {
    name: '',
    description: '',
    selectedBase: null,
    selectedBaseId: null,
    viewedBase: null,
    viewingBase: false,
    tags: [],
  }

  /**
    @param {object} edge
    takes a base image edge
    sets componest state for selectedBaseId and selectedBase
  */
  @boundMethod
  _selectBase(node) {
    const { props } = this;

    this.setState({ selectedBase: node });
    this.setState({ selectedBaseId: node.id });
    props.selectBaseCallback(node);
    props.toggleDisabledContinue(false);
  }

  /**
    @param {}
    gets current selectedBase and passes variables to AddEnvironmentComponentMutation
    callback triggers and modal state is changed to  next window
    DO NOT REMOVE
  */
  continueSave() {
    const { props } = this;
    props.toggleDisabledContinue(true);
    if (!props.datasets) {
      props.createLabbookMutation();
    } else {
      props.createDatasetMutation();
    }
  }

  /**
    @param {Array} tags
    sets component tags from child
  */
  @boundMethod
  _setTags(tags) {
    this.setState({ tags });
  }

  render() {
    const { props, state } = this;
    const self = this;
    const variables = { first: 20 };

    const innerContainer = classNames({
      'SelectBase__inner-container': true,
      'SelectBase__inner-container--datasets': true,
      'SelectBase__inner-container--viewer': state.viewingBase,
    });
    const mostRecent = localStorage.getItem('latest_base');

    return (
      <div className="SelectBase">
        <QueryRenderer
          variables={props.datasets ? {} : variables}
          query={props.datasets ? DatasetQuery : BaseQuery}
          environment={environment}
          render={(response) => {
            const queryProps = response.props;
            const { error } = response;
            if (error) {
              return (<div>{error.message}</div>);
            }

            if (queryProps && !props.datasets) {
              const selecBaseImage = classNames({
                SelectBase__images: true,
                'SelectBase__images--hidden': (state.selectedTab === 'none'),
              });

              const filterCategories = createProjectFilters(queryProps.availableBases.edges);
              const filteredProjects = filterProjects(queryProps.availableBases.edges, state.tags);
              return (
                <div className={innerContainer}>
                  <div className="SelectBase__select-container">
                    <AdvancedSearch
                      tags={state.tags}
                      setTags={this._setTags}
                      filterCategories={filterCategories}
                    />
                    <div className={selecBaseImage}>
                      {
                            filteredProjects.map(({ node }) => {
                              const isMostRecent = mostRecent === node.componentId;
                              const BaseWrapper = classNames({
                                BaseSlide__wrapper: true,
                                'BaseSlide__wrapper--recent': mostRecent === node.componentId,
                                'BaseSlide__wrapper--popular': !mostRecent && node.componentId === 'python3-data-science',
                              });
                              return (
                                <div
                                  key={node.id}
                                  className={BaseWrapper}
                                >
                                  { isMostRecent
                                  && <div className="BaseSlide__mostRecent">RECENT</div>
                                }
                                  <BaseCard
                                    key={`${node.id}_slide`}
                                    node={node}
                                    selectBase={self._selectBase}
                                    selectedBaseId={state.selectedBaseId}
                                  />
                                </div>);
                            })
                          }
                    </div>
                  </div>

                </div>
              );
            } if (queryProps && props.datasets) {
              const filterCategories = createDatasetFilters(queryProps.availableDatasetTypes);
              const filteredDatasets = filterDatasets(queryProps.availableDatasetTypes, state.tags);
              return (
                <div className={innerContainer}>
                  <AdvancedSearch
                    tags={state.tags}
                    setTags={this._setTags}
                    filterCategories={filterCategories}
                  />
                  <div className="SelectBase__select-container">
                    <div className="SelectBase__images">
                      {
                          filteredDatasets.map(node => (
                            <div
                              key={node.id}
                              className="BaseSlide__wrapper"
                            >
                              <BaseDatasetCard
                                key={`${node.id}_slide`}
                                node={node}
                                selectBase={self._selectBase}
                                selectedBaseId={state.selectedBaseId}
                              />
                            </div>
                          ))
                        }
                    </div>
                  </div>

                </div>
              );
            }
            return (<Loader />);
          }}
        />
      </div>
    );
  }
}
