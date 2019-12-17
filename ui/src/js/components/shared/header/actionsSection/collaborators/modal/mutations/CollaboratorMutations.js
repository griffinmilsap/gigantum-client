// Mutations
import AddCollaboratorMutation from 'Mutations/AddCollaboratorMutation';
import AddDatasetCollaboratorMutation from 'Mutations/AddDatasetCollaboratorMutation';
import DeleteCollaboratorMutation from 'Mutations/DeleteCollaboratorMutation';
import DeleteDatasetCollaboratorMutation from 'Mutations/DeleteDatasetCollaboratorMutation';


class CollboratorsMutations {
  constructor(props) {
    const {
      name,
      owner,
      sectionType,
    } = props;

    this.state = {
      name,
      owner,
      sectionType,
    };
  }

  /**
  *  @param {Object} data
  *  @param {Function} callback
  *  add collaborator decision to add labbook or dataset
  *  @return {}
  */
  addCollaborator = (data, callback) => {
    const { sectionType } = this.state;
    if (sectionType === 'labbook') {
      this.addLabookCollaborator(data, callback);
    } else {
      this.addDatasetCollaborator(data, callback);
    }
  }

  /**
  *  @param {Object} data
  *  @param {Function} callback
  *  add labbook collaborator
  *  @return {}
  */
  addLabookCollaborator = (data, callback) => {
    const { name, owner } = this.state;
    const {
      collaboratorName,
      newCollaborator,
      permissionOverride,
      newPermissions,
    } = data;

    AddCollaboratorMutation(
      name,
      owner,
      collaboratorName || newCollaborator,
      permissionOverride || newPermissions,
      callback,
    );
  }

  /**
  *  @param {Object} data
  *  @param {Function} callback
  *  add dataset collaborator
  *  @return {}
  */
  addDatasetCollaborator = (data, callback) => {
    const { name, owner } = this.state;
    const {
      collaboratorName,
      newCollaborator,
      permissionOverride,
      newPermissions,
    } = data;

    AddDatasetCollaboratorMutation(
      name,
      owner,
      collaboratorName || newCollaborator,
      permissionOverride || newPermissions,
      callback,
    );
  }

  /**
  *  @param {Object} data
  *  @param {Function} callback
  *  delete collaborator decesion
  *  @return {}
  */
  deleteCollaborator = (data, callback) => {
    const { sectionType } = this.state;
    if (sectionType === 'labbook') {
      this.deleteLabookCollaborator(data, callback);
    } else {
      this.deleteDatasetCollaborator(data, callback);
    }
  }

  /**
  *  @param {Object} data
  *  @param {Function} callback
  *  delete labbook collaborator
  *  @return {}
  */
  deleteLabookCollaborator = (data, callback) => {
    const { name, owner } = this.state;
    const {
      collaborator,
    } = data;

    DeleteCollaboratorMutation(
      name,
      owner,
      collaborator,
      callback,
    );
  }

  /**
  *  @param {Object} data
  *  @param {Function} callback
  *  delete dataset collaborator
  *  @return {}
  */
  deleteDatasetCollaborator = (data, callback) => {
    const { name, owner } = this.state;
    const {
      collaborator,
    } = data;

    DeleteDatasetCollaboratorMutation(
      name,
      owner,
      collaborator,
      callback,
    );
  }
}

export default CollboratorsMutations;
