// vendor
import React, { Component } from 'react';
import uuidv4 from 'uuid/v4';
// mutations
import SetVisibilityMutation from 'Mutations/SetVisibilityMutation';
import SetDatasetVisibilityMutation from 'Mutations/SetDatasetVisibilityMutation';
import PublishLabbookMutation from 'Mutations/branches/PublishLabbookMutation';
import PublishDatasetMutation from 'Mutations/branches/PublishDatasetMutation';
// component
import Modal from 'Components/common/Modal';
// store
import { setErrorMessage, setInfoMessage, setMultiInfoMessage } from 'JS/redux/reducers/footer';
import store from 'JS/redux/store';
// assets
import './VisibilityModal.scss';


export default class PublishModal extends Component {
  constructor(props) {
    super(props);

    this._publishLabbook = this._publishLabbook.bind(this);
    this._changeVisibility = this._changeVisibility.bind(this);
  }

  state = {
    isPublic: (this.props.visibility === 'public'),
  }

  /**
  *  @param {boolean}
  *  sets public state
  *  @return {string}
  */
  _setPublic(isPublic) {
    this.setState({
      isPublic,
    });
  }

  /**
  *  @param {}
  *  adds remote url to labbook
  *  @return {string}
  */
  _changeVisibility() {
    const self = this;
    const visibility = this.state.isPublic ? 'public' : 'private';

    this.props.toggleModal(this.props.modalStateValue);

    const {
      owner,
      labbookName,
    } = this.props;


    this.props.checkSessionIsValid().then((response) => {
      if (navigator.onLine) {
        if (response.data) {
          if (response.data.userIdentity.isSessionValid) {
            if (this.props.visibility !== visibility) {
              if (this.props.sectionType === 'labbook') {
                SetVisibilityMutation(
                  owner,
                  labbookName,
                  visibility,
                  (response, error) => {
                    if (error) {
                      console.log(error);
                      setErrorMessage('Visibility change failed', error);
                    } else {
                      setInfoMessage(`Visibility changed to ${visibility}`);
                    }
                  },
                );
              } else {
                SetDatasetVisibilityMutation(
                  owner,
                  labbookName,
                  visibility,
                  (response, error) => {
                    if (error) {
                      console.log(error);
                      setErrorMessage('Visibility change failed', error);
                    } else {
                      setInfoMessage(`Visibility changed to ${visibility}`);
                    }
                  },
                );
              }
            }
          } else {
            self.props.auth.renewToken(true, () => {
              self.props.resetState();
            }, () => {
              self._changeVisibility();
            });
          }
        }
      } else {
        self.props.resetState();
      }
    });
  }

  /**
  *  @param {}
  *  adds remote url to labbook
  *  @return {string}
  */
  _publishLabbook() {
    const id = uuidv4();
    const self = this;

    this.props.toggleModal();

    const {
      owner,
      labbookName,
      labbookId,
    } = this.props;

    this.props.checkSessionIsValid().then((response) => {
      if (navigator.onLine) {
        if (response.data) {
          if (response.data.userIdentity.isSessionValid) {
            if (store.getState().containerStatus.status !== 'Running') {
              self.props.resetPublishState(true);

              if (!self.props.remoteUrl) {
                self.props.setPublishingState(true);

                const failureCall = () => {
                  self.props.setPublishingState(false);
                  self.props.resetPublishState(false);
                };

                const successCall = () => {
                  self.props.setPublishingState(false);
                  self.props.resetPublishState(false);
                  // self.props.remountCollab();

                  setMultiInfoMessage(id, `Added remote https://gigantum.com/${self.props.owner}/${self.props.labbookName}`, true, false);

                  self.props.setRemoteSession();
                };

                if (this.props.sectionType === 'labbook') {
                  PublishLabbookMutation(
                    owner,
                    labbookName,
                    labbookId,
                    this.state.isPublic,
                    successCall,
                    failureCall,
                    (response, error) => {
                      if (error) {
                        failureCall();
                      }
                    },
                  );
                } else {
                  PublishDatasetMutation(
                    owner,
                    labbookName,
                    this.state.isPublic,
                    successCall,
                    failureCall,
                    (response, error) => {
                      if (error) {
                        failureCall();
                      }
                    },
                  );
                }
              }
            }
          } else {
            self.props.auth.renewToken(true, () => {
              self.props.resetState();
            }, () => {
              self._publishLabbook();
            });
          }
        }
      } else {
        self.props.resetState();
      }
    });
  }

  _modifyVisibility() {
    if (this.props.header === 'Publish') {
      this._publishLabbook();
    } else {
      this._changeVisibility();
    }
  }


  render() {
    const { props } = this;

    return (

      <Modal
        header={props.header}
        handleClose={() => props.toggleModal(props.modalStateValue)}
        size="large"
        icon={props.visibility}
        renderContent={() => (
          <div className="VisibilityModal">
            <div>
              <p>You are about to change the visibility of the project.</p>
            </div>

            <div>
              <div className="VisibilityModal__private">


                <label htmlFor="publish_private">
                  <input
                    defaultChecked={(props.visibility === 'private') || !this.state.isPublic}
                    type="radio"
                    name="publish"
                    id="publish_private"
                    onClick={() => { this._setPublic(false); }}
                  />
                  <b>Private</b>
                </label>

                <p className="VisibilityModal__paragraph">Private projects are only visible to collaborators. Users that are added as a collaborator will be able to view and edit.</p>

              </div>

              <div className="VisibilityModal__public">

                <label htmlFor="publish_public">
                  <input
                    defaultChecked={props.visibility === 'public'}
                    name="publish"
                    type="radio"
                    id="publish_public"
                    onClick={() => { this._setPublic(true); }}
                  />
                  <b>Public</b>
                </label>

                <p className="VisibilityModal__paragraph">Public projects are visible to everyone. Users will be able to import a copy. Only users that are added as a collaborator will be able to edit.</p>

              </div>

            </div>

            <div className="VisibilityModal__buttons">
              <button className="Btn--flat" onClick={() => { props.toggleModal(props.modalStateValue); }}>Cancel</button>
              <button className="Btn--last" onClick={() => { this._modifyVisibility(); }}>{props.buttonText}</button>
            </div>

          </div>
        )
        }
      />
    );
  }
}
