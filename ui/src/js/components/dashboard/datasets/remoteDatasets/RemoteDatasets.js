// vendor
import React, { Component } from 'react';
import {
  createPaginationContainer,
  graphql,
} from 'react-relay';
// queries
import UserIdentity from 'JS/Auth/UserIdentity';
// store
import store from 'JS/redux/store';
// components
import RemoteDatasetPanel from 'Components/dashboard/datasets/remoteDatasets/RemoteDatasetsPanel';
import DeleteDataset from 'Components/shared/modals/DeleteDataset';
import CardLoader from 'Components/dashboard/shared/loaders/CardLoader';
import NoResults from 'Components/dashboard/shared/NoResults';
// assets
import './RemoteDatasets.scss';

class RemoteDatasets extends Component {
  state = {
    deleteData: {
      remoteId: null,
      remoteOwner: null,
      remoteDatasetName: null,
      remoteUrl: null,
      existsLocally: null,
    },
    deleteModalVisible: false,
    isPaginating: false,
  };

  /*
    loads more remote datasets on mount
  */
  componentDidMount() {
    const { props } = this;
    if (props.remoteDatasets.remoteDatasets
      && props.remoteDatasets.remoteDatasets.pageInfo.hasNextPage) {
      this._loadMore();
    }

    UserIdentity.getUserIdentity().then((response) => {
      if (navigator.onLine) {
        if (response.data) {
          if (!response.data.userIdentity.isSessionValid) {
            props.auth.renewToken();
          }
        }
      } else {
        props.forceLocalView();
      }
    });
  }

  /*
    loads more remote datasets if available
  */
  UNSAFE_componentWillReceiveProps(nextProps) {
    if (nextProps.remoteDatasets.remoteDatasets
      && nextProps.remoteDatasets.remoteDatasets.pageInfo.hasNextPage) {
      this._loadMore();
    }
  }

  /**
    *  @param {}
    *  loads more datasets using the relay pagination container
  */
  _loadMore = () => {
    const self = this;
    const { props } = this;
    UserIdentity.getUserIdentity().then((response) => {
      if (navigator.onLine) {
        if (response.data) {
          if (response.data.userIdentity.isSessionValid) {
            this.setState({
              isPaginating: true,
            });

            if (props.remoteDatasets.remoteDatasets.pageInfo.hasNextPage) {
              props.relay.loadMore(
                8, // Fetch the next 8 items
                () => {
                  this.setState({
                    isPaginating: false,
                  });
                },
              );
            }
          } else {
            props.auth.renewToken(true, () => {
              props.forceLocalView();
            }, () => {
              self._loadMore();
            });
          }
        }
      } else {
        props.forceLocalView();
      }
    });
  }

  /**
    *  @param {object} deleteData
    *  changes the delete modal's visibility and changes the data passed to it
  */
  _toggleDeleteModal = (deleteData) => {
    if (deleteData) {
      this.setState({
        deleteData,
        deleteModalVisible: true,
      });
    } else {
      this.setState({
        deleteData: {
          remoteId: null,
          remoteOwner: null,
          remoteUrl: null,
          remoteDatasetName: null,
          existsLocally: null,
        },
        deleteModalVisible: false,
      });
    }
  }

  render() {
    const { props, state } = this;
    if (props.remoteDatasets && props.remoteDatasets.remoteDatasets !== null) {
      const datasets = props.filterDatasets(props.remoteDatasets, props.filterState);

      return (
        <div className="Datasets__listing">
          <div className="grid">
            {
            datasets.length
              ? datasets.map(edge => (
                <RemoteDatasetPanel
                  toggleDeleteModal={this._toggleDeleteModal}
                  datasetListId={props.remoteDatasetsId}
                  key={edge.node.owner + edge.node.name}
                  ref={`RemoteDatasetPanel${edge.node.name}`}
                  edge={edge}
                  history={props.history}
                  existsLocally={edge.node.isLocal}
                  auth={props.auth}
                />
              ))
              : !state.isPaginating
                && store.getState().datasetListing.filterText
                && <NoResults setFilterValue={props.setFilterValue} />
            }
            {
              Array(5).fill(1).map((value, index) => (
                <CardLoader
                  key={`RemoteDatasets_paginationLoader${index}`}
                  index={index}
                  isLoadingMore={state.isPaginating}
                />
              ))
            }
          </div>
          {
            state.deleteModalVisible
            && (
            <DeleteDataset
              sectionType="dataset"
              handleClose={() => { this._toggleDeleteModal(); }}
              datasetListId={props.datasetListId}
              remoteId={state.deleteData.remoteId}
              remoteConnection="RemoteDatasets_remoteDatasets"
              toggleModal={this._toggleDeleteModal}
              owner={state.deleteData.remoteOwner}
              name={state.deleteData.remoteDatasetName}
              remoteUrl={state.deleteData.remoteUrl}
              existsLocally={state.deleteData.existsLocally}
              remoteDelete
              history={props.history}
            />
            )
          }
        </div>
      );
    }

    return (<div />);
  }
}

export default createPaginationContainer(
  RemoteDatasets,
  graphql`
    fragment RemoteDatasets_remoteDatasets on DatasetList{
      remoteDatasets(first: $first, after: $cursor, orderBy: $orderBy, sort: $sort)@connection(key: "RemoteDatasets_remoteDatasets", filters: []){
        edges {
          node {
            name
            description
            visibility
            owner
            id
            isLocal
            creationDateUtc
            modifiedDateUtc
            importUrl
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
      return props.remoteDatasets.remoteDatasets;
    },
    getFragmentVariables(prevVars, first, cursor) {
      return {
        ...prevVars,
        first,
      };
    },
    getVariables(props, {
      first, cursor, orderBy, sort,
    }, fragmentVariables) {
      first = 10;
      cursor = props.remoteDatasets.remoteDatasets.pageInfo.endCursor;
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
      query RemoteDatasetsPaginationQuery(
        $first: Int!
        $cursor: String
        $orderBy: String
        $sort: String
      ) {
        datasetList{
          ...RemoteDatasets_remoteDatasets
        }
      }
    `,
  },
);
