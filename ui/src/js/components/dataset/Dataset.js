// vendor
import React, { Component } from 'react';
import { Route, Switch } from 'react-router-dom';
import { createRefetchContainer, graphql } from 'react-relay';
import { DragDropContext } from 'react-dnd';
import HTML5Backend from 'react-dnd-html5-backend';
import classNames from 'classnames';
import { connect } from 'react-redux';
import Loadable from 'react-loadable';
import { boundMethod } from 'autobind-decorator'
// mutations
import ConfigureDatasetMutation from 'Mutations/ConfigureDatasetMutation';
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
import Modal from 'Components/common/Modal';
import ErrorBoundary from 'Components/common/ErrorBoundary';
import DatasetHeader from 'Components/shared/header/Header';
import ButtonLoader from 'Components/common/ButtonLoader';
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

class Dataset extends Component {
  constructor(props) {
  	super(props);

    localStorage.setItem('owner', store.getState().routes.owner);
    this.state = {
      buttonState: '',
      configValues: new Map(),
      configModalVisible: !this.props.dataset.backendIsConfigured,
      latestError: '',
      overviewSkip: true,
      activitySkip: true,
      dataSkip: true,
      datasetSkip: true,
    };
    // bind functions here
    this._setBuildingState = this._setBuildingState.bind(this);
    this._configureDataset = this._configureDataset.bind(this);

    setCallbackRoute(props.location.pathname);
    const { labbookName, owner } = store.getState().routes;
    document.title = `${owner}/${labbookName}`;
  }

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
    @param {}
    subscribe to store to update state
    set unsubcribe for store
  */
  componentDidMount() {
    this.props.auth.isAuthenticated().then((response) => {
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
  _setStickHeader() {
    const isExpanded = (window.pageYOffset < this.offsetDistance) && (window.pageYOffset > 120);
    this.offsetDistance = window.pageYOffset;
    const sticky = 50;
    const isSticky = window.pageYOffset >= sticky;
    if ((store.getState().dataset.isSticky !== isSticky) || (store.getState().dataset.isExpanded !== isExpanded)) {
      setStickyState(isSticky, isExpanded);
    }
  }

  /**
    @param {boolean} isBuilding
    updates container status state
    updates dataset state
  */
  _setBuildingState = (isBuilding) => {
    this.refs.ContainerStatus && this.refs.ContainerStatus.setState({ isBuilding });

    if (this.props.isBuilding !== isBuilding) {
      setBuildingState(isBuilding);
    }
  }

  /**
   @param {}
   refetch dataset
   */
  @boundMethod
  _refetchDataset(section) {
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

  /**
    scrolls to top of window
  */
  _scrollToTop() {
    window.scrollTo(0, 0);
  }
  /**
    @param {Event} evt
    @param {String} parameter
    @param {String} parameterType
    updates configstate with input
  */
  _setDatasetConfig = (evt, parameter, parameterType) => {
      const input = parameterType === 'str' ? evt.target.value : evt.target.checked;
      const newConfig = this.state.configValues;
      if (input) {
        newConfig.set(parameter, input);
      } else {
        newConfig.delete(parameter);
      }
      this.setState({ configValues: newConfig });
  }
  /**
   * @param {Boolean} confirm
    calls configure dataset mutation
  */
  _configureDataset = (confirm = null) => {
    const { labbookName, owner } = store.getState().routes;
    const parameters = this.props.dataset.backendConfiguration.map(({ parameter, parameterType }) => {
      const value = this.state.configValues.get(parameter) || '';
      return {
        parameter,
        parameterType,
        value,
      };
    });
    this.setState({ buttonState: 'loading', latestError: '' });
    const successCall = () => {};
    const failureCall = () => {
      if (this.closeModal) {
        clearTimeout(this.closeModal);
        this.setState({ buttonState: '' });
      } else {
        this.setState({ configModalVisible: true, buttonState: '' });
      }
  };
    ConfigureDatasetMutation(
      owner,
      labbookName,
      parameters,
      confirm,
      successCall,
      failureCall,
      (response, error) => {
        const configureDataset = response && response.configureDataset;
        if (error) {
          console.log(error);
          this.setState({ buttonState: 'error' });
          setTimeout(() => {
              this.setState({ buttonState: '' });
          }, 2000);
        } else if (configureDataset.errorMessage) {
          setErrorMessage('Failed to configure Dataset', [{ message: configureDataset.errorMessage }]);
          this.setState({ buttonState: 'error', latestError: configureDataset.errorMessage });
          setTimeout(() => {
              this.setState({ buttonState: '' });
          }, 2000);
        } else if (configureDataset.isConfigured && !configureDataset.shouldConfirm && !configureDataset.backgroundJobKey) {
          this._configureDataset(true);
        } else if (configureDataset.isConfigured && configureDataset.shouldConfirm && !confirm) {
          this.setState({ confirmMessage: configureDataset.confirmMessage });
        } else if (confirm) {
          this.setState({ buttonState: 'finished' });
          this.closeModal = setTimeout(() => {
              this.setState({ configModalVisible: false, buttonState: '' });
          }, 2000);
        }
      },
    );
  }

  /**
    @param {}
    redirect back to dataset listing
  */
  _handleRedirect() {
    this.props.history.push('/datasets/local');
  }

  /**
    @param {}
    cancels confirm on configure dataset
  */
  _confirmCancelConfigure() {
    this.setState({ confirmMessage: '', buttonState: '' });
  }

  render() {
    const { props, state } = this;
    if (props.dataset) {
      const { dataset } = props;
      const datasetCSS = classNames({
        Dataset: true,
        'Dataset--detail-mode': props.detailMode,
        'Dataset--demo-mode': (window.location.hostname === Config.demoHostName) || props.diskLow,
      });
      const someFieldsFilled = this.state.configValues.size > 0;
      return (
        <div className={datasetCSS}>
          {
            this.state.configModalVisible &&
            <Modal
              header="Configure Dataset"
              size="large"
              renderContent={() => (<div className="Dataset__config-modal">
              {
                this.state.confirmMessage &&
                <Modal
                  size="small"
                  renderContent={() => (
                    <div>
                      {this.state.confirmMessage}
                      <div className="Dataset__confirm-buttons">
                        <button
                          onClick={() => this._confirmCancelConfigure()}
                          className="Btn--flat"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => this._configureDataset(true)}
                        >
                          Confirm
                        </button>
                      </div>
                    </div>
                  )}
                />
              }
                  <p>This dataset needs to be configured before it is ready for use.</p>
                  {
                    this.state.latestError &&
                    <p className="Dataset__config-error">{this.state.latestError}</p>
                  }
                  <div className="Dataset__config-container">
                    <div className="Dataset__configs">
                      {
                        dataset.backendConfiguration.map(({ description, parameter, parameterType }) => (
                          <div
                            className="Dataset__config-section"
                            key={parameter}
                          >
                            <div className="Dataset__config-parameter">
                              {parameter}
                              {
                                parameterType === 'bool' &&
                                <input
                                  type="checkbox"
                                  onClick={evt => this._setDatasetConfig(evt, parameter, parameterType)}
                                />
                              }
                            </div>
                            <div className="Dataset__config-description">{description}</div>
                            {
                              parameterType === 'str' &&
                              <input
                                type="text"
                                className="Dataset__config-textInput"
                                onKeyUp={(evt) => { this._setDatasetConfig(evt, parameter, parameterType); }}
                                onChange={(evt) => { this._setDatasetConfig(evt, parameter, parameterType); }}
                              />
                            }
                          </div>
                        ))
                      }
                    </div>
                  <div className="Dataset__config-buttons">
                    <button
                      onClick={() => this._handleRedirect()}
                      className="Btn--flat"
                    >
                      Return to Datasets
                    </button>
                    <ButtonLoader
                        buttonState={this.state.buttonState}
                        buttonText="Save Configuration"
                        className=""
                        params={{}}
                        buttonDisabled={!someFieldsFilled}
                        clicked={() => this._configureDataset()}
                    />
                  </div>
                </div>
                </div>)}
            />
          }

          <div className="Dataset__spacer flex flex--column">

            <DatasetHeader
              description={dataset.description}
              toggleBranchesView={() => {}}
              branchName=""
              dataset={dataset}
              sectionType="dataset"
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
                        scrollToTop={this._scrollToTop}
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
                            scrollToTop={this._scrollToTop}
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
                            lockFileBrowser={props.isUploading}
                          />

                        </ErrorBoundary>)}
                    />

                  </Switch>

                </Route>

              </Switch>

            </div>

          </div>

          <div className="Dataset__veil" />

        </div>);
    }

    if (state.authenticated) {
      return (<Loader />);
    }

    return (<Login auth={props.auth} />);
  }
}

const mapStateToProps = (state, ownProps) => state.dataset;

const mapDispatchToProps = dispatch => ({
});

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

const backend = (manager: Object) => {
  const backend = HTML5Backend(manager);


  const orgTopDropCapture = backend.handleTopDropCapture;

  backend.handleTopDropCapture = (e) => {
    e.preventDefault();
    if (backend.currentNativeSource) {
      orgTopDropCapture.call(backend, e);

      backend.currentNativeSource.item.dirContent = getFilesFromDragEvent(e, { recursive: true }); // returns a promise
    }
  };

  return backend;
};

export default DragDropContext(backend)(DatasetFragmentContainer);
