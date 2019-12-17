// @flow
// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// store
import { setErrorMessage } from 'JS/redux/actions/footer';
// config
import config from 'JS/config';
import fetchQuery from 'JS/fetch';
// components
import ButtonLoader from 'Components/common/ButtonLoader';
import Modal from 'Components/common/Modal';
import CollaboratorsRow from './CollaboratorsRow';
import NoCollaborators from './NoCollaborators';
// mutations
import CollaboratorMutations from './mutations/CollaboratorMutations';
// assets
import './CollaboratorsModal.scss';

type Props = {
  canManageCollaborators: boolean,
  collaborators: Array,
  name: string,
  owner: string,
  sectionType: string,
  toggleCollaborators: Function,
};

class CollaboratorsModal extends Component<Props> {
  state = {
    owner: this.props.owner,
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

  mutations = new CollaboratorMutations(this.props);

  componentWillMount() {
    const { collaborators } = this.props;
    const buttonLoaderRemoveCollaborator = {};
    if (collaborators) {
      collaborators.forEach(({ collaboratorUsername }) => {
        buttonLoaderRemoveCollaborator[collaboratorUsername] = '';
      });
    }
    this.setState({ buttonLoaderRemoveCollaborator });
  }

  componentDidMount() {
    window.addEventListener('click', this._closePermissionsMenu);
  }

  /**
    * @param {} -
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
  _getPermissions = (permission, collaboratorName) => {
    const { state } = this;
    if ((permission === 'readonly') || (permission === 'READ_ONLY')) {
      return 'Read';
    } if ((permission === 'readwrite') || (permission === 'READ_WRITE')) {
      return 'Write';
    } if ((permission === 'owner') || (permission === 'OWNER')) {
      return (collaboratorName === state.owner) ? 'Owner' : 'Admin';
    }
    return 'Read';
  }

  /**
  *  @param {number} -
  *  iterate value of index within the bounds of the array size
  *  @return {}
  */
  _setSelectedIndex = (iterate) => {
    const { state } = this;
    let newSelectedIndex = state.selectedIndex + iterate;

    newSelectedIndex = (newSelectedIndex < 0)
      ? state.colloboratorSearchList.length - 1
      : newSelectedIndex;
    newSelectedIndex = (newSelectedIndex >= this.state.colloboratorSearchList.length)
      ? 0
      : newSelectedIndex;

    this.setState({ selectedIndex: newSelectedIndex });
  }

  /**
  *  @param {String} newPermissions
  *  assigns new permissions in state
  *  @return {}
  */
  _setPermission = (newPermissions) => {
    this.setState({ newPermissions });
  }

  /**
  *  @param {event} evt
  *  queries collaborator api and updates list
  *  @return {}
  */
  _getUsers = (evt) => {
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
  _togglePermissionsMenu = (userExpanded) => {
    const { state } = this;
    const { permissionMenuOpen } = state;
    const { canManageCollaborators } = this.props;
    if (canManageCollaborators) {
      if (userExpanded) {
        if (
          (userExpanded !== localStorage.getItem('username'))
          && (userExpanded !== state.owner)
        ) {
          const newUserExpanded = (state.userExpanded === userExpanded)
            ? null
            : userExpanded;
          this.setState({
            userExpanded: newUserExpanded,
          });
        }
      } else {
        this.setState({ permissionMenuOpen: !permissionMenuOpen });
      }
    }
  }

  /**
    *  @param {Event} evt
    *  toggles permissionMenuOpen in state
    *  @return {}
    */
  _closePermissionsMenu = (evt) => {
    const { permissionMenuOpen, userExpanded } = this.state;
    const isPermissionsMenuOpen = evt.target.className.indexOf('CollaboratorModal__PermissionsSelector--add') > -1;
    const isSinglePermissionsMenuOpen = evt.target.className.indexOf('CollaboratorModal__PermissionsSelector--individual') > -1;

    if (!isPermissionsMenuOpen && permissionMenuOpen) {
      this.setState({ permissionMenuOpen: false });
    }
    if (!isSinglePermissionsMenuOpen && userExpanded) {
      this.setState({ userExpanded: null });
    }
  }

  /**
  *  @param {event} evt
  *  queries collaborator api and updates list
  *  @return {}
  */
  _handleInputKeys = (evt) => {
    const {
      colloboratorSearchList,
      selectedIndex,
    } = this.state;
    if ((evt.type === 'click') || (evt.key === 'Enter')) {
      if (colloboratorSearchList.length > 0) {
        const collaborator = colloboratorSearchList[selectedIndex];

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
  _completeColloborator = (collaborator) => {
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
  _addCollaborator = (permissionOverride, collaboratorName) => {
    // TODO: cleanup this function
    const {
      newCollaborator,
      newPermissions,
    } = this.state;

    // waiting for backend updates
    if (!permissionOverride) {
      this.setState({ addCollaboratorButtonDisabled: true, buttonLoaderAddCollaborator: 'loading' });
    } else {
      const { buttonLoaderRemoveCollaborator } = this.state;
      buttonLoaderRemoveCollaborator[collaboratorName] = 'loading';
      this.setState({ buttonLoaderRemoveCollaborator });
    }
    const mutationData = {
      collaboratorName,
      newCollaborator,
      permissionOverride,
      newPermissions,
    };

    this.mutations.addCollaborator(
      mutationData,
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
    );
  }

  /**
  *  @param {object} params
  *  deletes collaborators using mutation
  *  @return {}
  */
  _removeCollaborator = (evt, data) => {
    const { owner, name } = this.props;
    const { collaborator, button } = data.params;
    const {
      buttonLoaderRemoveCollaborator,
    } = this.state;

    if (button) {
      button.disabled = true;
    }

    buttonLoaderRemoveCollaborator[collaborator] = 'loading';
    this.setState({ buttonLoaderRemoveCollaborator });
    const mutationData = {
      collaborator,
    };
    // TODO remove duplicate code
    this.mutations.deleteCollaborator(
      mutationData,
      (response, error) => {
        if (this.refs[collaborator]) {
          this.refs[collaborator].classList.remove('loading');
        }

        if (button) {
          button.disabled = false;
        }

        if (error) {
          setErrorMessage(owner, name, 'Could not remove collaborator', error);

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

  render() {
    const {
      canManageCollaborators,
      collaborators,
      sectionType,
      toggleCollaborators,
    } = this.props;
    const {
      addCollaboratorButtonDisabled,
      buttonLoaderAddCollaborator,
      colloboratorSearchList,
      newCollaborator,
      permissionMenuOpen,
      userExpanded,
    } = this.state;
    const disableAddButton = addCollaboratorButtonDisabled
      || (newCollaborator.length < 3);

    // declare css here
    const autoCompleteMenu = classNames({
      'CollaboratorsModal__auto-compelte-menu box-shadow': true,
      'CollaboratorsModal__auto-compelte-menu--visible': colloboratorSearchList.length > 0,
    });
    const permissionsSelectorCSS = classNames({
      'CollaboratorModal__PermissionsSelector Dropdown': true,
      'Dropdown--open': permissionMenuOpen,
      'CollaboratorModal__PermissionsSelector--add': true,
      'Dropdown--collapsed': !permissionMenuOpen,
    });
    const permissionsMenuCSS = classNames({
      'CollaboratorModal__PermissionsMenu Dropdown__menu box-shadow': true,
      hidden: !permissionMenuOpen,
    });
    const collaboratorList = classNames({
      CollaboratorsModal__list: true,
      'CollaboratorsModal__list--overflow': (userExpanded !== null),
    });

    return (
      <Modal
        header="Manage Collaborators"
        icon="user"
        size="large-long"
        overflow="visible"
        handleClose={() => { toggleCollaborators(); }}
        renderContent={() => (
          <div className="Modal__sizer">
            { canManageCollaborators
              ? (
                <div className="CollaboratorsModal__add">
                  <input
                    className="CollaboratorsModal__input--collaborators"
                    ref={(el) => { this.collaboratorSearch = el; }}

                    onChange={evt => this._getUsers(evt)}
                    onKeyUp={evt => this._getUsers(evt)}

                    type="text"
                    placeholder="Add Collaborator"

                    disabled={addCollaboratorButtonDisabled}
                  />

                  <div className={autoCompleteMenu}>
                    <ul className="CollaboratorsModal__list">
                      { colloboratorSearchList.slice(0, 7).map((collaborator, index) => {
                        const listItemCSS = classNames({
                          CollaboratorsModal__listItem: true,
                          'CollaboratorsModal__listItem--selected': (index === this.state.selectedIndex),
                        });
                        return (
                          <li
                            role="presentation"
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
                      role="presentation"
                      className={permissionsSelectorCSS}
                      onClick={() => this._togglePermissionsMenu()}
                    >
                      {this._getPermissions(this.state.newPermissions)}
                    </span>
                    <ul className={permissionsMenuCSS}>
                      <li
                        role="presentation"
                        onClick={() => this._setPermission('readonly')}
                      >
                        <div className="CollaboratorsModal__permissions-header">Read</div>
                        <div className="CollaboratorsModal__permissions-subtext">Read-only permissions. Can only pull updates</div>
                      </li>
                      {
                        (sectionType !== 'dataset')
                        && (
                          <li
                            role="presentation"
                            onClick={() => this._setPermission('readwrite')}
                          >
                            <div className="CollaboratorsModal__permissions-header">Write</div>
                            <div className="CollaboratorsModal__permissions-subtext">Read/Write permissions. Can sync to branches other than master</div>
                          </li>
                        )
                      }
                      <li
                        role="presentation"
                        onClick={() => this._setPermission('owner')}
                      >
                        <div className="CollaboratorsModal__permissions-header">Admin</div>
                        <div className="CollaboratorsModal__permissions-subtext">Admin permissions. Can sync to master and manage collaborators</div>
                      </li>
                    </ul>
                  </div>
                  <ButtonLoader
                    className="ButtonLoader__collaborator Btn__plus Btn--round Btn--medium"
                    buttonState={buttonLoaderAddCollaborator}
                    buttonText=""
                    params={{}}
                    buttonDisabled={disableAddButton}
                    clicked={() => this._addCollaborator()}
                  />

                </div>
              )
              : <NoCollaborators {...this.props} />
            }

            <div className="CollaboratorsModal__collaborators">

              <h5 className="CollaboratorsModal__h5">Collaborators</h5>

              <div className="CollaboratorsModal__listContainer">

                { collaborators
                  && (
                  <ul className={collaboratorList}>
                    {
                      (collaborators.length === 0)
                      && (
                        <h4 className="text-center">No Collaborators found</h4>
                      )
                    }
                    {
                      collaborators.map((collaborator) => {
                        const {
                          buttonLoaderRemoveCollaborator,
                        } = this.state;
                        const {
                          owner,
                        } = this.props;

                        return (
                          <CollaboratorsRow
                            addCollaborator={this._addCollaborator}
                            buttonLoaderRemoveCollaborator={buttonLoaderRemoveCollaborator}
                            canManageCollaborators={canManageCollaborators}
                            collaborator={collaborator}
                            getPermissions={this._getPermissions}
                            owner={owner}
                            removeCollaborator={this._removeCollaborator}
                            sectionType={sectionType}
                            togglePermissionsMenu={this._togglePermissionsMenu}
                            userExpanded={userExpanded}
                          />
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

export default CollaboratorsModal;
