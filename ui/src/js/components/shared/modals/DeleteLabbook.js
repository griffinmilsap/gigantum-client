// @flow
// vendor
import React, { Component } from 'react';
// Mutations
import DeleteLabbookMutation from 'Mutations/repository/delete/DeleteLabbookMutation';
import DeleteRemoteLabbookMutation from 'Mutations/repository/delete/DeleteRemoteLabbookMutation';
// components
import ButtonLoader from 'Components/common/ButtonLoader';
import Modal from 'Components/common/Modal';
// store
import {
  setErrorMessage,
  setWarningMessage,
  setInfoMessage,
} from 'JS/redux/actions/footer';
// assets
import './DeleteLabbook.scss';

type Props = {
  name: string,
  owner: string,
  handleClose: Function,
  remoteDelete: bool,
  remoteId: string,
  labbookListId: string,
  remoteConnection: bool,
  toggleModal: Function,
  existsLocally: bool,
  remoteAdded: bool,
  history: Object,
};

export default class DeleteLabbook extends Component<Props> {
  state = {
    name: '',
    deletePending: false,
    deleteLabbookButtonState: '',
  };

  /**
    @param {object} evt
    sets state of name
  */
  _setLabbookName = (evt) => {
    this.setState({ name: evt.target.value });
  }

  /**
    @param {}
    fires appropriate delete labbook mutation
  */
  _deleteLabbook = () => {
    const {
      name,
      owner,
      remoteDelete,
      remoteId,
      labbookListId,
      remoteConnection,
      toggleModal,
      history,
    } = this.props;
    const { state } = this;


    if (name === state.name) {
      this.setState({
        deletePending: true,
        deleteLabbookButtonState: 'loading',
      });

      if (remoteDelete) {
        DeleteRemoteLabbookMutation(
          name,
          owner,
          true,
          remoteId,
          labbookListId,
          remoteConnection,
          (response, error) => {
            this.setState({ deletePending: false });

            if (error) {
              setErrorMessage(owner, name, `The was a problem deleting ${name}`, error);
              this.setState({ deleteLabbookButtonState: 'error' });
              setTimeout(() => {
                this.setState({
                  name: '',
                  deletePending: false,
                  deleteLabbookButtonState: '',
                });

                toggleModal();

                if (document.getElementById('deleteInput')) {
                  document.getElementById('deleteInput').value = '';
                }
              }, 1000);
            } else {
              setInfoMessage(owner, name, `${name} has been remotely deleted`);
              this.setState({ deleteLabbookButtonState: 'finished' });

              setTimeout(() => {
                this.setState({
                  name: '',
                  deletePending: false,
                  deleteLabbookButtonState: '',
                });
                toggleModal();

                if (document.getElementById('deleteInput')) {
                  document.getElementById('deleteInput').value = '';
                }
              }, 1000);
            }
          },
        );
      } else {
        DeleteLabbookMutation(
          name,
          owner,
          true,
          (response, error) => {
            this.setState({ deletePending: false });

            if (error) {
              setErrorMessage(owner, name, `The was a problem deleting ${name}`, error);
              this.setState({ deleteLabbookButtonState: 'error' });
              setTimeout(() => {
                this.setState({ deleteLabbookButtonState: '' });
              }, 2000);
            } else {
              setInfoMessage(owner, name, `${name} has been deleted`);
              this.setState({ deleteLabbookButtonState: 'finished' });
              setTimeout(() => {
                history.replace('../../projects/');
              }, 2000);
            }
          },
        );
      }
    } else {
      setWarningMessage(owner, name, 'Names do not match');
    }
  }

  /**
    *  @param {}
    *  determines the warning text to be displayed to the user
  */
  _getExplanationText = () => {
    const {
      name,
      owner,
      remoteDelete,
      existsLocally,
      remoteAdded,
    } = this.props;

    if (remoteDelete) {
      if (existsLocally) {
        return (
          <div>
            <p>
              This will delete
              {' '}
              <b>{name}</b>
              {' '}
              from the cloud.
            </p>
            <p>The Project will still exist locally.</p>
          </div>
        );
      }
      return (
        <p>
          This will delete
          {' '}
          <b>{name}</b>
          {' '}
          from the cloud. All data will be removed and can not be recovered.
        </p>
      );
    } if (remoteAdded) {
      return (
        <div>
          <p>
            This will delete
            {' '}
            <b>{name}</b>
            {' '}
            from this Gigantum client.
          </p>
          <p>{`You can still download it from gigantum.com/${owner}/${name}.`}</p>
        </div>
      );
    }
    return (
      <p>
        This will delete
        {' '}
        <b>{name}</b>
        {' '}
        from this Gigantum instance. All data will be removed and can not be recovered.
      </p>
    );
  }

  render() {
    const {
      name,
      handleClose,
      remoteDelete,
    } = this.props;
    const { state } = this;
    const deleteText = remoteDelete ? 'Delete Remote Project' : 'Delete Project';

    return (
      <Modal
        header={deleteText}
        handleClose={() => handleClose()}
        size="medium"
        icon="delete"
        renderContent={() => (
          <div className="DeleteLabbook">
            {this._getExplanationText()}

            <input
              id="deleteInput"
              placeholder={`Enter ${name} to delete`}
              onKeyUp={(evt) => { this._setLabbookName(evt); }}
              onChange={(evt) => { this._setLabbookName(evt); }}
              type="text"
            />

            <div className="DeleteProject__buttons">
              <button
                type="button"
                className="Btn Btn--flat"
                onClick={() => handleClose()}
              >
                Cancel
              </button>
              <ButtonLoader
                className="Btn Btn--wide Btn--last"
                buttonState={state.deleteLabbookButtonState}
                buttonText={deleteText}
                params={{}}
                buttonDisabled={state.deletePending || name !== state.name}
                clicked={this._deleteLabbook}
              />
            </div>
          </div>
        )
        }
      />
    );
  }
}
