// vendor
import React, { Component } from 'react';
import { createFragmentContainer, graphql } from 'react-relay';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
import { setBuildingState } from 'JS/redux/actions/labbook/labbook';
import store from 'JS/redux/store';
// mutations
import BuildImageMutation from 'Mutations/container/BuildImageMutation';
import StopContainerMutation from 'Mutations/container/StopContainerMutation';
// components
import ErrorBoundary from 'Components/common/ErrorBoundary';
import Tooltip from 'Components/common/Tooltip';
import Loader from 'Components/common/Loader';
import Base from './Base';
import Packages from './packages/Packages';
import Secrets from './secrets/Secrets';
import CustomDockerfile from './CustomDockerfile';
// assets
import './Environment.scss';


class Environment extends Component {
  constructor(props) {
  	super(props);
    const { owner, labbookName } = store.getState().routes;

    this.state = {
      modal_visible: false,
      readyToBuild: false,
      show: false,
      message: '',
      owner,
      labbookName,
    };

    this._buildCallback = this._buildCallback.bind(this);
    this._setBase = this._setBase.bind(this);
  }

  componentDidMount() {
    const { props } = this;
    props.refetch('environment');
  }

  /**
  *  @param {Function} callback
  *  callback that triggers buildImage mutation
  */
  _buildCallback = (callback) => {
    const { labbookName, owner } = this.state;
    let buildData = false;
    if (callback) {
      buildData = {
        hideFooter: true,
      };
    }
    setBuildingState(true);
    if (store.getState().containerStatus.status === 'Running') {
      StopContainerMutation(
        owner,
        labbookName,
        (response, error) => {
          if (error) {
            console.log(error);
            setErrorMessage(`Problem stopping ${labbookName}`, error);
          } else {
            BuildImageMutation(
              owner,
              labbookName,
              buildData,
              (response, error, id) => {
                if (error) {
                  setErrorMessage(`${labbookName} failed to build`, error);
                }
                if (callback) {
                  callback(response, error, id);
                }

                return 'finished';
              },
            );
          }
        },
      );
    } else {
      BuildImageMutation(
        owner,
        labbookName,
        buildData,
        (response, error, id) => {
          if (error) {
            setErrorMessage(`${labbookName} failed to build`, error);
          }
          if (callback) {
            callback(response, error, id);
          }
          return 'finished';
        },
      );
    }
  }

  /**
  *  @param {Obect}
  *  sets readyToBuild state to true
  */
  _setBase(base) {
    this.setState({ readyToBuild: true });
  }

  render() {
    const { props } = this;
    if (props.labbook && props.labbook.environment && props.labbook.environment.id) {
      const { environment } = props.labbook;
      const { base } = environment;
      return (
        <div className="Environment">
          <div className="Base__headerContainer">
            <h4>
                Base&nbsp;&nbsp;&nbsp;
              <Tooltip section="baseEnvironment" />
            </h4>
          </div>
          <ErrorBoundary type="baseError" key="base">
            <Base
              ref="base"
              environment={environment}
              baseLatestRevision={environment.baseLatestRevision}
              environmentId={environment.id}
              editVisible
              containerStatus={props.containerStatus}
              setComponent={this._setComponent}
              setBase={this._setBase}
              buildCallback={this._buildCallback}
              blockClass="Environment"
              base={base}
              isLocked={props.isLocked}
              owner={props.owner}
              name={props.name}
            />
          </ErrorBoundary>
          <ErrorBoundary type="packageDependenciesError" key="packageDependencies">
            <Packages
              componentRef={ref => this.packageDependencies = ref}
              owner={props.owner}
              name={props.name}
              environment={props.labbook.environment}
              environmentId={props.labbook.environment.id}
              labbookId={props.labbook.id}
              containerStatus={props.containerStatus}
              setBase={this._setBase}
              setComponent={this._setComponent}
              buildCallback={this._buildCallback}
              overview={props.overview}
              base={base}
              isLocked={props.isLocked}
              packageLatestVersions={props.packageLatestVersions}
              packageLatestRefetch={props.packageLatestRefetch}
            />
          </ErrorBoundary>
          <CustomDockerfile
            dockerfile={props.labbook.environment.dockerSnippet}
            buildCallback={this._buildCallback}
            isLocked={props.isLocked}
          />
          <Secrets
            environment={props.labbook.environment}
            environmentId={props.labbook.environment.id}
            owner={props.owner}
            name={props.name}
            isLocked={props.isLocked}
          />
        </div>
      );
    }
    return (
      <Loader />
    );
  }
}

export default createFragmentContainer(
  Environment,
  graphql`fragment Environment_labbook on Labbook {
    environment @skip (if: $environmentSkip){
      id
      imageStatus
      containerStatus
      base{
        developmentTools
        packageManagers
      }
      dockerSnippet
      baseLatestRevision

      ...Base_environment
      ...Packages_environment
      ...Secrets_environment
    }
  }`,
);
