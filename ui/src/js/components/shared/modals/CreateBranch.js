// vendor
import React, { Component, Fragment } from 'react';
import dateFormat from 'dateformat';
import Moment from 'moment';
import classNames from 'classnames';
// Mutations
import CreateExperimentalBranchMutation from 'Mutations/branches/CreateExperimentalBranchMutation';
// components
import ButtonLoader from 'Components/common/ButtonLoader';
import Modal from 'Components/common/Modal';
// utilities
import validation from 'JS/utils/Validation';
import BuildImageMutation from 'Mutations/container/BuildImageMutation';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
import store from 'JS/redux/store';
// assets
import './CreateBranch.scss';

export default class CreateBranchModal extends Component {
  constructor(props) {
    super(props);
    let branchDescription = props.selected ? `${props.selected.description}. ${props.selected.activeBranch} at ${formatedTimestamp}.` : props.description ? props.description : '';
    branchDescription = branchDescription.substr(0, 80);
    const textLength = 80 - branchDescription.length;


    const formatedCurrentTimestamp = Moment().format('M/DD/YY h:mm:ss A');


    const formatedTimestamp = props.selected ? Moment(Date.parse(props.selected.activityNode.timestamp)).format('M/DD/YY h:mm:ss A') : '';


    const textWarning = textLength > 20 ? 'CreateBranch__warning--green' : 'CreateBranch__warning--orange';

    this.state = {
      modalVisible: props.modalVisible,
      showLoginPrompt: false,
      showError: false,
      branchName: '',
      createButtonClicked: false,
      buttonLoaderCreateBranch: '',
      textWarning,
      branchDescription,
      textLength,
    };

    this._showModal = this._showModal.bind(this);
    this._hideModal = this._hideModal.bind(this);
    this._createNewBranch = this._createNewBranch.bind(this);
    this._updateTextState = this._updateTextState.bind(this);
  }


  UNSAFE_componentWillReceiveProps(nextProps) {
    const { state } = this;
    if (nextProps.modalVisible !== state.modalVisible) {
      this.setState({ modalVisible: nextProps.modalVisible });
    }

    if (nextProps.selected) {
      const formattedTimestamp = Moment(Date.parse(nextProps.selected.activityNode.timestamp)).format('MMDDYY-HHmmss').toLowerCase();
      const branchName = `${nextProps.selected.activeBranch}-at-${formattedTimestamp}`;
      this.setState({ branchName });
    } else if (state.branchName && (typeof state.branchName === 'string') && (state.branchName.indexOf('rollback') > -1)) {
      this.setState({ branchName: '' });
    }
  }

  /**
  *   @param {}
  *   shows modal by setting state
  *   @return {}
  */
  _showModal() {
    this.setState({ modalVisible: true });
  }

  /**
  *   @param {}
  *   hides modal by stetting state
  *   @return {}
  */
  _hideModal(inputsDisabled) {
    const { props } = this;
    if (!inputsDisabled) {
      this.setState({
        branchName: '',
        modalVisible: false,
      });

      if (props.toggleModal) {
        props.toggleModal('createBranchVisible');
      }
    }
  }

  /**
  *   @param {event,string} evt, key
  *   returns error text when a branch name is invalid
  *   @return {}
  */
  _getErrorText() {
    const { state } = this;
    return state.errorType === 'send' ? 'Error: Last character cannot be a hyphen.' : 'Error: Branch name may only contain lowercase alphanumeric and `-`. (e.g. new-branch-name)';
  }

  /**
  *   @param {event,string} evt, key
  *   sets state of text using a key
  *   @return {}
  */
  _updateTextState = (evt, key) => {
    const state = {};

    if (key === 'branchName') {
      const isMatch = validation.labbookName(evt.target.value);
      if (isMatch) {
        this.setState({
          branchName: evt.target.value,
          errorType: '',
          showError: false,
        });
      } else {
        this.setState({
          showError: ((isMatch === false) && (evt.target.value.length > 0)),
          errorType: '',
          branchName: (evt.target.value === '') ? '' : state.branchName,
        });
      }
    } else {
      state[key] = evt.target.value;
    }
    if (key === 'branchDescription') {
      const textLength = 80 - evt.target.value.length;
      if ((textLength <= 80) && (textLength > 20)) {
        state.textWarning = 'CreateBranch__warning--green';
      } else if (textLength < 20) {
        state.textWarning = 'CreateBranch__warning--orange';
      }
      state.textLength = textLength;
    }

    this.setState(state);
  }

  /**
  *   @param {}
  *   formats date for branch name
  *   @return {}
  */
  _formattedISO(date) {
    return dateFormat(date, 'isoDateTime').toLowerCase().replace(/:/g, '-');
  }

  /**
  *   @param {}
  *   triggers CreateExperimentalBranchMutation
  *   @return {}
  */
  _createNewBranch() {
    const self = this;


    const { state, props } = this;


    const { owner, labbookName } = store.getState().routes;


    const { branchName } = this.state;


    const revision = props.selected ? props.selected.activityNode.commit : null;


    this.setState({ buttonLoaderCreateBranch: 'loading' });

    CreateExperimentalBranchMutation(
      owner,
      labbookName,
      branchName,
      revision,
      state.branchDescription,
      (response, error) => {
        if (error) {
          setErrorMessage('Problem Creating new branch', error);

          setTimeout(() => {
            this.setState({ buttonLoaderCreateBranch: 'error' });
          }, 1000);
        } else {
          if (props.selected) {
            props.setBuildingState(owner, labbookName, true);
            BuildImageMutation(
              owner,
              labbookName,
              false,
              (response, error) => {
                if (error) {
                  setErrorMessage(`${labbookName} failed to build`, error);
                }

                return 'finished';
              },
            );
          }

          this.setState({ buttonLoaderCreateBranch: 'finished' });
        }

        setTimeout(() => {
          this.setState({ buttonLoaderCreateBranch: '' });

          if (self._hideModal) {
            self._hideModal();
          }
        }, 2000);
      },
    );
  }

  render() {
    const { props, state } = this;
    const createDisabled = state.showError
          || (state.branchName.length === 0)
          || state.createButtonClicked;
    const inputsDisabled = state.buttonLoaderCreateBranch !== '';
    const branchNameTimestamp = props.selected ? Moment(Date.parse(props.selected.activityNode.timestamp)).format('MMDDYY-HHmmss').toLowerCase() : '';
    const branchDefault = props.selected ? `${props.selected.activeBranch}-at-${branchNameTimestamp}` : '';
    const textAreaDefault = state.branchDescription;
    const inputCSS = classNames({
      'CreateBranch__input--invalid': state.showError,
    });
    const errorCSS = classNames({
      CreateBranch__error: state.showError,
      hidden: !state.showError,
    });
    const branchModalTitle = props.selected ? 'Create Rollback Branch' : 'Create Branch';
    const icon = props.selected ? 'rollback' : 'add';

    return (
      <div>
        { state.modalVisible
          && (
          <Modal
            handleClose={() => { this._hideModal(inputsDisabled); }}
            size="large"
            header={branchModalTitle}
            icon={icon}
            renderContent={() => (
              <div className="CreateBranch">
                <div className="CreateBranch__name">
                  <label
                    htmlFor="CreateBranchName"
                  >
                    Name
                    <input
                      id="CreateBranchName"
                      type="text"
                      maxLength="80"
                      className={inputCSS}
                      onChange={evt => this._updateTextState(evt, 'branchName')}
                      onKeyUp={evt => this._updateTextState(evt, 'branchName')}
                      placeholder="Enter a unique branch name"
                      defaultValue={branchDefault}
                      disabled={inputsDisabled}
                    />
                  </label>
                  <span className={errorCSS}>{this._getErrorText()}</span>
                </div>

                <div className="CreateBranch__description">
                  <label
                    id="CreateBranchDescription__label"
                    htmlFor="CreateBranchDescription"
                  >
                    Description
                    <textarea
                      id="CreateBranchDescription"
                      className="CreateBranch__input--description"
                      disabled={inputsDisabled}
                      onChange={evt => this._updateTextState(evt, 'branchDescription')}
                      onKeyUp={evt => this._updateTextState(evt, 'branchDescription')}
                      maxLength="80"
                      placeholder="Briefly describe this branch, its purpose and any other key details. "
                      defaultValue={textAreaDefault}
                    />
                  </label>
                  <p className={`CreateBranch__warning ${state.textWarning}`}>{`${state.textLength} characters remaining`}</p>
                </div>

                <div className="CreateBranch_nav">
                  <div className="CreateBranch__buttons">
                    <button
                      type="submit"
                      disabled={inputsDisabled}
                      onClick={() => { this._hideModal(); }}
                      className="CreateBranch__btn--progress Btn--flat"
                    >
                      Cancel
                    </button>

                    <ButtonLoader
                      className="Btn--last"
                      ref="buttonLoaderCreateBranch"
                      buttonState={state.buttonLoaderCreateBranch}
                      buttonText="Create"
                      params={{}}
                      buttonDisabled={createDisabled}
                      clicked={this._createNewBranch}
                    />
                  </div>
                </div>
              </div>
            )
          }
          />
          )
        }
      </div>

    );
  }
}
