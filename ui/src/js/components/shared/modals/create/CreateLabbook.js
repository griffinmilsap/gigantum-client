// vendor
import React from 'react';
import classNames from 'classnames';
// utilities
import validation from 'JS/utils/Validation';
// components
import LoginPrompt from 'Components/shared/modals/LoginPrompt';
// queries
import RepositoryNameIsAvailable from './queries/RepositoryNameIsAvailableQuery';
// assets
import './CreateLabbook.scss';

export default class CreateLabbook extends React.Component {
  state = {
    name: '',
    description: '',
    showError: false,
    errorType: '',
    textWarning: 'CreateLabbook__warning--green',
    textLength: 80,
    showLoginPrompt: false,
  };

  /**
  *   @param {} -
  *   takes an event input
  *   creates a labbook mutation sets labbook name on parent component
  *   triggers setComponent to proceed to next view
  * */
  continueSave = () => {
    const { props, state } = this;
    const { name, description } = state;

    props.setButtonState('loading');

    RepositoryNameIsAvailable.checkRespositoryName(name).then((response) => {
      if (response.data.repositoryNameIsAvailable) {
        props.createLabbookCallback(name, description);
        props.setButtonState('');
      } else {
        this.setState({
          name: '',
          showError: true,
          errorType: 'validation',
        });
        props.setButtonState('');
        this.createLabbookName.focus();
      }
    }).catch((error) => {
      console.log(error);
      props.setButtonState('error');
    });
  }

  /**
  *  @param {}
  *  closes login prompt modal
  *  @return {}
  */
  _closeLoginPromptModal = () => {
    this.setState({ showLoginPrompt: false });
  }

  /**
    @param {Object, string} evt,field
    updates text in a state object and passes object to setState method
  */
  _updateTextState = (evt, field) => {
    const state = {};
    const { props } = this;

    state[field] = evt.target.value;

    if (field === 'name') {
      const isMatch = validation.labbookName(evt.target.value);
      this.setState({
        showError: ((isMatch === false) && (evt.target.value.length > 0)),
        errorType: '',
      });

      props.toggleDisabledContinue((evt.target.value === '') || (isMatch === false));
    } else {
      const textLength = 80 - evt.target.value.length;
      if (textLength > 21) {
        state.textWarning = 'CreateLabbook__warning--green';
      } else if ((textLength <= 21)) {
        state.textWarning = 'CreateLabbook__warning--orange';
      }
      state.textLength = textLength;
    }

    this.setState(state);
  }

  /**
    @param {}
    returns error message
    @return {string} errorMessage
  */
  _getErrorText() {
    switch (this.state.errorType) {
      case 'send':
        return 'Error: Last character cannot be a hyphen.';
      case 'validation':
        return 'Name is already in use, please enter another name.';
      default:
        return 'Error: Title may only contain lowercase alphanumeric and `-`. (e.g. lab-book-title)';
    }
  }

  render() {
    const { props, state } = this;
    const type = props.datasets ? 'Dataset' : 'Project';
    // declare css here
    const inputCSS = classNames({
      invalid: state.showError,
    });
    const errorSpanCSS = classNames({
      error: state.showError,
      hidden: !state.showError,
    });

    return (
      <div className="CreateLabbook">
        { state.showLoginPrompt &&
          <LoginPrompt closeModal={this._closeLoginPromptModal} />
        }
        <div>
          <div className="CreateLabbook__name">
            <label htmlFor="CreateLabbookName">
              Title
              <input
                ref={(input) => { this.createLabbookName = input; }}
                id="CreateLabbookName"
                type="text"
                maxLength="36"
                className={inputCSS}
                onChange={evt => this._updateTextState(evt, 'name')}
                placeholder="Enter a unique, descriptive title"
              />
            </label>
            <span className={errorSpanCSS}>
              {this._getErrorText()}
            </span>
          </div>

          <div className="CreateLabbook__description">
            <label htmlFor="CreateLabbookDescription">
              Description
              <textarea
                id="CreateLabbookDescription"
                maxLength="80"
                className="CreateLabbook__description-input"
                type="text"
                onChange={evt => this._updateTextState(evt, 'description')}
                placeholder={`Briefly describe this ${type}, its purpose and any other key details.`}
              />
            </label>

            <p className={`CreateLabbook__warning ${state.textWarning}`}>
              {`${this.state.textLength} characters remaining`}
            </p>
          </div>

        </div>
      </div>
    );
  }
}
