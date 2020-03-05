// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import uuidv4 from 'uuid/v4';
// queries
import UserIdentity from 'JS/Auth/UserIdentity';
// components
import Tooltip from 'Components/common/Tooltip';
import Modal from 'Components/common/Modal';
// store
import store from 'JS/redux/store';
// mutations
import ImportRemoteDatasetMutation from 'Mutations/repository/import/ImportRemoteDatasetMutation';
import ImportRemoteLabbookMutation from 'Mutations/repository/import/ImportRemoteLabbookMutation';
import BuildImageMutation from 'Mutations/container/BuildImageMutation';
// utilities
import prepareUpload from './PrepareUpload';
// assets
import './ImportModule.scss';

const dropZoneId = uuidv4();


/**
*  @param {String, String, String}
*  trigers §
*  @return {}
*/
const buildImage = (name, owner, id) => {
  BuildImageMutation(owner, name, false, (response, error) => {
    if (error) {
      console.error(error);

      store.dispatch({
        type: 'MULTIPART_INFO_MESSAGE',
        payload: {
          id,
          message: `ERROR: Failed to build ${name}`,
          messsagesList: error,
          error: true,
        },
      });
    }
  });
};


export default class ImportModule extends Component {
  constructor(props) {
    super(props);

    this.state = {
      files: [],
      error: false,
      isImporting: false,
      remoteURL: '',
      showImportModal: false,
      ready: null,
      isOver: false,
    };

    this._getBlob = this._getBlob.bind(this);
    this._dragoverHandler = this._dragoverHandler.bind(this);
    this._dropHandler = this._dropHandler.bind(this);
    this._dragendHandler = this._dragendHandler.bind(this);
    this._fileSelected = this._fileSelected.bind(this);
    this._importingState = this._importingState.bind(this);
    this._clearState = this._clearState.bind(this);
    this._closeLoginPromptModal = this._closeLoginPromptModal.bind(this);
    this._drop = this._drop.bind(this);
    this._dragover = this._dragover.bind(this);
    this._dragleave = this._dragleave.bind(this);
    this._dragenter = this._dragenter.bind(this);
  }

  componentDidMount() {
    const fileInput = document.getElementById('file__input');
    if (fileInput) {
      fileInput.onclick = (evt) => {
        evt.cancelBubble = true;
        evt.stopPropagation(evt);
      };
    }

    this.counter = 0;

    this.setState({
      files: [],
      error: false,
      isImporting: false,
      remoteURL: '',
      showImportModal: false,
      ready: null,
    });

    window.addEventListener('drop', this._drop);
    window.addEventListener('dragover', this._dragover);
    window.addEventListener('dragleave', this._dragleave);
    window.addEventListener('dragenter', this._dragenter);
  }

  componentWillUnmount() {
    window.removeEventListener('drop', this._drop);
    window.removeEventListener('dragover', this._dragover);
    window.removeEventListener('dragleave', this._dragleave);
    window.removeEventListener('dragenter', this._dragenter);
  }

  /**
  *  @param {}
  *  sets state of app for importing
  *  @return {}
  */
  _importingState = () => {
    this.setState({
      isImporting: true,
      showImportModal: false,
    });
    document.getElementById('modal__cover').classList.remove('hidden');
    document.getElementById('loader').classList.remove('hidden');
  }

  /**
  *  @param {String} filename
  *  returns corrected version of filename
  *  @return {}
  */
  _getFilename(filename) {
    const fileArray = filename.split('-');
    fileArray.pop();
    const newFilename = fileArray.join('-');
    return newFilename;
  }


  /**
  *  @param {object} dataTransfer
  *  preventDefault on dragOver event
  */
  _getBlob = (dataTransfer) => {
    const nameArray = dataTransfer.files[0].name.split('-');
    nameArray.pop();
    const name = nameArray.join('-');
    const nameArrayExtension = dataTransfer.files[0].name.split('.');
    const extension = nameArrayExtension[nameArrayExtension.length - 1];
    if ((extension === 'zip') || (extension === 'lbk')) {
      this.setState({
        files: dataTransfer.files,
        ready: {
          owner: localStorage.getItem('username'),
          name,
        },
      });
    }
  }

  /**
  *  @param {Object} event
  *  @param {Boolean} isOver
  *  preventDefault on dragOver event
  */
  _dragoverHandler = (evt, isOver) => { // use evt, event is a reserved word in chrome
    evt.preventDefault(); // this kicks the event up the event loop
    this.setState({ isOver });
  }

  /**
  *  @param {Object} event
  *  handle file drop and get file data
  */
  _dropHandler = (evt) => {
    // use evt, event is a reserved word in chrome
    const dataTransfer = evt.dataTransfer;
    evt.preventDefault();
    evt.dataTransfer.effectAllowed = 'none';
    evt.dataTransfer.dropEffect = 'none';
    this._getBlob(dataTransfer);
    this.setState({ isOver: false })
    return false;
  }

  /**
  *  @param {Object}
  *  handle end of dragover with file
  */
  _dragendHandler = (evt) => { // use evt, event is a reserved word in chrome
    const dataTransfer = evt.dataTransfer;

    evt.preventDefault();
    evt.dataTransfer.effectAllowed = 'none';
    evt.dataTransfer.dropEffect = 'none';

    if (dataTransfer.items) {
      // Use DataTransferItemList interface to remove the drag data
      for (let i = 0; i < dataTransfer.items.length; i++) {
        dataTransfer.items.remove(i);
      }
    } else {
      // Use DataTransfer interface to remove the drag data
      evt.dataTransfer.clearData();
    }
    return false;
  }

  /**
  *  @param {Object}
  *  opens file system for user to select file
  */
  _fileSelected = (evt) => {
    this._getBlob(document.getElementById('file__input'));
  }

  /**
  *  @param {}
  *  clears state of file and sets css back to import
  *  @return {}
  */
  _clearState = () => {
    if (document.getElementById('dropZone__filename')) {
      document.getElementById('dropZone__filename').classList.remove('ImportModule__animation');
    }
    this.setState({ files: [], isImporting: false });
  }

  /**
  *  @param {}
  *  @return {string} returns text to be rendered
  */
  _getImportDescriptionText() {
    return this.state.error
      ? 'File must be .zip'
      : 'Drag & Drop .zip file, or click to select.';
  }

  /**
  *  @param {}
  *  shows create project modal
  *  @return {}
  */
  _showModal(evt) {
    if (navigator.onLine) {
      if (evt.target.id !== 'file__input-label') {
        this.props.showModal();
      }
    } else {
      store.dispatch({
        type: 'ERROR_MESSAGE',
        payload: {
          message: 'Cannot create a Project at this time.',
          messageBody: [
            {
              message: 'An internet connection is required to create a Project.',
            },
          ],
        },
      });
    }
  }

  /**
  *  @param {}
  *  closes import modal
  *  @return {}
  */
  _closeImportModal = () => {
    this.setState({
      files: [],
      error: false,
      isImporting: false,
      remoteURL: '',
      showImportModal: false,
      ready: null,
    });
  }


  /**
  *  @param {Object} evt
  *  updated url in state
  *  @return {}
  */
  _updateRemoteUrl(evt) {
    const newValue = evt.target.value;
    const name = newValue.split('/')[newValue.split('/').length - 1];
    const owner = newValue.split('/')[newValue.split('/').length - 2];
    if (name && owner) {
      this.setState({
        ready: {
          name,
          owner,
          method: 'remote',
        },
      });
    }
    this.setState({ remoteURL: evt.target.value });
  }

  /**
  *  imports labbook from remote url, builds the image, and redirects to imported labbook
  *  @return {}
  */
  _import = () => {
    const { props, state } = this;
    const id = uuidv4();

    if (state.files[0] !== undefined) {
      const self = this;


      UserIdentity.getUserIdentity().then((response) => {
        if (navigator.onLine) {
          if (response.data) {
            if (response.data.userIdentity.isSessionValid) {
              self._importingState();

              store.dispatch({
                type: 'MULTIPART_INFO_MESSAGE',
                payload: {
                  id,
                  message: 'Importing Project please wait',
                  isLast: false,
                  error: false,
                },
              });
              this.setState({ ready: null });
              if (props.section === 'labbook') {
                prepareUpload(state.files[0], 'ImportLabbookMutation', buildImage, state, props.history);
              } else {
                prepareUpload(state.files[0], 'ImportDatasetMutation', false, state, props.history);
              }

              document.getElementById('modal__cover').classList.remove('hidden');
              document.getElementById('loader').classList.remove('hidden');
              this.setState({ showImportModal: false });
              this._clearState();
            } else {

              props.auth.renewToken(true, () => {
                this.setState({ showLoginPrompt: true });
              }, () => {
                this._import();
              });
            }
          }
        } else {
          this.setState({ showLoginPrompt: true });
        }
      });
    } else if (state.remoteURL) {
      const modifiedURL = (state.remoteURL.indexOf('http') > -1)
        ? state.remoteURL
        : `https://${state.remoteURL}`;
      const domain = new URL(modifiedURL);
      const hostname = domain.hostname.replace('.com', '.io');
      const name = state.remoteURL.split('/')[state.remoteURL.split('/').length - 1];
      const owner = state.remoteURL.split('/')[state.remoteURL.split('/').length - 2];
      const remote = `https://repo.${hostname}/${owner}/${name}.git`;

      if (props.section === 'labbook') {
        this._importRemoteProject(owner, name, remote, id);
      } else {
        this._importRemoteDataset(owner, name, remote, id);
      }
    }
  }

  /**
  *  @param {object}
  *  detects when a file has been dropped
  */
  _drop(evt) {
    if (document.getElementById('dropZone')) {
      document.getElementById('dropZone').classList.remove('ImportModule__drop-area-highlight');
    }

    if (evt.target.classList.contains(dropZoneId)) {
      evt.preventDefault();
      evt.dataTransfer.effectAllowed = 'none';
      evt.dataTransfer.dropEffect = 'none';
    }
  }

  /**
  *  @param {object}
  *  detects when file has been dragged over the DOM
  */
  _dragover(evt) {
    if (document.getElementById('dropZone')) {

      document.getElementById('dropZone').classList.add('ImportModule__drop-area-highlight');
    }

    if (evt.target.classList.contains(dropZoneId) < 0) {
      evt.preventDefault();
      evt.dataTransfer.effectAllowed = 'none';
      evt.dataTransfer.dropEffect = 'none';
    }
  }

  /**
  *  @param {object}
  *  detects when file leaves dropzone
  */
  _dragleave(evt) {
    this.counter -= 1;

    if (evt.target.classList && evt.target.classList.contains(dropZoneId) < 0) {
      if (document.getElementById('dropZone')) {
        if (this.counter === 0) {

          document.getElementById('dropZone').classList.remove('ImportModule__drop-area-highlight');
        }
      }
    }
  }

  /**
  *  @param {object}
  *  detects when file enters dropzone
  */
  _dragenter(evt) {
    this.counter += 1;

    if (document.getElementById('dropZone')) {

      document.getElementById('dropZone').classList.add('ImportModule__drop-area-highlight');
    }

    if (evt.target.classList && evt.target.classList.contains(dropZoneId) < 0) {
      evt.preventDefault();
      evt.dataTransfer.effectAllowed = 'none';
      evt.dataTransfer.dropEffect = 'none';
    }
  }

  /**
  *  @param {}
  *  @return {} hides login prompt modal
  */
  _closeLoginPromptModal() {
    this.setState({ showLoginPrompt: false });
  }

  /**
  *  @param {String, String, String, String}
  *  trigers ImportRemoteLabbookMutation
  *  @return {}
  */
  _importRemoteProject(owner, name, remote, id) {
    const self = this;
    self._importingState();
    const sucessCall = () => {
      this._clearState();
      store.dispatch({
        type: 'MULTIPART_INFO_MESSAGE',
        payload: {
          id,
          message: `Successfully imported remote Project ${name}`,
          isLast: true,
          error: false,
        },
      });

      buildImage(name, owner, id);

      self.props.history.replace(`/projects/${owner}/${name}`);
    };

    const failureCall = (error) => {
      this._clearState();
      store.dispatch({
        type: 'MULTIPART_INFO_MESSAGE',
        payload: {
          id,
          message: 'ERROR: Could not import remote Project',
          messageBody: error,
          error: true,
        },
      });

      document.getElementById('loader').classList.add('hidden');
      document.getElementById('modal__cover').classList.add('hidden');
    };
    ImportRemoteLabbookMutation(
      owner,
      name,
      remote,
      sucessCall,
      failureCall,
      (response, error) => {
        if (error) {
          failureCall(error);
        }
      },
    );
  }


  /**
  *  @param {String, String, String, String}
  *  trigers ImportRemoteDatasetMutation
  *  @return {}
  */
  _importRemoteDataset(owner, name, remote, id) {
    const self = this;
    self._importingState();
    ImportRemoteDatasetMutation(owner, name, remote, (response, error) => {
      this._clearState();
      document.getElementById('modal__cover').classList.add('hidden');
      document.getElementById('loader').classList.add('hidden');
      if (error) {
        console.error(error);
        store.dispatch({
          type: 'MULTIPART_INFO_MESSAGE',
          payload: {
            id,
            message: 'ERROR: Could not import remote Dataset',
            messageBody: error,
            error: true,
          },
        });
      } else if (response) {
        this._clearState();
        store.dispatch({
          type: 'MULTIPART_INFO_MESSAGE',
          payload: {
            id,
            message: `Successfully imported remote Dataset ${name}`,
            isLast: true,
            error: false,
          },
        });
        self.props.history.replace(`/datasets/${response.importRemoteDataset.newDatasetEdge.node.owner}/${name}`);
      }
    });
  }

  render() {
    const { props, state } = this;
    const loadingMaskCSS = classNames({
      'ImportModule__loading-mask': state.isImporting,
      hidden: !state.isImporting,
    });

    return (
      <div
        className="ImportModule Card Card--line-50 Card--text-center Card--add Card--import column-4-span-3"
        key="AddLabbookCollaboratorPayload"
      >

        <ImportModal self={this} />

        <div className="Import__header">
          <div className={`Import__icon Import__icon--${props.section}`}>
            <div className="Import__add-icon" />
          </div>
          <div className="Import__title">
            <h2 className="Import__h2 Import__h2--azure">{props.title}</h2>
          </div>
        </div>

        <button
          type="button"
          className="btn--import"
          onClick={(evt) => { this._showModal(evt); }}
        >
          Create New
        </button>

        <button
          type="button"
          className="btn--import"
          onClick={(evt) => { this.setState({ showImportModal: true }); }}
        >
          Import Existing
        </button>

        <Tooltip section="createLabbook" />
        <Tooltip section="importLabbook" />
        <div className={loadingMaskCSS} />
      </div>
    );
  }
}

const ImportModal = ({ self }) => {
  const { props, state } = self;
  const owner = state.ready ? state.ready.owner : '';
  const name = state.ready ? state.ready.name : '';
  const section = props.section === 'labbook' ? 'Project' : 'Dataset';
  const dropBoxCSS = classNames({
    'Dropbox ImportDropzone flex flex--column align-items--center': true,
    'Dropbox--hovered': state.isOver,
    'Dropbox--dropped': state.ready && state.files[0],
  });
  return (
    <div className="Import__main">
      {
      state.showImportModal
      && (
      <Modal
        header={`Import ${section}`}
        handleClose={() => self._closeImportModal()}
        size="large"
        icon="add"
        renderContent={() => (
          <div className="ImportModal">
            <p>{`Import a ${section} by either pasting a URL or drag & dropping below`}</p>
            <input
              className="Import__input"
              type="text"
              placeholder={`Paste ${section} URL`}
              onChange={evt => self._updateRemoteUrl(evt)}
              defaultValue={state.remoteUrl}
            />

            <div
              id="dropZone"
              className={dropBoxCSS}
              ref={div => self.dropZone = div}
              type="file"
              onDragEnd={evt => self._dragendHandler(evt, false)}
              onDrop={evt => self._dropHandler(evt)}
              onDragOver={evt => self._dragoverHandler(evt, true)}
            >
              {
                 (state.ready && state.files[0])
                   ? (
                     <div className="Import__ready">
                       <div>{`Select Import to import the following ${section}`}</div>
                       <hr />
                       <div>{`${section} Owner: ${owner}`}</div>
                       <div>{`${section} Name: ${name}`}</div>
                     </div>
                   ) : (
                     <div className="DropZone">
                       <p>{`Drag and drop an exported ${section} here`}</p>
                     </div>
                   )}
            </div>

            <div className="Import__buttonContainer">
              <button
                type="button"
                onClick={() => self._closeImportModal()}
                className="Btn--flat"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => { self._import(); }}
                className="Btn--last"
                disabled={!self.state.ready || self.state.isImporting}
              >
                Import
              </button>
            </div>
          </div>
        )
        }
      />
      )
    }
    </div>
  );
};
