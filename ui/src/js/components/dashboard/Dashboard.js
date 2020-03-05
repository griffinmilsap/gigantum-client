import React, { Component } from 'react';
import { graphql, QueryRenderer } from 'react-relay';
import queryString from 'querystring';
// redux
import { setCallbackRoute } from 'JS/redux/actions/routes';
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

type Props = {
  match: Object,
  history: Object,
  auth: Object,
  diskLow: boolean,
}

export default class DashboardContainer extends Component<Props> {
  constructor(props) {
    super(props);

    const { orderBy, sort } = queryString.parse(props.history.location.hash.slice(1));

    this.state = {
      selectedComponent: props.match && props.match.path,
      orderBy: orderBy || 'modified_on',
      sort: sort || 'desc',
    };
  }

  componentDidMount() {
    const { props } = this;
    setCallbackRoute(props.history.location.pathname);
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
  _refetchSort = (orderBy, sort) => {
    const { state } = this;
    if (state.orderBy !== orderBy || state.sort !== sort) {
      this.setState({ orderBy, sort });
    }
  }


  /**
  *  @param {}
  *  returns jsx of selected component
  *  @return {jsx}
  */
  _displaySelectedComponent = () => {
    const {
      orderBy,
      sort,
      selectedComponent,
    } = this.state;
    const {
      match,
      history,
      auth,
      diskLow,
    } = this.props;
    const sectionRoute = match
      && match.params
      && match.params.labbookSection;
    let query;

    if ((sectionRoute !== 'cloud') && (sectionRoute !== 'local')) {
      history.replace('/projects/local');
    }
    if (selectedComponent === '/datasets/:labbookSection') {
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
          first: sectionRoute === 'cloud' ? 10 : 100,
          cursor: null,
          orderBy,
          sort,
        }}
        render={(response) => {
          const { error } = this;
          const queryProps = response.props;
          if (error) {
            console.log(error);
          } else if (queryProps) {
            if (selectedComponent === '/datasets/:labbookSection') {
              if (sectionRoute === 'cloud') {
                return (
                  <RemoteDatasetsContainer
                    auth={auth}
                    datasetList={queryProps}
                    history={history}
                    section={sectionRoute}
                    refetchSort={this._refetchSort}
                    diskLow={diskLow}
                    orderBy={orderBy}
                    sort={sort}
                  />
                );
              }
              return (
                <LocalDatasetsContainer
                  auth={auth}
                  datasetList={queryProps}
                  history={history}
                  section={sectionRoute}
                  refetchSort={this._refetchSort}
                  diskLow={diskLow}
                  orderBy={orderBy}
                  sort={sort}
                />
              );
            }
            if (sectionRoute === 'cloud') {
              return (
                <RemoteLabbooksContainer
                  auth={auth}
                  labbookList={queryProps}
                  history={history}
                  section={sectionRoute}
                  refetchSort={this._refetchSort}
                  diskLow={diskLow}
                  orderBy={orderBy}
                  sort={sort}
                />
              );
            }

            return (
              <LocalLabbooksContainer
                auth={auth}
                labbookList={queryProps}
                history={history}
                section={sectionRoute}
                refetchSort={this._refetchSort}
                diskLow={diskLow}
                orderBy={orderBy}
                sort={sort}
              />
            );
          } else {
            if (selectedComponent === '/datasets/:labbookSection') {
              return (
                <LocalDatasetsContainer
                  auth={auth}
                  datasetList={queryProps}
                  history={history}
                  section={sectionRoute}
                  refetchSort={this._refetchSort}
                  loading
                  diskLow={diskLow}
                  orderBy={orderBy}
                  sort={sort}
                />
              );
            }

            return (
              <LocalLabbooksContainer
                auth={auth}
                labbookList={queryProps}
                history={history}
                section={sectionRoute}
                refetchSort={this._refetchSort}
                loading
                diskLow={diskLow}
                orderBy={orderBy}
                sort={sort}
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
