// vendor
import React, { Component } from 'react';
import Highlighter from 'react-highlight-words';
import { Link } from 'react-router-dom';
import Moment from 'moment';
import classNames from 'classnames';
import { boundMethod } from 'autobind-decorator';
// muations
import StartContainerMutation from 'Mutations/container/StartContainerMutation';
import StopContainerMutation from 'Mutations/container/StopContainerMutation';
// store
import { setErrorMessage, setInfoMessage } from 'JS/redux/actions/footer';
import store from 'JS/redux/store';
// assets
import './LocalLabbookPanel.scss';

/**
*  labbook panel is to only render the edge passed to it
*/

export default class LocalLabbookPanel extends Component {
  state = {
    exportPath: '',
    status: 'loading',
    textStatus: '',
    labbookName: this.props.edge.node.name,
    owner: this.props.edge.node.owner,
    cssClass: 'loading',
  };

  /** *
  * @param {Object} nextProps
  * processes container lookup and assigns container status to labbook card
  */
  static getDerivedStateFromProps(nextProps, state) {
    const { environment } = nextProps.node;
    if (environment) {
      const { containerStatus, imageStatus } = environment;
      let status = 'Running';
      status = (containerStatus === 'NOT_RUNNING') ? 'Stopped' : status;
      status = (imageStatus === 'BUILD_IN_PROGRESS' || imageStatus === 'BUILD_QUEUED') ? 'Building' : status;
      status = (imageStatus === 'BUILD_FAILED') ? 'Rebuild' : status;
      status = (imageStatus === 'DOES_NOT_EXIST') ? 'Rebuild' : status;

      status = ((state.status === 'Starting') && (containerStatus !== 'RUNNING')) || (state.status === 'Stopping' && (containerStatus !== 'NOT_RUNNING')) ? state.status : status;

      let textStatus = (status === 'Rebuild') ? 'Stopped' : status;
      textStatus = (state.textStatus === 'Start') ? 'Start' : textStatus;
      textStatus = (state.textStatus === 'Stop') ? 'Stop' : textStatus;

      state.status = status;
      state.textStatus = textStatus;
      state.cssClass = status;
    }

    return { ...state };
  }

  /** *
  * @param {string} status
  * fires when a componet mounts
  * adds a scoll listener to trigger pagination
  */
  @boundMethod
  _stopStartContainer(evt, status) {
    evt.preventDefault();
    evt.stopPropagation();
    evt.nativeEvent.stopImmediatePropagation();
    if (status === 'Stopped') {
      this._startContainerMutation();
    } else if (status === 'Running') {
      this._stopContainerMutation();
    } else if (status === 'loading') {
      setInfoMessage('Container status is still loading. The status will update when it is available.');
    } else if (status === 'Building') {
      setInfoMessage('Container is still building and the process may not be interrupted.');
    } else {
      this._rebuildContainer();
    }
  }

  /** *
  * @param {string} status
  * starts labbook conatainer
  */
  @boundMethod
  _startContainerMutation() {
    const self = this;

    const { owner, labbookName } = this.state;
    setInfoMessage(`Starting ${labbookName} container`);
    this.setState({ status: 'Starting', textStatus: 'Starting' });

    StartContainerMutation(
      owner,
      labbookName,
      (response, error) => {
        if (error) {
          setErrorMessage(`There was a problem starting ${this.state.labbookName}, go to Project and try again`, error);
        } else {
          self.props.history.replace(`../../projects/${owner}/${labbookName}`);
        }
      },
    );
  }

  /** *
  * @param {string} status
  * stops labbbok conatainer
  */
  @boundMethod
  _stopContainerMutation() {
    const { owner, labbookName } = this.state;

    const self = this;
    setInfoMessage(`Stopping ${labbookName} container`);
    this.setState({ status: 'Stopping', textStatus: 'Stopping' });

    StopContainerMutation(
      owner,
      labbookName,
      (response, error) => {
        if (error) {
          console.log(error);
          setErrorMessage(`There was a problem stopping ${this.state.labbookName} container`, error);
          self.setState({ textStatus: 'Running', status: 'Running' });
        } else {
          // this.setState({ status: 'Stopped', textStatus: 'Stopped' });
        }
      },
    );
  }

  /** *
  * @param {object,string} evt,status
  * stops labbbok conatainer
  ** */
  @boundMethod
  _updateTextStatusOver(evt, isOver, status) {
    const newStatus = status;
    if (isOver) {
      if (status === 'Running') {
        this.setState({ textStatus: 'Stop' });
      } else if (status === 'Stopped') {
        this.setState({ textStatus: 'Start' });
      }
    } else {
      this.setState({ textStatus: status });
    }
  }

  /** *
  * @param {objectstring} evt,status
  * stops labbbok conatainer
  ** */
  @boundMethod
  _updateTextStatusOut(evt, status) {
    if (status !== 'loading') {
      this.setState({ textStatus: status });
    }
  }

  render() {
    const { props, state } = this;
    const { edge } = props;
    const {
      status,
      textStatus,
      cssClass,
    } = state;

    const containerCSS = classNames({
      [`ContainerStatus__container-state ContainerStatus__containerStatus--state ${cssClass} box-shadow`]: true,
      'Tooltip-data': cssClass === 'Rebuild',
    });

    return (
      <Link
        to={`/projects/${edge.node.owner}/${edge.node.name}`}
        onClick={() => props.goToLabbook(edge.node.name, edge.node.owner)}
        key={`local${edge.node.name}`}
        className="Card Card--225 Card--text column-4-span-3 flex flex--column justify--space-between"
      >

        <div className="LocalLabbooks__row--icons">
          { !(props.visibility === 'local')
            && (
            <div
              data-tooltip={`${props.visibility}`}
              className={`Tooltip-Listing LocalLabbookPanel__${props.visibility} Tooltip-data Tooltip-data--small`}
            />
            )
          }

          <div className="LocalLabbooks__containerStatus">

            <div
              data-tooltip="Rebuild Required, container will attempt to rebuild before starting."
              onClick={evt => this._stopStartContainer(evt, cssClass)}
              onMouseOver={evt => this._updateTextStatusOver(evt, true, status)}
              onMouseOut={evt => this._updateTextStatusOut(evt, false, status)}
              className={containerCSS}
            >
              <div className="ContainerStatus__text">{ textStatus }</div>
              <div className="ContainerStatus__toggle">
                <div className="ContainerStatus__toggle-btn" />
              </div>
            </div>

          </div>

        </div>

        <div className="LocalLabbooks__row--text">

          <div>

            <h5
              className="LocalLabbooks__panel-title"
              onClick={() => this.props.goToLabbook(edge.node.name, edge.node.owner)}
            >

              <Highlighter
                highlightClassName="LocalLabbooks__highlighted"
                searchWords={[store.getState().labbookListing.filterText]}
                autoEscape={false}
                caseSensitive={false}
                textToHighlight={edge.node.name}
              />

            </h5>

          </div>

          <p className="LocalLabbooks__paragraph LocalLabbooks__paragraph--owner ">{edge.node.owner}</p>
          <p className="LocalLabbooks__paragraph LocalLabbooks__paragraph--metadata">
            <span className="bold">Created:</span>
            {' '}
            {Moment(edge.node.creationDateUtc).format('MM/DD/YY')}
          </p>
          <p className="LocalLabbooks__paragraph LocalLabbooks__paragraph--metadata">
            <span className="bold">Modified:</span>
            {' '}
            {Moment(edge.node.modifiedOnUtc).fromNow()}
          </p>

          <p className="LocalLabbooks__paragraph LocalLabbooks__paragraph--description">
            {
              edge.node.description && edge.node.description.length
                ? (
                  <Highlighter
                    highlightClassName="LocalLabbooks__highlighted"
                    searchWords={[store.getState().labbookListing.filterText]}
                    autoEscape={false}
                    caseSensitive={false}
                    textToHighlight={edge.node.description}
                  />
                )
                : (
                  <span> No description provided</span>
                )
            }
          </p>

        </div>
      </Link>
    );
  }
}
