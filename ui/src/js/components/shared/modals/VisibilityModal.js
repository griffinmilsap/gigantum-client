// @flow
// vendor
import React, { Component } from 'react';
import uuidv4 from 'uuid/v4';
// mutations
import SetVisibilityMutation from 'Mutations/repository/visibility/SetVisibilityMutation';
import SetDatasetVisibilityMutation from 'Mutations/repository/visibility/SetDatasetVisibilityMutation';
import PublishLabbookMutation from 'Mutations/branches/PublishLabbookMutation';
import PublishDatasetMutation from 'Mutations/branches/PublishDatasetMutation';
// component
import Modal from 'Components/common/Modal';
// store
import {
  setErrorMessage,
  setInfoMessage,
  setMultiInfoMessage,
} from 'JS/redux/actions/footer';

import store from 'JS/redux/store';
// assets
import './VisibilityModal.scss';

type Props = {
  auth: {
    renewToken: Function,
  },
  buttonText: string,
  checkSessionIsValid: Function,
  header: string,
  labbookId: string,
  modalStateValue: Object,
  name: string,
  owner: string,
  remoteUrl: string,
  resetState: Function,
  resetPublishState: Function,
  setRemoteSession: Function,
  setPublishingState: Function,
  sectionType: string,
  toggleModal: Function,
  visibility: bool,
}

class VisibilityModal extends Component<Props> {
  state = {
    isPublic: (this.props.visibility === 'public'),
  }

  /**
  *  @param {boolean}
  *  sets public state
  *  @return {string}
  */
  _setPublic = (isPublic) => {
    this.setState({
      isPublic,
    });
  }

  /**
  *  @param {}
  *  adds remote url to labbook
  *  @return {string}
  */
  _changeVisibility = () => {
    const { props, state } = this;
    const self = this;
    const visibility = state.isPublic ? 'public' : 'private';
    const {
      auth,
      checkSessionIsValid,
      modalStateValue,
      owner,
      name,
      resetState,
      sectionType,
      toggleModal,
    } = this.props;

    toggleModal(modalStateValue);


    checkSessionIsValid().then((response) => {
      if (navigator.onLine) {
        if (response.data) {
          if (response.data.userIdentity.isSessionValid) {
            if (props.visibility !== visibility) {
              if (sectionType === 'labbook') {
                SetVisibilityMutation(
                  owner,
                  name,
                  visibility,
                  (visibilityResponse, error) => {
                    if (error) {
                      console.log(error);
                      setErrorMessage(owner, name, 'Visibility change failed', error);
                    } else {
                      setInfoMessage(owner, name, `Visibility changed to ${visibility}`);
                    }
                  },
                );
              } else {
                SetDatasetVisibilityMutation(
                  owner,
                  name,
                  visibility,
                  (visibilityResponse, error) => {
                    if (error) {
                      console.log(error);
                      setErrorMessage(owner, name, 'Visibility change failed', error);
                    } else {
                      setInfoMessage(owner, name, `Visibility changed to ${visibility}`);
                    }
                  },
                );
              }
            }
          } else {
            auth.renewToken(true, () => {
              resetState();
            }, () => {
              self._changeVisibility();
            });
          }
        }
      } else {
        resetState();
      }
    });
  }

  /**
  *  @param {}
  *  adds remote url to labbook
  *  @return {string}
  */
  _publishLabbook = () => {
    const { props, state } = this;
    const id = uuidv4();
    const self = this;
    const {
      auth,
      checkSessionIsValid,
      owner,
      name,
      labbookId,
      remoteUrl,
      resetState,
      resetPublishState,
      sectionType,
      setPublishingState,
      setRemoteSession,
      toggleModal,
    } = this.props;

    toggleModal();

    checkSessionIsValid().then((response) => {
      if (navigator.onLine) {
        if (response.data) {
          if (response.data.userIdentity.isSessionValid) {
            if (store.getState().containerStatus.status !== 'Running') {
              resetPublishState(true);

              if (!remoteUrl) {
                setPublishingState(owner, name, true);

                const failureCall = () => {
                  setPublishingState(owner, name, false);
                  resetPublishState(false);
                };

                const successCall = () => {
                  setPublishingState(owner, name, false);
                  resetPublishState(false);
                  // self.props.remountCollab();
                  const messageData = {
                    id,
                    message: `Added remote https://gigantum.com/${owner}/${name}`,
                    isLast: true,
                    error: false,
                  };
                  setMultiInfoMessage(owner, name, messageData);

                  setRemoteSession();
                };

                if (sectionType === 'labbook') {
                  PublishLabbookMutation(
                    owner,
                    name,
                    labbookId,
                    state.isPublic,
                    successCall,
                    failureCall,
                    (publishResponse, error) => {
                      if (error) {
                        failureCall();
                      }
                    },
                  );
                } else {
                  PublishDatasetMutation(
                    owner,
                    name,
                    state.isPublic,
                    successCall,
                    failureCall,
                    (publishResponse, error) => {
                      if (error) {
                        failureCall();
                      }
                    },
                  );
                }
              }
            }
          } else {
            auth.renewToken(true, () => {
              resetState();
            }, () => {
              self._publishLabbook();
            });
          }
        }
      } else {
        resetState();
      }
    });
  }

  /**
  *  @param {} -
  *  triggers publish or change visibility
  *  @return {}
  */
  _modifyVisibility = () => {
    const { header } = this.props;
    if (header === 'Publish') {
      this._publishLabbook();
    } else {
      this._changeVisibility();
    }
  }


  render() {
    const {
      buttonText,
      header,
      modalStateValue,
      toggleModal,
      visibility,
    } = this.props;
    const { isPublic } = this.state;
    const publishStatement = header === 'Publish' ? 'Once published, the Project will be visible in the Gigantum Hub tab on the Projects listing Page.' : '';
    const message = `You are about to change the visibility of the Project. ${publishStatement}`;

    return (
      <Modal
        header={header}
        handleClose={() => toggleModal(modalStateValue)}
        size="large"
        icon={visibility}
        renderContent={() => (
          <div className="VisibilityModal">
            <div>
              <p>{message}</p>
            </div>

            <div>
              <div className="VisibilityModal__private">
                <label
                  className="Radio"
                  htmlFor="publish_private"
                >
                  <input
                    defaultChecked={(visibility === 'private') || !isPublic}
                    type="radio"
                    name="publish"
                    id="publish_private"
                    onClick={() => { this._setPublic(false); }}
                  />
                  <span><b>Private</b></span>
                </label>

                <p className="VisibilityModal__paragraph">Private projects are only visible to collaborators. Users that are added as a collaborator will be able to view and edit.</p>

              </div>

              <div className="VisibilityModal__public">

                <label
                  className="Radio"
                  htmlFor="publish_public"
                >
                  <input
                    defaultChecked={visibility === 'public'}
                    name="publish"
                    type="radio"
                    id="publish_public"
                    onClick={() => { this._setPublic(true); }}
                  />
                  <span><b>Public</b></span>
                </label>

                <p className="VisibilityModal__paragraph">Public projects are visible to everyone. Users will be able to import a copy. Only users that are added as a collaborator will be able to edit.</p>

              </div>

            </div>

            <div className="VisibilityModal__buttons">
              <button
                type="submit"
                className="Btn--flat"
                onClick={() => { toggleModal(modalStateValue); }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="Btn--last"
                onClick={() => { this._modifyVisibility(); }}
              >
                {buttonText}
              </button>
            </div>

          </div>
        )
        }
      />
    );
  }
}

export default VisibilityModal;
