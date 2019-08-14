// vendor
import React, { Component } from 'react';
import { Route, Switch } from 'react-router-dom';
import { createRefetchContainer, graphql } from 'react-relay';
import { DragDropContext } from 'react-dnd';
import HTML5Backend from 'react-dnd-html5-backend';
import classNames from 'classnames';
import { connect } from 'react-redux';
import Loadable from 'react-loadable';
// store
import store from 'JS/redux/store';
import { setStickyState } from 'JS/redux/actions/dataset/dataset';
import { setCallbackRoute } from 'JS/redux/actions/routes';
// config
import Config from 'JS/config';
// utils
import { getFilesFromDragEvent } from 'JS/utils/html-dir-content';
// components
import Login from 'Components/login/Login';
import Loader from 'Components/common/Loader';
import ErrorBoundary from 'Components/common/ErrorBoundary';
import Header from 'Components/shared/header/Header';
// assets
import './Dataset.scss';

const Loading = () => <Loader />;

const Overview = Loadable({
  loader: () => import('./overview/DatasetOverviewContainer'),
  loading: Loading,
  delay: 500,
});

const Activity = Loadable({
  loader: () => import('./activity/DatasetActivityContainer'),
  loading: Loading,
  delay: 500,
});

const Data = Loadable({
  loader: () => import('./data/Data'),
  loading: Loading,
  delay: 500,
});

/**
  scrolls to top of window
*/
const scrollToTop = () => {
  window.scrollTo(0, 0);
};

/**
*  @param {Object} props
*
*  gets value of isLocked to lock out functionality while the backend is synching
*/
const getIsLocked = (props) => {
  const { owner, name } = props.dataset;
  const isLocked = props.isSynchingObject[`${owner}_${name}`]
    ? props.isSynchingObject[`${owner}_${name}`]
    : false;
  return isLocked;
};

class Dataset extends Component {
  constructor(props) {
    super(props);
    const { labbookName, owner } = store.getState().routes;

    localStorage.setItem('owner', store.getState().routes.owner);

    setCallbackRoute(props.location.pathname);

    document.title = `${owner}/${labbookName}`;
  }

  state = {
    overviewSkip: true,
    activitySkip: true,
    dataSkip: true,
    datasetSkip: true,
  };

  /**
    @param {object} nextProps
    @param {object} state
    calls setCallbackRoute on prop change
  */
  static getDerivedStateFromProps(nextProps, state) {
    setCallbackRoute(nextProps.location.pathname);
    return state;
  }

  /**
    @param {} -
    subscribe to store to update state
    set unsubcribe for store
  */
  componentDidMount() {
    const { auth } = this.props;
    auth.isAuthenticated().then((response) => {
      let isAuthenticated = response;
      if (isAuthenticated === null) {
        isAuthenticated = false;
      }
      if (isAuthenticated !== this.state.authenticated) {
        this.setState({ authenticated: isAuthenticated });
      }
    });

    this._setStickHeader();
    window.addEventListener('scroll', this._setStickHeader);
  }

  /**
    @param {}
    removes event listeners
  */
  componentWillUnmount() {
    window.removeEventListener('scroll', this._setStickHeader);
  }

  /**
    @param {}
    dispatches sticky state to redux to update state
  */
  _setStickHeader = () => {
    const isExpanded = (window.pageYOffset < this.offsetDistance)
      && (window.pageYOffset > 120);
    const sticky = 50;
    const isSticky = window.pageYOffset >= sticky;

    this.offsetDistance = window.pageYOffset;

    if ((store.getState().dataset.isSticky !== isSticky)
      || (store.getState().dataset.isExpanded !== isExpanded)) {
      setStickyState(isSticky, isExpanded);
    }
  }

  /**
   @param {String} section
   refetch dataset
   */
  _refetchDataset = (section) => {
    const { props, state } = this;
    const currentSection = `${section}Skip`;
    const currentState = {
      overviewSkip: state.overviewSkip,
      activitySkip: state.activitySkip,
      dataSkip: state.dataSkip,
    };
    const sections = ['overview', 'activity', 'data'];
    const queryVariables = {
      datasetID: props.dataset.id,
      [currentSection]: false,
    };
    const renderVariables = {
      datasetID: props.dataset.id,
      ...currentState,
      [currentSection]: false,
    };
    const remainingQueryVariables = {
      datasetID: props.dataset.id,
      datasetSkip: false,
    };
    const remainingRenderVariables = {
      datasetID: props.dataset.id,
      datasetSkip: false,
    };
    const newState = {
      datasetSkip: true,
    };
    const options = {
      force: true,
    };

    sections.forEach((fragmentSection) => {
      const remainingSection = `${fragmentSection}Skip`;
      if (fragmentSection !== section) {
        remainingQueryVariables[remainingSection] = false;
        newState[remainingSection] = false;
      }
      remainingRenderVariables[remainingSection] = false;
    });

    const refetchCallback = () => {
      this.setState({ [currentSection]: false });
      props.relay.refetch(
        remainingQueryVariables,
        remainingRenderVariables,
        () => {
          this.setState(newState);
        },
        options,
      );
    };

    if (state[currentSection]) {
      props.relay.refetch(queryVariables, renderVariables, refetchCallback, options);
    }
  }

  render() {
    const { props, state } = this;

    if (props.dataset) {
      const { dataset } = props;
      const isLocked = getIsLocked(props);

      // declare css here
      const datasetCSS = classNames({
        Dataset: true,
        'Dataset--detail-mode': props.detailMode,
        'Dataset--demo-mode': (window.location.hostname === Config.demoHostName) || props.diskLow,
      });

      return (
        <div className={datasetCSS}>

          <div className="Dataset__spacer flex flex--column">

            <Header
              description={dataset.description}
              toggleBranchesView={() => {}}
              branchName=""
              dataset={dataset}
              sectionType="dataset"
              isLocked={isLocked}
              {...props}
            />

            <div className="Dataset__routes flex flex-1-0-auto">

              <Switch>
                <Route
                  exact
                  path={`${props.match.path}`}
                  render={() => (
                    <ErrorBoundary type="datasetSectionError" key="overview">
                      <Overview
                        key={`${props.datasetName}_overview`}
                        dataset={dataset}
                        isManaged={dataset.datasetType.isManaged}
                        datasetId={dataset.id}
                        scrollToTop={scrollToTop}
                        sectionType="dataset"
                        datasetType={dataset.datasetType}
                        refetch={this._refetchDataset}
                      />
                    </ErrorBoundary>
                  )}
                />

                <Route path={`${props.match.path}/:datasetMenu`}>

                  <Switch>

                    <Route
                      path={`${props.match.path}/overview`}
                      render={() => (
                        <ErrorBoundary
                          type="datasetSectionError"
                          key="activity"
                        >

                          <Overview
                            key={`${props.datasetName}_overview`}
                            dataset={dataset}
                            isManaged={dataset.datasetType.isManaged}
                            datasetId={dataset.id}
                            scrollToTop={scrollToTop}
                            sectionType="dataset"
                            datasetType={dataset.datasetType}
                            refetch={this._refetchDataset}
                          />

                        </ErrorBoundary>
                      )}
                    />

                    <Route
                      path={`${props.match.path}/activity`}
                      render={() => (
                        <ErrorBoundary
                          type="datasetSectionError"
                          key="activity"
                        >
                          <Activity
                            key={`${props.datasetName}_activity`}
                            dataset={dataset}
                            diskLow={props.diskLow}
                            activityRecords={props.activityRecords}
                            datasetId={dataset.id}
                            activeBranch={dataset.activeBranch}
                            sectionType="dataset"
                            refetch={this._refetchDataset}
                            {...props}
                          />
                        </ErrorBoundary>
                      )}
                    />

                    <Route
                      path={`${props.match.url}/data`}
                      render={() => (
                        <ErrorBoundary
                          type="datasetSectionError"
                          key="code"
                        >

                          <Data
                            dataset={dataset}
                            owner={dataset.owner}
                            name={dataset.name}
                            datasetId={dataset.id}
                            isManaged={dataset.datasetType.isManaged}
                            type="dataset"
                            section="data"
                            refetch={this._refetchDataset}
                            lockFileBrowser={props.isUploading || isLocked}
                          />

                        </ErrorBoundary>
                      )}
                    />

                  </Switch>

                </Route>

              </Switch>

            </div>

          </div>

          <div className="Dataset__veil" />

        </div>
      );
    }

    if (state.authenticated) {
      return (<Loader />);
    }

    return (<Login auth={props.auth} />);
  }
}

const mapStateToProps = state => state.dataset;

const mapDispatchToProps = () => ({});

const DatasetContainer = connect(mapStateToProps, mapDispatchToProps)(Dataset);


const DatasetFragmentContainer = createRefetchContainer(
  DatasetContainer,
  {
    dataset: graphql`
      fragment Dataset_dataset on Dataset{
          id
          description
          owner
          name
          defaultRemote
          visibility @skip(if: $datasetSkip)
          backendIsConfigured
          backendConfiguration{
            parameter
            description
            parameterType
            value
          }
          commitsBehind
          datasetType {
              name
              storageType
              description
              readme
              tags
              icon
              url
              isManaged
          }
          ...Data_dataset
          ...DatasetActivityContainer_dataset
          ...DatasetOverviewContainer_dataset
      }`,
  },
  graphql`
  query DatasetRefetchQuery($first: Int!, $cursor: String, $datasetID: ID!, $overviewSkip: Boolean!, $activitySkip: Boolean!, $dataSkip: Boolean!, $datasetSkip: Boolean!){
    dataset: node(id: $datasetID){
      ... on Dataset {
        visibility @skip(if: $datasetSkip)
      }
      ...Data_dataset
      ...DatasetActivityContainer_dataset
      ...DatasetOverviewContainer_dataset
    }
  }
  `,
);

const datasetBackend = (manager: Object) => {
  const backend = HTML5Backend(manager);
  const orgTopDropCapture = backend.handleTopDropCapture;

  backend.handleTopDropCapture = (e) => {
    e.preventDefault();
    if (backend.currentNativeSource) {
      orgTopDropCapture.call(backend, e);

      // returns a promise
      backend.currentNativeSource.item.dirContent = getFilesFromDragEvent(e, { recursive: true });
    }
  };

  return backend;
};

export default DragDropContext(datasetBackend)(DatasetFragmentContainer);
