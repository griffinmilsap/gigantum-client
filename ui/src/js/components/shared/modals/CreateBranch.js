// vendor
import React, { Component } from 'react';
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
// assets
import './CreateBranch.scss';


/**
* @param {Object} props
* gets description, text warning and text length from props, returns as an object
* @ return {Object}
*/
const getBranchDescrtipion = (props) => {
  let branchDescription;
  const formatedTimestamp = props.selected
    ? Moment(Date.parse(props.selected.activityNode.timestamp)).format('M/DD/YY h:mm:ss A')
    : '';

  if (props.selected) {
    branchDescription = `${props.selected.description}. ${props.selected.activeBranch} at ${formatedTimestamp}.`;
  } else if (props.description) {
    branchDescription = props.description;
  } else {
    branchDescription = '';
  }
  branchDescription = branchDescription.substr(0, 80);

  const textLength = 80 - branchDescription.length;
  const textWarning = (textLength > 20)
    ? 'CreateBranch__warning--green'
    : 'CreateBranch__warning--orange';


  return {
    textWarning,
    branchDescription,
    textLength,
  };
};

type Props = {
  modalVisible: boolean,
  name: string,
  owner: string,
  selected: {
    activeBranch: string,
    activityNode: {
      timestamp: Number,
    },
    description: string,
  },
  setBuildingState: Function,
  toggleModal: Function,
}

class CreateBranchModal extends Component<Props> {
  constructor(props) {
    super(props);

    const {
      textWarning,
      branchDescription,
      textLength,
    } = getBranchDescrtipion(props);

    this.state = {
      modalVisible: props.modalVisible,
      showError: false,
      branchName: '',
      createButtonClicked: false,
      buttonLoaderCreateBranch: '',
      textWarning,
      branchDescription,
      textLength,
    };
  }


  static getDerivedStateFromProps(nextProps, state) {
    let { branchName } = state;
    if (nextProps.selected) {
      const { timestamp } = nextProps.selected.activityNode;
      const formattedTimestamp = Moment(Date.parse(timestamp)).format('MMDDYY-HHmmss').toLowerCase();
      branchName = `${nextProps.selected.activeBranch}-at-${formattedTimestamp}`;
    } else if (state.branchName && (typeof state.branchName === 'string') && (state.branchName.indexOf('rollback') > -1)) {
      branchName = '';
    }

    const modalVisible = (nextProps.modalVisible !== state.modalVisible)
      ? nextProps.modalVisible
      : state.modalVisible;

    return {
      ...state,
      branchName,
      modalVisible,
    };
  }

  /**
  *   @param {}
  *   shows modal by setting state
  *   @return {}
  */
  _showModal = () => {
    this.setState({ modalVisible: true });
  }

  /**
  *   @param {}
  *   hides modal by stetting state
  *   @return {}
  */
  _hideModal = (inputsDisabled) => {
    const { toggleModal } = this.props;
    if (!inputsDisabled) {
      this.setState({
        branchName: '',
        modalVisible: false,
      });

      if (toggleModal) {
        toggleModal('createBranchVisible');
      }
    }
  }

  /**
  *   @param {event,string} evt, key
  *   returns error text when a branch name is invalid
  *   @return {}
  */
  _getErrorText = () => {
    const { state } = this;
    return (state.errorType === 'send')
      ? 'Error: Last character cannot be a hyphen.'
      : 'Error: Branch name may only contain lowercase alphanumeric and `-`. (e.g. new-branch-name)';
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
  _formattedISO = date => dateFormat(date, 'isoDateTime').toLowerCase().replace(/:/g, '-');

  /**
  *   @param {}
  *   triggers CreateExperimentalBranchMutation
  *   @return {}
  */
  _createNewBranch = () => {
    const self = this;
    const {
      owner,
      name,
      selected,
      setBuildingState,
    } = this.props;
    const { branchName, branchDescription } = this.state;
    const revision = selected ? selected.activityNode.commit : null;

    this.setState({ buttonLoaderCreateBranch: 'loading' });

    CreateExperimentalBranchMutation(
      owner,
      name,
      branchName,
      revision,
      branchDescription,
      (response, error) => {
        if (error) {
          setErrorMessage(owner, name, 'Problem Creating new branch', error);

          setTimeout(() => {
            this.setState({ buttonLoaderCreateBranch: 'error' });
          }, 1000);
        } else {
          if (selected) {
            setBuildingState(owner, name, true);
            BuildImageMutation(
              owner,
              name,
              false,
              (response, error) => {
                if (error) {
                  setErrorMessage(owner, name, `${name} failed to build`, error);
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
    const { selected } = this.props;
    const {
      branchDescription,
      branchName,
      buttonLoaderCreateBranch,
      createButtonClicked,
      modalVisible,
      showError,
      textLength,
      textWarning,
    } = this.state;
    const createDisabled = showError
          || (branchName.length === 0)
          || createButtonClicked;
    const inputsDisabled = buttonLoaderCreateBranch !== '';
    const branchNameTimestamp = selected
      ? Moment(Date.parse(selected.activityNode.timestamp)).format('MMDDYY-HHmmss').toLowerCase()
      : '';
    const branchDefault = selected
      ? `${selected.activeBranch}-at-${branchNameTimestamp}`
      : '';
    const textAreaDefault = branchDescription;
    const branchModalTitle = selected ? 'Create Rollback Branch' : 'Create Branch';
    const icon = selected ? 'rollback' : 'add';

    // declare css here
    const inputCSS = classNames({
      'CreateBranch__input--invalid': showError,
    });
    const errorCSS = classNames({
      CreateBranch__error: showError,
      hidden: !showError,
    });

    return (
      <div>
        { modalVisible
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
                  <p className={`CreateBranch__warning ${textWarning}`}>{`${textLength} characters remaining`}</p>
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
                      buttonState={buttonLoaderCreateBranch}
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

export default CreateBranchModal;
