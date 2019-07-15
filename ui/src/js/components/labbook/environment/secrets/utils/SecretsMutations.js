// mutations
import DeleteSecretsFileMutation from 'Mutations/environment/DeleteSecretsFileMutation';
import RemoveSecretsEntryMutation from 'Mutations/environment/RemoveSecretsEntryMutation';
import InsertSecretsEntryMutation from 'Mutations/environment/InsertSecretsEntryMutation';
// utils
import prepareUpload from './PrepareUpload'

class PackageMutations {
  /**
    * @param {Object} props
    *        {string} props.owner
    *        {string} props.name
    *        {string} props.connection
    *        {string} props.parentId
    * pass above props to state
    */
  constructor(props) {
    this.state = props;
  }

  /**
   *  @param {Object} data
   *         {string} data.filename
   *         {string} data.mountPath
   *  @param {function} callback
   *  calls insert secret mutation
   */
  insertSecret(data, callback) {
    const {
      filename,
      mountPath,
    } = data;

    const {
      owner,
      name,
      environmentId,
    } = this.state;

    InsertSecretsEntryMutation(
      owner,
      name,
      environmentId,
      filename,
      mountPath,
      callback,
    );
  }

  /**
   *  @param {Object} data
   *         {string} data.file
   *  @param {function} callback
   *  calls upload secret mutation
   */
  uploadSecret(data) {
    const {
      file,
      filename,
      id,
      component,
    } = data;

    const {
      owner,
      name,
      environmentId,
    } = this.state;

    const mutationData = {
      file,
      typeOfUpload: 'Secrets_secretsFileMapping',
      owner,
      name,
      environmentId,
      id,
      filename,
    };

    prepareUpload(mutationData, component);
  }

  /**
   *  @param {Object} data
   *         {string} data.filename
   *         {string} data.mountPath
   *  @param {function} callback
   *  calls insert secret mutation
   */
  removeSecret(data, callback) {
    const {
      filename,
      id,
    } = data;

    const {
      owner,
      name,
      environmentId,
    } = this.state;

    RemoveSecretsEntryMutation(
      owner,
      name,
      environmentId,
      id,
      filename,
      callback,
    );
  }

  /**
   *  @param {Object} data
   *         {string} data.filename
   *         {string} data.mountPath
   *  @param {function} callback
   *  calls insert secret mutation
   */
  deleteSecret(data, callback) {
    const {
      filename,
      id,
    } = data;

    const {
      owner,
      name,
      environmentId,
    } = this.state;

    DeleteSecretsFileMutation(
      owner,
      name,
      environmentId,
      id,
      filename,
      callback,
    );
  }
}

export default PackageMutations;
