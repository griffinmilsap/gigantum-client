// vendor
import React, { Component } from 'react';
import {
  createPaginationContainer,
  graphql,
} from 'react-relay';
import { boundMethod } from 'autobind-decorator';
// components
import LocalDatasetPanel from 'Components/dashboard/datasets/localDatasets/LocalDatasetsPanel';
import CardLoader from 'Components/dashboard/shared/loaders/CardLoader';
import ImportModule from 'Components/dashboard/shared/import/ImportModule';
import NoResults from 'Components/dashboard/shared/NoResults';
// helpers
import DatasetVisibilityLookup from './lookups/DatasetVisibilityLookup';
// assets
import './LocalDatasets.scss';


export class LocalDatasets extends Component {
  state = {
    isPaginating: false,
    visibilityList: new Map(),
  };

  /** *
  * @param {}
  * adds event listener for pagination and fetches container status
  */
  componentDidMount() {
    const { props } = this;
    this.mounted = true;
    if (!props.loading) {
      this._visibilityLookup();
      if (props.datasetList
         && props.localDatasets.localDatasets
         && props.localDatasets.localDatasets.edges
         && props.localDatasets.localDatasets.edges.length === 0) {
        this._fetchDemo();
      }
    }
  }

  /** *
  * @param {}
  * removes event listener for pagination and removes timeout for container status
  */
  componentWillUnmount() {
    this.mounted = false;

    window.removeEventListener('scroll', this._captureScroll);
  }

  /**
    *  @param {}
    *  fires when user scrolls
    *  if nextPage exists and user is scrolled down, it will cause loadmore to fire
  */
  @boundMethod
  _captureScroll() {
    const { props, state } = this;
    const root = document.getElementById('root');
    const distanceY = window.innerHeight + document.documentElement.scrollTop + 200;
    const expandOn = root.offsetHeight;

    if (props.localDatasets.localDatasets) {
      if ((distanceY > expandOn) && !state.isPaginating
      && props.localDatasets.localDatasets.pageInfo.hasNextPage) {
        this._loadMore();
      }
    }
  }

  /**
    *  @param {}
    *  loads more datasets using the relay pagination container
  */
  @boundMethod
  _loadMore() {
    const { props } = this;
    this.setState({
      isPaginating: true,
    });

    if (props.localDatasets.localDatasets.pageInfo.hasNextPage) {
      props.relay.loadMore(
        10, // Fetch the next 10 items
        () => {
          this.setState({
            isPaginating: false,
          });
          this._visibilityLookup();
        },
      );
    }
  }

  /** *
    * @param {integer} count
    * attempts to fetch a demo if no datasets are present, 3 times
  */
  @boundMethod
  _fetchDemo(count = 0) {
    const { props } = this;
    if (count < 3) {
      const self = this;
      const { relay } = props;
      setTimeout(() => {
        relay.refetchConnection(20, () => {
          if (!(props.localDatasets.localDatasets.edges.length > 0)) {
            self._fetchDemo(count + 1);
          }
        });
      }, 3000);
    }
  }

  /** *
    * @param {}
    * calls VisibilityLookup query and attaches the returned data to the state
    */
  @boundMethod
  _visibilityLookup() {
    const { props } = this;
    const self = this;
    const idArr = props.localDatasets.localDatasets.edges.map(edges => edges.node.id);
    let index = 0;

    function query(ids) {
      const subsetIds = idArr.slice(index, index + 10);

      DatasetVisibilityLookup.query(subsetIds).then((res) => {
        if (res && res.data
          && res.data.datasetList
          && res.data.datasetList.localById) {
          const visibilityListCopy = new Map(self.state.visibilityList);

          res.data.datasetList.localById.forEach((node) => {
            visibilityListCopy.set(node.id, node);
          });


          if (index < idArr.length) {
            index += 10;

            query(ids, index);
          }
          if (self.mounted) {
            self.setState({ visibilityList: visibilityListCopy });
          }
        }
      });
    }

    query(idArr, index);
  }

  render() {
    const { props, state } = this;
    const datasetList = props.localDatasets;// datasetList is passed as localDatasets
    if ((datasetList && datasetList.localDatasets && datasetList.localDatasets.edges)
    || props.loading) {
      const datasets = props.filterDatasets(datasetList, props.filterState, props.loading);
      const importVisible = (props.section === 'local' || !props.loading) && !props.filterText;

      return (

        <div className="Datasets__listing">

          <div className="grid">
            {
              importVisible
                && (
                <ImportModule
                  {...props}
                  ref="ImportModule_localLabooks"
                  section="dataset"
                  title="Add Dataset"
                  showModal={props.showModal}
                  history={props.history}
                />
                )
            }
            {
              datasets.length ? datasets.map((edge) => {
                const visibility = state.visibilityList.has(edge.node.id) ?
                  state.visibilityList.get(edge.node.id).visibility : 'loading';

                return (
                  <LocalDatasetPanel
                    key={`${edge.node.owner}/${edge.node.name}`}
                    ref={`LocalDatasetPanel${edge.node.name}`}
                    className="LocalDatasets__panel"
                    edge={edge}
                    visibility={visibility}
                    history={props.history}
                    filterText={props.filterText}
                    goToDataset={props.goToDataset}
                  />
                );
              })
                : !props.loading && props.filterText
                && <NoResults setFilterValue={props.setFilterValue} />
            }

            {
              Array(5).fill(1).map((value, index) => (
                <CardLoader
                  key={`LocalDatasets_paginationLoader${index}`}
                  index={index}
                  isLoadingMore={state.isPaginating || props.loading}
                />
              ))
            }

          </div>
        </div>
      );
    }
    return (<div />);
  }
}

export default createPaginationContainer(
  LocalDatasets,
  graphql`
    fragment LocalDatasets_localDatasets on DatasetList{
      localDatasets(first: $first, after: $cursor, orderBy: $orderBy, sort: $sort)@connection(key: "LocalDatasets_localDatasets", filters: []){
        edges {
          node {
            id
            name
            description
            owner
            createdOnUtc
            modifiedOnUtc
            overview {
              numFiles
              totalBytes
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
  `,
  {
    direction: 'forward',
    getConnectionFromProps(props, error) {
      return props.localDatasets.localDatasets;
    },
    getFragmentVariables(prevVars, first) {
      return {
        ...prevVars,
        first,
      };
    },
    getVariables(props, {
      first, cursor, orderBy, sort,
    }, fragmentVariables) {
      first = 10;
      cursor = props.localDatasets.localDatasets.pageInfo.endCursor;
      orderBy = fragmentVariables.orderBy;
      sort = fragmentVariables.sort;
      return {
        first,
        cursor,
        orderBy,
        sort,
        // in most cases, for variables other than connection filters like
        // `first`, `after`, etc. you may want to use the previous values.
      };
    },
    query: graphql`
      query LocalDatasetsPaginationQuery(
        $first: Int!
        $cursor: String
        $orderBy: String
        $sort: String
      ) {
        datasetList{
          ...LocalDatasets_localDatasets
        }
      }
    `,
  },
);
