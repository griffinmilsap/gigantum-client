// @flow
// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// components
import ButtonLoader from 'Components/common/ButtonLoader';
// css
import './CollaboratorsRow.scss';

type Props = {
  addCollaborator: Function,
  buttonLoaderRemoveCollaborator: Object,
  canManageCollaborators: boolean,
  collaborator: {
    collaboratorUsername: string,
    permission: boolean,
  },
  getPermissions: Function,
  owner: string,
  removeCollaborator: Function,
  sectionType: string,
  togglePermissionsMenu: Function,
  userExpanded: boolean,
}

class CollaboratorsRow extends Component<Props> {
  render() {
    const {
      addCollaborator,
      buttonLoaderRemoveCollaborator,
      canManageCollaborators,
      collaborator,
      getPermissions,
      owner,
      removeCollaborator,
      sectionType,
      togglePermissionsMenu,
      userExpanded,
    } = this.props;

    const collaboratorName = collaborator.collaboratorUsername;
    const username = localStorage.getItem('username');
    const isUser = collaboratorName === username;
    const disableButtonLoader = collaboratorName === localStorage.getItem('username') || !canManageCollaborators || (collaboratorName === owner);
    // decalre css here
    const collaboratorItemCSS = classNames({
      'CollaboratorsModal__item CollaboratorsModal__item--me': isUser,
      CollaboratorsModal__item: !isUser,
    });
    const individualPermissionsSelectorCSS = classNames({
      CollaboratorModal__PermissionsSelector: true,
      'CollaboratorModal__PermissionsSelector--individual': true,
      'CollaboratorModal__PermissionsSelector--open': userExpanded === collaboratorName,
      'CollaboratorModal__PermissionsSelector--disabled': isUser
        || !canManageCollaborators
        || (collaboratorName === owner),
      'CollaboratorModal__PermissionsSelector--collapsed': (userExpanded !== collaboratorName),
    });
    const individualPermissionsMenuCSS = classNames({
      'CollaboratorModal__PermissionsMenu box-shadow': true,
      'CollaboratorModal__PermissionsMenu--individual': true,
      hidden: (userExpanded !== collaboratorName),
    });
    return (
      <li
        key={collaboratorName}
        ref={collaboratorName}
        className={collaboratorItemCSS}
      >
        <div className="CollaboratorsModal__collaboratorName">
          {collaboratorName}
        </div>

        <div className="CollaboratorsModal__permissions CollaboratorsModal__permissions--individual CollaboratorsModal__permissions--small">
          <span
            role="presentation"
            className={individualPermissionsSelectorCSS}
            onClick={() => togglePermissionsMenu(collaboratorName)}
          >
            {getPermissions(collaborator.permission, collaboratorName)}
          </span>
          <ul className={individualPermissionsMenuCSS}>
            <li
              role="presentation"
              onClick={() => addCollaborator('readonly', collaboratorName)}
            >
              <div className="CollaboratorsModal__permissions-header">Read</div>
              <div className="CollaboratorsModal__permissions-subtext">Read-only permissions. Can only pull updates</div>
            </li>
            {
              (sectionType !== 'dataset')
              && (
              <li
                role="presentation"
                onClick={() => addCollaborator('readwrite', collaboratorName)}
              >
                <div className="CollaboratorsModal__permissions-header">Write</div>
                <div className="CollaboratorsModal__permissions-subtext">Read/Write permissions. Can sync to branches other than master</div>
              </li>
              )
            }
            <li
              role="presentation"
              onClick={() => addCollaborator('owner', collaboratorName)}
            >
              <div className="CollaboratorsModal__permissions-header">Admin</div>
              <div className="CollaboratorsModal__permissions-subtext">Admin permissions. Can sync to master and managed collaborators</div>
            </li>
          </ul>
        </div>

        <ButtonLoader
          ref={collaboratorName}
          buttonState={buttonLoaderRemoveCollaborator[collaboratorName]}
          buttonText=""
          className="ButtonLoader__collaborator Btn__delete Btn--round Btn--bordered"
          params={{ collaborator: collaboratorName, button: this }}
          buttonDisabled={disableButtonLoader}
          clicked={removeCollaborator}
        />

      </li>
    );
  }
}

export default CollaboratorsRow;
