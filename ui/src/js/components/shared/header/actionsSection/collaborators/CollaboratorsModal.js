// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import { boundMethod } from 'autobind-decorator';
// Mutations
import AddCollaboratorMutation from 'Mutations/AddCollaboratorMutation';
import AddDatasetCollaboratorMutation from 'Mutations/AddDatasetCollaboratorMutation';
import DeleteCollaboratorMutation from 'Mutations/DeleteCollaboratorMutation';
import DeleteDatasetCollaboratorMutation from 'Mutations/DeleteDatasetCollaboratorMutation';

// store
import { setErrorMessage } from 'JS/redux/actions/footer';
// config
import config from 'JS/config';
import fetchQuery from 'JS/fetch';
// components
import ButtonLoader from 'Components/common/ButtonLoader';
import Modal from 'Components/common/Modal';
import NoCollaborators from './NoCollaborators';
// assets
import './CollaboratorsModal.scss';

export default class CollaboratorsModal extends Component {
  constructor(props) {
  	super(props);
    const {
      labbookName,
      owner,
    } = props;

  	this.state = {
      labbookName,
      owner,
      addCollaboratorButtonDisabled: false,
      newCollaborator: '',
      newPermissions: 'readonly',
      permissionMenuOpen: false,
      userExpanded: null,
      buttonLoaderRemoveCollaborator: {},
      buttonLoaderAddCollaborator: '',
      colloboratorSearchList: [],
      selectedIndex: 0,
    };

    this._addCollaborator = this._addCollaborator.bind(this);
    this._removeCollaborator = this._removeCollaborator.bind(this);
    this._completeColloborator = this._completeColloborator.bind(this);
  }

  componentDidMount() {
    const buttonLoaderRemoveCollaborator = {};

    this.props.collaborators.forEach(({ collaboratorUsername }) => {
      buttonLoaderRemoveCollaborator[collaboratorUsername] = '';
    });
    window.addEventListener('click', this._closePermissionsMenu);

    this.setState({ buttonLoaderRemoveCollaborator });
  }

  /**
    * @param {}
    * fires when component unmounts
    * removes added event listeners
  */
  componentWillUnmount() {
    window.removeEventListener('click', this._closePermissionsMenu);
  }

  /**
    *  @param {String} permission
    *  @param {String} CollaboratorName
    *  gets permissions value and displays it to the UI more clearly
  */
  _getPermissions(permission, collaboratorName) {
    if ((permission === 'readonly') || (permission === 'READ_ONLY')) {
      return 'Read';
    } if ((permission === 'readwrite') || (permission === 'READ_WRITE')) {
      return 'Write';
    } if ((permission === 'owner') || (permission === 'OWNER')) {
      return collaboratorName === this.state.owner ? 'Owner' : 'Admin';
    }
    return 'Read';
  }

  /**
  *  @param {number}
  *  iterate value of index within the bounds of the array size
  *  @return {}
  */
  _setSelectedIndex(iterate) {
    let newSelectedIndex = this.state.selectedIndex + iterate;

    newSelectedIndex = (newSelectedIndex < 0) ? this.state.colloboratorSearchList.length - 1 : newSelectedIndex;
    newSelectedIndex = (newSelectedIndex >= this.state.colloboratorSearchList.length) ? 0 : newSelectedIndex;

    this.setState({ selectedIndex: newSelectedIndex });
  }

  /**
  *  @param {String} newPermissions
  *  assigns new permissions in state
  *  @return {}
  */
  _setPermission(newPermissions) {
    this.setState({ newPermissions });
  }

  /**
  *  @param {event} evt
  *  queries collaborator api and updates list
  *  @return {}
  */
  _getUsers(evt) {
    const userInput = evt.target.value;

    if ((userInput.length > 2) && (evt.key !== 'Enter')) {
      const apiURL = evt.target.value.indexOf('@') > 0 ? config.userAPI.getUserEmailQueryString(evt.target.value) : config.userAPI.getUsersQueryString(evt.target.value);

      fetchQuery(apiURL).then((response) => {
        const collaborators = response.hits.hit.map(hit => hit.fields);

        this.setState({ colloboratorSearchList: collaborators });
      });
    } else {
      this.setState({ colloboratorSearchList: [] });
    }


    this._handleInputKeys(evt);
  }

  /**
  *  @param {String} userExpanded
  *  toggles permissionMenuOpen in state or assigns userexpanded a name
  *  @return {}
  */
  _togglePermissionsMenu(userExpanded) {
    const { props, state } = this;
    if (props.canManageCollaborators) {
      if (userExpanded) {
        if ((userExpanded !== localStorage.getItem('username')) && (userExpanded !== state.owner)) {
          this.setState({
            userExpanded: (state.userExpanded === userExpanded) ? null : userExpanded,
          });
        }
      } else {
        this.setState({ permissionMenuOpen: !state.permissionMenuOpen });
      }
    }
  }

  /**
    *  @param {Event} evt
    *  toggles permissionMenuOpen in state
    *  @return {}
    */
  @boundMethod
  _closePermissionsMenu(evt) {
    const isPermissionsMenuOpen = evt.target.className.indexOf('CollaboratorModal__PermissionsSelector--add') > -1;
    const isSinglePermissionsMenuOpen = evt.target.className.indexOf('CollaboratorModal__PermissionsSelector--individual') > -1;

    if (!isPermissionsMenuOpen && this.state.permissionMenuOpen) {
      this.setState({ permissionMenuOpen: false });
    }
    if (!isSinglePermissionsMenuOpen && this.state.userExpanded) {
      this.setState({ userExpanded: null });
    }
  }

  /**
  *  @param {event} evt
  *  queries collaborator api and updates list
  *  @return {}
  */
  _handleInputKeys(evt) {
    if ((evt.type === 'click') || (evt.key === 'Enter')) {
      if (this.state.colloboratorSearchList.length > 0) {
        const collaborator = this.state.colloboratorSearchList[this.state.selectedIndex];

        this._completeColloborator(collaborator);
      } else {
        this._addCollaborator();
      }
    } else if (evt.key === 'ArrowDown') {
      this._setSelectedIndex(1);
    } else if (evt.key === 'ArrowUp') {
      this._setSelectedIndex(-1);
    } else {
      this.setState({ newCollaborator: evt.target.value });
    }
  }

  /**
  *  @param {event} evt
  *  queries collaborator api and updates list
  *  @return {}
  */
  _completeColloborator(collaborator) {
    if (collaborator) {
      this.collaboratorSearch.value = collaborator.username;

      this.setState({
        newCollaborator: collaborator.username,
        colloboratorSearchList: [],
        selectedIndex: 0,
      });
    }
  }

  /**
  *  @param {String} permissionOverride
  *  @param {String} collaboratorName
  *  sets state of Collaborators
  *  @return {}
  */
  _addCollaborator(permissionOverride, collaboratorName) {
    const {
      labbookName,
      owner,
      newCollaborator,
      newPermissions,
    } = this.state;

    const { props } = this;

    // waiting for backend updates
    if (!permissionOverride) {
      this.setState({ addCollaboratorButtonDisabled: true, buttonLoaderAddCollaborator: 'loading' });
    } else {
      const { buttonLoaderRemoveCollaborator } = this.state;
      buttonLoaderRemoveCollaborator[collaboratorName] = 'loading';
      this.setState({ buttonLoaderRemoveCollaborator });
    }

    if (props.sectionType === 'dataset') {
        AddDatasetCollaboratorMutation(
          labbookName,
          owner,
          collaboratorName || newCollaborator,
          permissionOverride || newPermissions,
          (response, error) => {
            const completeState = this.state.buttonLoaderRemoveCollaborator;

            if (permissionOverride && completeState[collaboratorName]) {
              if (error) {
                completeState[collaboratorName] = 'error';
              } else {
                completeState[collaboratorName] = 'finished';
              }
              this.setState({
                buttonLoaderRemoveCollaborator: completeState,
                buttonLoaderAddCollaborator: '',
              });

              setTimeout(() => {
                const postCompleteState = this.state.buttonLoaderRemoveCollaborator;
                postCompleteState[collaboratorName] = '';
                this.setState({ buttonLoaderAddCollaborator: '' });
              }, 2000);
            } else {
              completeState[newCollaborator] = '';

              this.setState({ newCollaborator: '', addCollaboratorButtonDisabled: false, buttonLoaderRemoveCollaborator: completeState });

              this.collaboratorSearch.value = '';

              if (error) {
                this.setState({ buttonLoaderAddCollaborator: 'error' });
              } else {
                this.setState({ buttonLoaderAddCollaborator: 'finished' });
              }

              setTimeout(() => {
                this.setState({ buttonLoaderAddCollaborator: '' });
              }, 2000);
            }
          },
        )

      } else {
        AddCollaboratorMutation(
          labbookName,
          owner,
          collaboratorName || newCollaborator,
          permissionOverride || newPermissions,
          (response, error) => {
            const completeState = this.state.buttonLoaderRemoveCollaborator;

            if (permissionOverride && completeState[collaboratorName]) {
              if (error) {
                completeState[collaboratorName] = 'error';
              } else {
                completeState[collaboratorName] = 'finished';
              }
              this.setState({ buttonLoaderRemoveCollaborator: completeState, addCollaboratorButtonDisabled: false, newCollaborator: '' });

              setTimeout(() => {
                const postCompleteState = this.state.buttonLoaderRemoveCollaborator;
                postCompleteState[collaboratorName] = '';
                this.setState({ buttonLoaderAddCollaborator: '' });
              }, 2000);
            } else {
              completeState[newCollaborator] = '';

              this.setState({ newCollaborator: '', addCollaboratorButtonDisabled: false, buttonLoaderRemoveCollaborator: completeState });

              this.collaboratorSearch.value = '';

              if (error) {
                setErrorMessage('Could not add collaborator', error);

                this.setState({ buttonLoaderAddCollaborator: 'error' });
              } else {
                this.setState({ buttonLoaderAddCollaborator: 'finished' });
              }

              setTimeout(() => {
                this.setState({
                  buttonLoaderAddCollaborator: '',
                  addCollaboratorButtonDisabled: false,
                });
              }, 2000);
            }
          },
        )

      }
  }

  /**
  *  @param {object} params
  *  deletes collaborators using mutation
  *  @return {}
  */
  _removeCollaborator(evt, data) {
    const { props, state } = this;
    const { collaborator, button } = data.params;
    const { buttonLoaderRemoveCollaborator, owner, labbookName } = state;

    if (button) {
      button.disabled = true;
    }

    buttonLoaderRemoveCollaborator[collaborator] = 'loading';
    this.setState({ buttonLoaderRemoveCollaborator });
    // TODO remove duplicate code
    if (props.sectionType === 'dataset') {
      DeleteDatasetCollaboratorMutation(
        labbookName,
        owner,
        collaborator,
        (response, error) => {
          if (this.refs[collaborator]) {
            this.refs[collaborator].classList.remove('loading');
          }

          if (button) {
            button.disabled = false;
          }

          if (error) {
            setErrorMessage('Could not remove collaborator', error);

            buttonLoaderRemoveCollaborator[collaborator] = 'error';

            this.setState({ buttonLoaderRemoveCollaborator });
          } else {
            buttonLoaderRemoveCollaborator[collaborator] = 'finished';

            this.setState({ buttonLoaderRemoveCollaborator });
          }

          setTimeout(() => {
            buttonLoaderRemoveCollaborator[collaborator] = '';

            this.setState({ buttonLoaderRemoveCollaborator });
          }, 2000);
        },
      );
    } else {
      DeleteCollaboratorMutation(
        labbookName,
        owner,
        collaborator,
        (response, error) => {
          if (this.refs[collaborator]) {
            this.refs[collaborator].classList.remove('loading');
          }

          if (button) {
            button.disabled = false;
          }

          if (error) {
            setErrorMessage('Could not remove collaborator', error);

            buttonLoaderRemoveCollaborator[collaborator] = 'error';

            this.setState({ buttonLoaderRemoveCollaborator });
          } else {
            buttonLoaderRemoveCollaborator[collaborator] = 'finished';

            this.setState({ buttonLoaderRemoveCollaborator });
          }

          setTimeout(() => {
            buttonLoaderRemoveCollaborator[collaborator] = '';

            this.setState({ buttonLoaderRemoveCollaborator });
          }, 2000);
        },
      );
    }
  }

  render() {
    const { props, state } = this;
    const disableAddButton = state.addCollaboratorButtonDisabled || (state.newCollaborator.length < 3);

    // declare css here
    const autoCompleteMenu = classNames({
      'CollaboratorsModal__auto-compelte-menu box-shadow': true,
      'CollaboratorsModal__auto-compelte-menu--visible': state.colloboratorSearchList.length > 0,
    });
    const permissionsSelectorCSS = classNames({
      'CollaboratorModal__PermissionsSelector Dropdown': true,
      'Dropdown--open': state.permissionMenuOpen,
      'CollaboratorModal__PermissionsSelector--add': true,
      'Dropdown--collapsed': !state.permissionMenuOpen,
    });
    const permissionsMenuCSS = classNames({
      'CollaboratorModal__PermissionsMenu Dropdown__menu box-shadow': true,
      hidden: !state.permissionMenuOpen,
    });
    const collaboratorList = classNames({
      CollaboratorsModal__list: true,
      'CollaboratorsModal__list--overflow': (state.userExpanded !== null),
    });

    return (
      <Modal
        header="Manage Collaborators"
        icon="user"
        size="large-long"
        overflow="visible"
        handleClose={() => { props.toggleCollaborators(); }}
        renderContent={() => (
          <div className="Modal__sizer">
            { props.canManageCollaborators
              ? (
                <div className="CollaboratorsModal__add">
                  <input
                    className="CollaboratorsModal__input--collaborators"
                    ref={el => this.collaboratorSearch = el}

                    onChange={evt => this._getUsers(evt)}
                    onKeyUp={evt => this._getUsers(evt)}

                    type="text"
                    placeholder="Add Collaborator"

                    disabled={this.state.addCollaboratorButtonDisabled}
                  />

                  <div className={autoCompleteMenu}>
                    <ul className="CollaboratorsModal__list">
                      { state.colloboratorSearchList.slice(0, 7).map((collaborator, index) => {
                        const listItemCSS = classNames({
                          CollaboratorsModal__listItem: true,
                          'CollaboratorsModal__listItem--selected': (index === this.state.selectedIndex),
                        });
                        return (
                          <li
                            onClick={() => this._completeColloborator(collaborator)}
                            className={listItemCSS}
                            key={collaborator.username}
                          >
                            <div className="CollaboratorsModal__listItem--username">{collaborator.username}</div>
                            <div className="CollaboratorsModal__listItem--name">{collaborator.name}</div>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                  <div className="CollaboratorsModal__permissions">
                    <span
                      className={permissionsSelectorCSS}
                      onClick={() => this._togglePermissionsMenu()}
                    >
                      {this._getPermissions(this.state.newPermissions)}
                    </span>
                    <ul className={permissionsMenuCSS}>
                      <li onClick={() => this._setPermission('readonly')}>
                        <div className="CollaboratorsModal__permissions-header">Read</div>
                        <div className="CollaboratorsModal__permissions-subtext">Read-only permissions. Can only pull updates</div>
                      </li>
                      {
                        (props.sectionType !== 'dataset')
                        && (
                          <li onClick={() => this._setPermission('readwrite')}>
                            <div className="CollaboratorsModal__permissions-header">Write</div>
                            <div className="CollaboratorsModal__permissions-subtext">Read/Write permissions. Can sync to branches other than master</div>
                          </li>
                        )
                      }
                      <li onClick={() => this._setPermission('owner')}>
                        <div className="CollaboratorsModal__permissions-header">Admin</div>
                        <div className="CollaboratorsModal__permissions-subtext">Admin permissions. Can sync to master and manage collaborators</div>
                      </li>
                    </ul>
                   </div>
                   <ButtonLoader
                      className="ButtonLoader__collaborator Btn__plus Btn--round Btn--medium"
                      ref="addCollaborator"

                      buttonState={this.state.buttonLoaderAddCollaborator}
                      buttonText=""

                      params={{}}
                      buttonDisabled={disableAddButton}
                      clicked={() => this._addCollaborator()}
                    />

                 </div>
                )
                : <NoCollaborators {...props} />
            }

            <div className="CollaboratorsModal__collaborators">

              <h5 className="CollaboratorsModal__h5">Collaborators</h5>

              <div className="CollaboratorsModal__listContainer">

                { props.collaborators
                  && (
                  <ul className={collaboratorList}>
                    {
                      props.collaborators.map((collaborator) => {
                        const collaboratorName = collaborator.collaboratorUsername;
                        const collaboratorItemCSS = classNames({
                          'CollaboratorsModal__item CollaboratorsModal__item--me': (collaborator.collaboratorUsername === localStorage.getItem('username')),
                          CollaboratorsModal__item: !(collaborator.collaboratorUsername === localStorage.getItem('username')),
                        });
                        const individualPermissionsSelectorCSS = classNames({
                          CollaboratorModal__PermissionsSelector: true,
                          'CollaboratorModal__PermissionsSelector--individual': true,
                          'CollaboratorModal__PermissionsSelector--open': state.userExpanded === collaboratorName,
                          'CollaboratorModal__PermissionsSelector--disabled': (collaboratorName === localStorage.getItem('username'))
                            || !props.canManageCollaborators
                            || (collaboratorName === state.owner),
                          'CollaboratorModal__PermissionsSelector--collapsed': (state.userExpanded !== collaboratorName),
                        });
                        const individualPermissionsMenuCSS = classNames({
                          'CollaboratorModal__PermissionsMenu box-shadow': true,
                          'CollaboratorModal__PermissionsMenu--individual': true,
                          hidden: (state.userExpanded !== collaboratorName),
                        });
                        const disableButtonLoader = collaboratorName === localStorage.getItem('username') || !props.canManageCollaborators || (collaboratorName === state.owner);
                        return (
                          <li
                            key={collaboratorName}
                            ref={collaboratorName}
                            className={collaboratorItemCSS}
                          >
                            <div className="CollaboratorsModal__collaboratorName">{collaboratorName}</div>

                            <div className="CollaboratorsModal__permissions CollaboratorsModal__permissions--individual CollaboratorsModal__permissions--small">
                              <span
                                className={individualPermissionsSelectorCSS}
                                onClick={() => this._togglePermissionsMenu(collaboratorName)}
                              >
                                {this._getPermissions(collaborator.permission, collaboratorName)}
                              </span>
                              <ul className={individualPermissionsMenuCSS}>
                                <li onClick={() => this._addCollaborator('readonly', collaboratorName)}>
                                  <div className="CollaboratorsModal__permissions-header">Read</div>
                                  <div className="CollaboratorsModal__permissions-subtext">Read-only permissions. Can only pull updates</div>
                                </li>
                                {
                                  (props.sectionType !== 'dataset')
                                  && (
                                  <li onClick={() => this._addCollaborator('readwrite', collaboratorName)}>
                                      <div className="CollaboratorsModal__permissions-header">Write</div>
                                    <div className="CollaboratorsModal__permissions-subtext">Read/Write permissions. Can sync to branches other than master</div>
                                  </li>
                                  )
                                }
                                <li onClick={() => this._addCollaborator('owner', collaboratorName)}>
                                  <div className="CollaboratorsModal__permissions-header">Admin</div>
                                  <div className="CollaboratorsModal__permissions-subtext">Admin permissions. Can sync to master and managed collaborators</div>
                                </li>
                              </ul>
                            </div>

                            <ButtonLoader
                              ref={collaboratorName}
                              buttonState={state.buttonLoaderRemoveCollaborator[collaboratorName]}
                              buttonText=""
                              className="ButtonLoader__collaborator Btn__remove Btn--round Btn--small"
                              params={{ collaborator: collaboratorName, button: this }}
                              buttonDisabled={disableButtonLoader}
                              clicked={this._removeCollaborator}
                            />

                          </li>
                        );
                      })
                    }
                  </ul>
                  )
                }
              </div>
            </div>
          </div>
        )
        }
      />
    );
  }
}
