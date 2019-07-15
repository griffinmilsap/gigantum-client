// vendor
import React, { Component } from 'react';
import { boundMethod } from 'autobind-decorator';
// mutations
import ChangeLabbookBaseMutation from 'Mutations/ChangeLabbookBaseMutation';
import BuildImageMutation from 'Mutations/container/BuildImageMutation';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
// components
import Modal from 'Components/common/Modal';
import ButtonLoader from 'Components/common/ButtonLoader';
import SelectBase from './create/SelectBase';
// assets
import './SelectBaseModal.scss';

/**
    @param {name, owner}
    builds docker iamge of labbook
*/
const buildImage = (name, owner) => {
  BuildImageMutation(
    owner,
    name,
    false,
    (response, error) => {
      if (error) {
        console.error(error);
        setErrorMessage(`ERROR: Failed to build ${name}`, error);
      }
    },
  );
}

export default class SelectBaseModal extends Component {
  state = {
    repository: '',
    componentId: '',
    revision: '',
    continueDisabled: true,
    changeBaseButtonState: '',
  }

  /**
    @param {boolean} menuVisibility
    shows hides navigation menu
  */
  _toggleMenuVisibility = (menuVisibility) => {
    this.setState({ menuVisibility });
  }

  /**
    @param {boolean} isDisabled
    setsContinueDisabled value to true or false
  */
  _toggleDisabledContinue = (isDisabled) => {
    this.setState({
      continueDisabled: isDisabled,
    });
  }

  /**
    @param {string, string ,Int} repository, componentId revision
    sets (repository, componentId and revision to state for create labbook mutation
  */
  _selectBaseCallback = (node) => {
    const {
      repository,
      componentId,
      revision,
    } = node;
    this.setState({
      repository,
      componentId,
      revision,
    });
  }

  /**
      @param {}
      sets name and description to state for change base mutation
  */
  _changeBaseMutation = () => {
    const { props } = this;
    const {
      owner,
      name,
    } = props;
    const {
      repository,
      componentId,
      revision,
    } = this.state;

    this.setState({
      changeBaseButtonState: 'loading',
    });

    document.getElementById('modal__cover').classList.remove('hidden');
    document.getElementById('loader').classList.remove('hidden');

    ChangeLabbookBaseMutation(
      owner,
      name,
      repository,
      componentId,
      revision,
      (response, error) => {
        if (error) {
          setErrorMessage('An error occured while trying to change bases.', error);

          this.setState({
            changeBaseButtonState: 'error',
          });
          setTimeout(() => {
            this.setState({
              changeBaseButtonState: '',
            });
          }, 2000);
        } else {
          this.setState({
            changeBaseButtonState: 'finished',
          });

          setTimeout(() => {

            buildImage(name, owner);

            this.setState({
              changeBaseButtonState: '',
            }, () => {
              props.toggleModal();
              document.getElementById('modal__cover').classList.add('hidden');
              document.getElementById('loader').classList.add('hidden');
            });
          }, 2000);
        }
      },
    );
  }

  render() {
    const { props, state } = this;
    return (
      <Modal
        size="large-long"
        handleClose={() => props.toggleModal()}
        header="Select a Base"
        preHeader="Modifying Environment"
        noPadding
        icon="change"
        renderContent={() => (
          <div className="SelectBaseModal">
            <SelectBase
              selectBaseCallback={this._selectBaseCallback}
              toggleDisabledContinue={this._toggleDisabledContinue}
              toggleMenuVisibility={this._toggleMenuVisibility}
            />
            <div className="SelectBaseModal__buttons flex justify--right">
              <button
                onClick={() => { props.toggleModal() }}
                className="Btn--flat"
                type="button"
              >
                Cancel
              </button>
              <ButtonLoader
                buttonState={state.changeBaseButtonState}
                buttonText="Change Base"
                className="Btn--last"
                params={{}}
                buttonDisabled={state.continueDisabled}
                clicked={this._changeBaseMutation}
              />
            </div>
          </div>
        )}
      />
    )
  }
}
