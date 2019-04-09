import React, { Component } from 'react';
import { graphql, QueryRenderer } from 'react-relay';
import queryString from 'querystring';
// redux
import { setCallbackRoute } from 'JS/redux/reducers/routes';
// components
import environment from 'JS/createRelayEnvironment';
import Loader from 'Components/common/Loader';
import LocalLabbooksContainer from './labbooks/localLabbooks/LocalLabbooksContainer';
import LocalDatasetsContainer from './datasets/localDatasets/LocalDatasetsContainer';
import RemoteDatasetsContainer from './datasets/remoteDatasets/RemoteDatasetsContainer';
import RemoteLabbooksContainer from './labbooks/remoteLabbooks/RemoteLabbooksContainer';
// assets
import './Dashboard.scss';


const LocalListingQuery = graphql`query DashboardLocalQuery($first: Int!, $cursor: String, $orderBy: String $sort: String){
  ...LocalLabbooksContainer_labbookList
}`;

const LocalDatasetListingQuery = graphql`query DashboardDatasetLocalQuery($first: Int!, $cursor: String, $orderBy: String $sort: String){
  ...LocalDatasetsContainer_datasetList
}`;
const RemoteDatasetListingQuery = graphql`query DashboardDatasetRemoteQuery($first: Int!, $cursor: String, $orderBy: String $sort: String){
  ...RemoteDatasetsContainer_datasetList
}`;

const RemoteListingQuery = graphql`query DashboardRemoteQuery($first: Int!, $cursor: String, $orderBy: String $sort: String){
  ...RemoteLabbooksContainer_labbookList
}`;

export default class DashboardContainer extends Component {
  constructor(props) {
    super(props);

    const { orderBy, sort } = queryString.parse(this.props.history.location.search.slice(1));

    this.state = {
      selectedComponent: props.match.path,
      orderBy: orderBy || 'modified_on',
      sort: sort || 'desc',
    };
    setCallbackRoute(props.history.location.pathname);
    this._refetchSort = this._refetchSort.bind(this);
  }

  /**
  *  @param {Object} nextProps
  *  update select component before component renders
  */
  UNSAFE_componentWillReceiveProps(nextProps) {
    this.setState({
      selectedComponent: nextProps.match.path,
    });
    setCallbackRoute(nextProps.history.location.pathname);
  }

  /**
    * @param {string, string} orderBy, sort
    * sets state of orderBy and sort, passed to child components
  */
  _refetchSort(orderBy, sort) {
    if (this.state.orderBy !== orderBy || this.state.sort !== sort) {
      this.setState({ orderBy, sort });
    }
  }


  /**
  *  @param {}
  *  returns jsx of selected component
  *  @return {jsx}
  */
  _displaySelectedComponent() {
    const paths = this.props.history.location.pathname.split('/');
    const sectionRoute = paths.length > 2 ? paths[2] : 'local';

    if (paths[2] !== 'cloud' && paths[2] !== 'local') {
      this.props.history.replace('../../../../projects/local');
    }


    let query;
    if (this.state.selectedComponent === '/datasets/:labbookSection') {
      query = sectionRoute === 'cloud' ? RemoteDatasetListingQuery : LocalDatasetListingQuery;
    } else if (sectionRoute === 'cloud') {
      query = RemoteListingQuery;
    } else {
      query = LocalListingQuery;
    }

    return (
      <QueryRenderer
        environment={environment}
        query={query}
        variables={{
          first: sectionRoute === 'cloud' ? 8 : 100,
          cursor: null,
          orderBy: this.state.orderBy,
          sort: this.state.sort,
        }}
        render={({ error, props }) => {
          if (error) {
            console.log(error);
          } else if (props) {
            if (this.state.selectedComponent === '/datasets/:labbookSection') {
              if (sectionRoute === 'cloud') {
                return (
                  <RemoteDatasetsContainer
                    auth={this.props.auth}
                    datasetList={props}
                    history={this.props.history}
                    section={sectionRoute}
                    refetchSort={this._refetchSort}
                  />
                );
              }
              return (
                <LocalDatasetsContainer
                  auth={this.props.auth}
                  datasetList={props}
                  history={this.props.history}
                  section={sectionRoute}
                  refetchSort={this._refetchSort}
                />
              );
            }
            if (sectionRoute === 'cloud') {
              return (
                <RemoteLabbooksContainer
                  auth={this.props.auth}
                  labbookList={props}
                  history={this.props.history}
                  refetchSort={this._refetchSort}
                />
              );
            }

            return (
              <LocalLabbooksContainer
                auth={this.props.auth}
                labbookList={props}
                history={this.props.history}
                refetchSort={this._refetchSort}
              />
            );
          } else {
            if (this.state.selectedComponent === '/datasets/:labbookSection') {
              return (
                <LocalDatasetsContainer
                  auth={this.props.auth}
                  datasetList={props}
                  history={this.props.history}
                  section={sectionRoute}
                  refetchSort={this._refetchSort}
                  loading
                />
              );
            }

            return (
              <LocalLabbooksContainer
                auth={this.props.auth}
                labbookList={props}
                history={this.props.history}
                section={sectionRoute}
                refetchSort={this._refetchSort}
                loading
              />
            );
          }
        }}
      />
    );
  }

  render() {
    return (
      <div className="Dashboard flex flex-column">

        <div className="Dashboard__view flex-1-0-auto">
          <div id="dashboard__cover" className="Dashboard__cover hidden">
            <Loader />
          </div>
          {
            this._displaySelectedComponent()
          }
        </div>
      </div>
    );
  }
}
