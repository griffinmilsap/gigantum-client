// @flow
// vendor
import React, { PureComponent } from 'react';

type Props = {
  collaborators: Array<Object>
}

class NoCollaborators extends PureComponent<Props> {
  render() {
    const { collaborators } = this.props;
    if (collaborators && collaborators.length) {
      return (
        <div className="CollaboratorsModal__message">
          To add and edit collaborators,
          <b>{' Administrator '}</b>
          access is required. Contact the Project
          <b>{' Owner '}</b>
          or a Project
          <b>{' Administrator '}</b>
          to manage collaborator settings.
        </div>
      );
    }
    return (
      <div className="CollaboratorsModal__message">
        <b>
          This project needs to be published before collaborators can be added.
        </b>
      </div>
    );
  }
}

export default NoCollaborators;
