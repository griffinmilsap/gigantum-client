// vendor
import React, { Component } from 'react';
import uuidv4 from 'uuid/v4';
import Highlighter from 'react-highlight-words';
import classNames from 'classnames';
import Moment from 'moment';
// muations
import ImportRemoteLabbookMutation from 'Mutations/repository/import/ImportRemoteLabbookMutation';
import BuildImageMutation from 'Mutations/container/BuildImageMutation';
// store
import store from 'JS/redux/store';
import { setWarningMessage, setMultiInfoMessage } from 'JS/redux/actions/footer';
// queries
import UserIdentity from 'JS/Auth/UserIdentity';
// components
import LoginPrompt from 'Components/shared/modals/LoginPrompt';
import Loader from 'Components/common/Loader';
// assets
import './RemoteLabbookPanel.scss';

type Props = {
  auth: {
    renewToken: Function,
  },
  edge: {
    node: {
      importUrl: string,
    }
  },
  existsLocally: boolean,
  toggleDeleteModal: Function,
}

class RemoteLabbookPanel extends Component<Props> {
  state = {
    isImporting: false,
    showLoginPrompt: false,
  };

  /**
    *  @param {}
    *  changes state of isImporting to false
  */
  _clearState = () => {
    if (document.getElementById('dashboard__cover')) {
      document.getElementById('dashboard__cover').classList.add('hidden');
    }
    this.setState({
      isImporting: false,
    });
  }

  /**
    *  @param {}
    *  changes state of isImporting to true
  */
  _importingState = () => {
    document.getElementById('modal__cover').classList.remove('hidden');
    document.getElementById('loader').classList.remove('hidden');
    this.setState({
      isImporting: true,
    });
  }

  /**
    *  @param {owner, labbookName}
    *  imports labbook from remote url, builds the image, and redirects to imported labbook
    *  @return {}
  */
  _importLabbook = (owner, labbookName) => {
    // TODO break up this function
    const { auth, edge } = this.props;
    const self = this;
    const id = uuidv4();
    const remote = edge.node.importUrl;

    UserIdentity.getUserIdentity().then((response) => {
      if (navigator.onLine) {
        if (response.data) {
          if (response.data.userIdentity.isSessionValid) {
            this._importingState();
            const messageData = {
              id,
              message: 'Importing Project please wait',
              isLast: false,
              error: false,
            };
            setMultiInfoMessage(owner, labbookName, messageData);
            const successCall = () => {
              this._clearState();
              const mulitMessageData = {
                id,
                message: `Successfully imported remote Project ${labbookName}`,
                isLast: true,
                error: false,
              };
              setMultiInfoMessage(owner, labbookName, mulitMessageData);


              BuildImageMutation(
                owner,
                labbookName,
                false,
                (response, error) => {
                  if (error) {
                    console.error(error);
                    const buildMessageData = {
                      id,
                      owner,
                      name: labbookName,
                      message: `ERROR: Failed to build ${labbookName}`,
                      isLast: null,
                      error: true,
                      messageBody: error,
                    };
                    setMultiInfoMessage(owner, labbookName, buildMessageData);
                  }
                },
              );

              self.props.history.replace(`/projects/${owner}/${labbookName}`);
            };
            const failureCall = (error) => {
              this._clearState();
              const failureMessageData = {
                id,
                owner,
                name: labbookName,
                message: 'ERROR: Could not import remote Project',
                isLast: null,
                error: true,
                messageBody: error,
              };
              setMultiInfoMessage(owner, labbookName, failureMessageData);
            };
            self.setState({ isImporting: true });

            ImportRemoteLabbookMutation(
              owner,
              labbookName,
              remote,
              successCall,
              failureCall,
              (response, error) => {
                if (error) {
                  failureCall(error);
                }
                self.setState({ isImporting: false });
              },
            );
          } else {
            auth.renewToken(true, () => {
              this.setState({ showLoginPrompt: true });
            }, () => {
              this._importLabbook(owner, labbookName);
            });
          }
        }
      } else {
        this.setState({ showLoginPrompt: true });
      }
    });
  }

  /**
   * @param {}
   * fires when user identity returns invalid session
   * prompts user to revalidate their session
   */
  _closeLoginPromptModal = () => {
    this.setState({
      showLoginPrompt: false,
    });
  }

  /**
   * @param {object} edge
   * validates user's session and then triggers toggleDeleteModal
   * which passes parameters to the DeleteLabbook component
  */
  _handleDelete = (edge) => {
    // TODO: move toggleDeleteModal
    const { auth, existsLocally, toggleDeleteModal } = this.props;
    if (localStorage.getItem('username') !== edge.node.owner) {
      const { owner, name } = edge.node;
      setWarningMessage(owner, name, 'You can only delete remote Projects that you have created.');
    } else {
      UserIdentity.getUserIdentity().then((response) => {
        if (navigator.onLine) {
          if (response.data) {
            if (response.data.userIdentity.isSessionValid) {
              toggleDeleteModal({
                remoteId: edge.node.id,
                remoteUrl: edge.node.remoteUrl,
                remoteOwner: edge.node.owner,
                remoteLabbookName: edge.node.name,
                existsLocally,
              });
            } else {
              auth.renewToken(true, () => {
                this.setState({ showLoginPrompt: true });
              }, () => {
                toggleDeleteModal({
                  remoteId: edge.node.id,
                  remoteUrl: edge.node.remoteUrl,
                  remoteOwner: edge.node.owner,
                  remoteLabbookName: edge.node.name,
                  existsLocally,
                });
              });
            }
          }
        } else {
          this.setState({ showLoginPrompt: true });
        }
      });
    }
  }


  render() {
    // variables declared here
    const { isImporting, showLoginPrompt } = this.state;
    const { edge, existsLocally } = this.props;
    const deleteDisabled = isImporting || (localStorage.getItem('username') !== edge.node.owner);
    const deleteTooltipText = (localStorage.getItem('username') !== edge.node.owner) ? 'Only owners and admins can delete a remote Project' : '';

    // css declared here
    const descriptionCss = classNames({
      'RemoteLabbooks__row RemoteLabbooks__row--text': true,
      blur: isImporting,
    });
    const deleteCSS = classNames({
      'Btn__dashboard Btn--action': true,
      'Tooltip-data Tooltip-data--wide': localStorage.getItem('username') !== edge.node.owner,
      'Btn__dashboard--delete': localStorage.getItem('username') === edge.node.owner,
      'Btn__dashboard--delete-disabled': localStorage.getItem('username') !== edge.node.owner,
    });

    return (
      <div
        key={edge.node.name}
        className="Card Card--225 column-4-span-3 flex flex--column justify--space-between"
      >
        <div className="RemoteLabbooks__row RemoteLabbooks__row--icon">
          { !(edge.node.visibility === 'local')
            && (
            <div
              data-tooltip={`${edge.node.visibility}`}
              className={`Tooltip-Listing RemoteLabbooks__${edge.node.visibility} Tooltip-data Tooltip-data--small`}
            />
            )
          }
          { existsLocally
            ? (
              <button
                type="button"
                className="Btn__dashboard Btn--action Btn__dashboard--cloud Btn__Tooltip-data"
                data-tooltip="This Project has already been imported"
                disabled
              >
              Imported
              </button>
            )
            : (
              <button
                type="button"
                disabled={isImporting}
                className="Btn__dashboard Btn--action Btn__dashboard--cloud-download"
                onClick={() => this._importLabbook(edge.node.owner, edge.node.name)}
              >
              Import
              </button>
            )
          }

          <button
            type="button"
            className={deleteCSS}
            data-tooltip={deleteTooltipText}
            disabled={deleteDisabled}
            onClick={() => this._handleDelete(edge)}
          >
           Delete
          </button>

        </div>

        <div className={descriptionCss}>

          <div className="RemoteLabbooks__row RemoteLabbooks__row--title">
            <h5 className="RemoteLabbooks__panel-title">
              <Highlighter
                highlightClassName="LocalLabbooks__highlighted"
                searchWords={[store.getState().labbookListing.filterText]}
                autoEscape={false}
                caseSensitive={false}
                textToHighlight={edge.node.name}
              />
            </h5>

          </div>

          <p className="RemoteLabbooks__paragraph RemoteLabbooks__paragraph--owner">{edge.node.owner}</p>
          <p className="RemoteLabbooks__paragraph RemoteLabbooks__paragraph--metadata">
            <span className="bold">Created:</span>
            {' '}
            {Moment(edge.node.creationDateUtc).format('MM/DD/YY')}
          </p>
          <p className="RemoteLabbooks__paragraph RemoteLabbooks__paragraph--metadata">
            <span className="bold">Modified:</span>
            {' '}
            {Moment(edge.node.modifiedDateUtc).fromNow()}
          </p>

          <p className="RemoteLabbooks__paragraph RemoteLabbooks__paragraph--description">
            { (edge.node.description && edge.node.description.length)
              ? (
                <Highlighter
                  highlightClassName="LocalLabbooks__highlighted"
                  searchWords={[store.getState().labbookListing.filterText]}
                  autoEscape={false}
                  caseSensitive={false}
                  textToHighlight={edge.node.description}
                />
              )
              : 'No description provided'
           }
          </p>
        </div>

        { isImporting
          && (
            <div className="RemoteLabbooks__loader">
              <Loader />
            </div>
          )
        }

        { showLoginPrompt
          && <LoginPrompt closeModal={this._closeLoginPromptModal} />
        }
      </div>
    );
  }
}

export default RemoteLabbookPanel;
