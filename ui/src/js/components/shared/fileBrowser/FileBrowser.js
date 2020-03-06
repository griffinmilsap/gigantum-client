// vendor
import React, { Component } from 'react';
import store from 'JS/redux/store';
import { DropTarget } from 'react-dnd';
import { NativeTypes } from 'react-dnd-html5-backend';
import classNames from 'classnames';
import isEqual from 'react-fast-compare';
// store
import {
  setFileBrowserLock,
} from 'JS/redux/actions/labbook/labbook';
import {
  setUploadMessageRemove,
} from 'JS/redux/actions/footer';
// assets
import './FileBrowser.scss';
// components
import LinkModal from './LinkModal';
import AddSubfolder from './fileRow/AddSubfolder';
import FileSizePromptModal from './FileSizePromptModal';
import FileBrowserToolbar from './FileBrowserToolbar';
import FileBrowserTools from './FileBrowserTools';
import File from './fileRow/File';
import Folder from './fileRow/Folder';
import Datasets from './fileRow/dataset/Datasets';
// util
import prepareUpload from './utilities/PrepareUpload';
import FileBrowserMutations from './utilities/FileBrowserMutations';
import Connectors from './utilities/Connectors';
import FileFormatter, { fileHandler } from './utilities/FileFormatter';


/**
  *  @param {Object} uploadData
  *  checks to see length of upload file
  *  @return {Object}
  */
const getQueuedFiles = (uploadData) => {
  const fileTooLarge = uploadData
    && uploadData.fileSizeData
    && uploadData.fileSizeData.fileSizeNotAllowed
    && uploadData.fileSizeData.fileSizeNotAllowed.length;
  const filePrompted = uploadData
    && uploadData.fileSizeData
    && uploadData.fileSizeData.fileSizePrompt
    && uploadData.fileSizeData.fileSizePrompt.length;

  return {
    fileTooLarge,
    filePrompted,
  };
};

/**
  *  @param {Array} files
  *  checks if all files are local
  *  @return {Boolean}
  */
const checkLocalAll = (files) => {
  let isLocal = true;
  Object.keys(files).forEach((fileKey) => {
    if (files[fileKey].children) {
      const isChildrenLocal = checkLocalAll(files[fileKey].children);
      if (isChildrenLocal === false) {
        isLocal = false;
      }
    } else if (!files[fileKey].edge.node.isLocal) {
      isLocal = false;
    }
  });
  return isLocal;
};

/**
  *  @param {Array} files
  *  checks if a file object is local and it's children
  *  @return {Boolean}
  */
const checkLocalIndividual = (files) => {
  if (files) {
    let isLocal = true;
    const searchChildren = (parent) => {
      if (parent.children) {
        Object.keys(parent.children).forEach((childKey) => {
          if (parent.children[childKey].edge) {
            if (parent.children[childKey].edge.node.isLocal === false) {
              isLocal = false;
            }
            searchChildren(parent.children[childKey]);
          }
        });
      }
    };

    if (files.children) {
      searchChildren(files);
    } else {
      isLocal = files.edge.node.isLocal;
    }

    return isLocal;
  }
  return true;
};

/**
  *  @param {Object} props
  *  @param {Object} state
  *  gets a download list of files from linked dataset
  *  @return {Array}
  */
const getDownloadList = (props, state) => {
  const downloadList = [];
  if (props.section === 'data') {
    Object.keys(state.childrenState).forEach((key) => {
      if (state.childrenState[key].isSelected && !state.childrenState[key].edge.node.isLocal) {
        downloadList.push(state.childrenState[key].edge.node.key);
      }
    });
  }

  return downloadList;
};

class FileBrowser extends Component {
  constructor(props) {
    super(props);
    this.state = {
      mutations: new FileBrowserMutations(this._getMutationData()),
      mutationData: this._getMutationData(),
      hoverId: '',
      childrenState: {},
      multiSelect: 'none',
      search: '',
      isOverChildFile: false,
      sort: 'az',
      reverse: false,
      count: 0,
      files: {},
      aboveSize: window.innerWidth > 1240,
      popupVisible: false,
      fileSizePromptVisible: false,
      showLinkModal: false,
      downloadingAll: false,
      isRefetching: false,
      downloadingEdges: null,
    };
  }

  static getDerivedStateFromProps(props, state) {
    const previousCount = state.count;
    const count = props.files.edges.length;
    const childrenState = state.isFetching ? state.childrenState : {};
    const selectedFiles = [];
    let selectedCount = 0;
    let selectedFileCount = 0;
    let selectedFolderCount = 0;

    const files = props.files.edges;

    const processChildState = (edges, datasetName) => {
      if (datasetName && edges.length === 0) {
        const adjustedKey = `${datasetName}/`;
        childrenState[adjustedKey] = {
          isSelected: (state.childrenState && state.childrenState[adjustedKey])
            ? state.childrenState[adjustedKey].isSelected : false,
          isIncomplete: (state.childrenState && state.childrenState[adjustedKey])
            ? state.childrenState[adjustedKey].isIncomplete : false,
          isExpanded: (state.childrenState && state.childrenState[adjustedKey])
            ? state.childrenState[adjustedKey].isExpanded : false,
          isAddingFolder: (state.childrenState && state.childrenState[adjustedKey])
            ? state.childrenState[adjustedKey].isAddingFolder : false,
        };
      }
      edges.forEach((edge) => {
        if (edge.node && edge.node.key) {
          const key = datasetName ? `${datasetName}/${edge.node.key}` : edge.node.key;
          const splitKey = key.split('/').filter(n => n);
          splitKey.forEach((key, index) => {
            if (index !== splitKey.length) {
              const tempKey = `${splitKey.slice(0, index).join('/')}/`;

              if (!childrenState[tempKey] && tempKey !== '/') {
                childrenState[tempKey] = {
                  isSelected: (state.childrenState && state.childrenState[tempKey])
                    ? state.childrenState[tempKey].isSelected : false,
                  isIncomplete: (state.childrenState && state.childrenState[tempKey])
                    ? state.childrenState[tempKey].isIncomplete : false,
                  isExpanded: (state.childrenState && state.childrenState[tempKey])
                    ? state.childrenState[tempKey].isExpanded : false,
                  isAddingFolder: (state.childrenState && state.childrenState[tempKey])
                    ? state.childrenState[tempKey].isAddingFolder : false,
                  edge: {
                    node: {
                      isDir: true,
                      key: tempKey,
                      modifiedAt: Math.floor(Date.now() / 1000),
                      id: tempKey,
                    },
                  },
                };
              }
            }
          });
          childrenState[key] = {
            isSelected: (state.childrenState && state.childrenState[key])
              ? state.childrenState[key].isSelected : false,
            isIncomplete: (state.childrenState && state.childrenState[key])
              ? state.childrenState[key].isIncomplete : false,
            isExpanded: (state.childrenState && state.childrenState[key])
              ? state.childrenState[key].isExpanded : false,
            isAddingFolder: (state.childrenState && state.childrenState[key])
              ? state.childrenState[key].isAddingFolder : false,
            edge,
          };
        }
      });
    };
    processChildState(files);

    Object.keys(childrenState).forEach((key) => {
      if (childrenState[key].isSelected) {
        selectedFiles.push(key);
      }
      let isCurrentSelected = false;
      selectedFiles.forEach((selectedFileKey) => {
        if (key.startsWith(selectedFileKey) && !(childrenState[selectedFileKey].isExpanded)) {
          isCurrentSelected = true;
        } else {
          isCurrentSelected = childrenState[key].isSelected;
        }
      });
      if (isCurrentSelected) {
        selectedCount += 1;
        if (childrenState[key].edge.node.isDir) {
          selectedFolderCount += 1;
        } else {
          selectedFileCount += 1;
        }
      }
    });

    let multiSelect = (selectedCount >= count) ? 'all' : 'partial';
    multiSelect = selectedCount === 0 ? 'none' : multiSelect;

    return {
      ...state,
      childrenState,
      isRefetching: false,
      selectedCount,
      selectedFileCount,
      selectedFolderCount,
      search: count === previousCount ? state.search : '',
      count,
      multiSelect,
    };
  }

  /**
   sets worker
  */
  componentDidMount() {
    const { props } = this;
    const files = props.files.edges;
    const { linkedDatasets } = props;
    this.fileHandler = new FileFormatter(fileHandler);
    this.fileHandler.postMessage({
      files,
      linkedDatasets,
      search: this.state.search,
    });

    this.fileHandler.addEventListener('message', this._fileHandlerMessage);
  }

  shouldComponentUpdate(nextProps, nextState) {
    return !isEqual(this.props, nextProps) || !isEqual(this.state, nextState);
  }

  /*
      resets search
    */
  componentDidUpdate() {
    if (this.list) {
      this.list.recomputeGridSize();
    }
    // TODO should not be using document to clear value
    const element = document.getElementsByClassName('FileBrowser__input')[0];
    if (this.state.search === '' && element && element.value !== '') {
      element.value = '';
    }
    const files = this.props.files.edges;
    const { linkedDatasets } = this.props;

    this.fileHandler.postMessage({
      files,
      linkedDatasets,
      search: this.state.search,
    });
  }

  componentWillUnmount() {
    this.fileHandler.removeEventListener('message', this._fileHandlerMessage);
    this.fileHandler.terminate();
    delete this.fildHandler;
  }

  /**
    *  @param {Object} evt
    *  sets state of fileHash and files when computed by
    *  the worker
    *  @return {}
    */
  _fileHandlerMessage = (evt) => {
    const { state } = this;
    if (state.fileHash !== evt.data.hash) {
      this.setState({ fileHash: evt.data.hash, files: evt.data.files });
    }
  }

  /**
    *  @param {} -
    *  refetches relay connection
    *  @return {}
    */
  _refetch = () => {
    const { relay, loadMore } = this.props;
    this.setState({ isRefetching: true });

    relay.refetchConnection(
      100,
      (response, error) => {
        if (error) {
          console.log(error);
        }
        loadMore();
      },
    );
  }

  /**
    *  @param {Boolean} allFilesLocal
    *  handles downloading all files in data-filebrowser
    *  @return {}
    */
  _handleDownloadAll = (allFilesLocal) => {
    const { state } = this;
    const { downloadDatasetFiles } = state.mutations;

    if (!state.downloadingAll && !allFilesLocal) {
      const { owner, name } = this.props;
      const data = {
        datasetOwner: owner,
        datasetName: name,
        allKeys: true,
      };
      data.successCall = () => {
        this.setState({ downloadingAll: false });
      };
      data.failureCall = () => {
        this.setState({ downloadingAll: false });
      };

      const callback = (response, error) => {
        if (error) {
          this.setState({ downloadingAll: false });
        }
      };
      this.setState({ downloadingAll: true });

      downloadDatasetFiles(data, callback);
    }
  }

  /**
    *  @param {string} key - key of file to be updated
    *  @param {boolean} isSelected - update if the value is selected
    *  @param {boolean} isIncomplete - update if the value is incomplete
    *  @param {boolean} isExpanded - update if the value is incomplete
    *  @param {boolean} isAddingFolder - update if the value is incomplete
    *  @return {}
    */
  _updateChildState = (
    key,
    isSelected,
    isIncomplete,
    isExpanded,
    isAddingFolder,
  ) => {
    const { state, props } = this;
    const { childrenState } = state;
    const childrenStateKeys = Object.keys(childrenState);
    let multiCount = 0;
    let multiSelect;


    childrenState[key].isSelected = isSelected;
    childrenState[key].isIncomplete = isIncomplete;
    childrenState[key].isExpanded = isExpanded;
    childrenState[key].isAddingFolder = isAddingFolder;

    childrenStateKeys.forEach((childKey) => {
      if (childrenState[childKey].isSelected) {
        multiCount += 1;
      }
    });

    multiSelect = (multiCount >= props.files.edges.length) ? 'all' : 'partial';
    multiSelect = (multiCount === 0) ? 'none' : multiSelect;

    this.setState({ childrenState, multiSelect });
  }

  /**
    *  @param {string} stateKey
    *  @param {string || boolean || number} value
    *  update state of component for a given key value pair
    *  @return {}
    */
  _setState = (key, value) => {
    this.setState({ [key]: value });
  }

  /**
  *  @param {}
  *  sorts files into an object for rendering
  *  @return {object}
  */
  _getMutationData = () => {
    const {
      parentId,
      connection,
      section,
      owner,
      name,
    } = this.props;

    return {
      owner,
      name,
      parentId,
      connection,
      section,
    };
  }

  /**
  *  @param {boolean} popupVisible
  *  triggers favoirte unfavorite mutation
  *  @return {}
  */
  _togglePopup = (popupVisible) => {
    this.setState({ popupVisible });
  }

  /**
  *  @param {}
  *  loops through selcted files and deletes them
  *  @return {}
  */
  _deleteSelectedFiles = () => {
    const { state } = this;
    const filePaths = [];
    const dirList = [];
    const comparePaths = [];
    const edges = [];
    const deletedKeys = [];

    Object.keys(state.childrenState).forEach((key) => {

      if (state.childrenState[key].isSelected) {
        const { edge } = state.childrenState[key];
        delete this.state.childrenState[key];
        if (edge.node.isDir) {
          deletedKeys.push(key);
        }
        comparePaths.push(edge.node.key);
        filePaths.push(edge.node.key);
        edges.push(edge);
        if (edge.node.isDir) {
          dirList.push(edge.node.key);
        }
      }
    });

    Object.keys(state.childrenState).forEach((key) => {
      deletedKeys.forEach((deletedKey) => {
        if (key.startsWith(deletedKey) && this.state.childrenState[key]) {
          const { edge } = this.state.childrenState[key];

          delete this.state.childrenState[key];
          comparePaths.push(edge.node.key);
          filePaths.push(edge.node.key);
          edges.push(edge);
          if (edge.node.isDir) {
            dirList.push(edge.node.key);
          }
        }
      });
    });

    const filteredPaths = filePaths.filter((key) => {
      const hasDir = dirList.some(dir => ((key.indexOf(dir) > -1) && (dir !== key)));
      return !hasDir;
    });
    this._togglePopup(false);
    this._deleteMutation(filteredPaths, edges);
  }

  /**
  *  @param {Array} downloadList
  *  loops through selcted files and downloads them
  *  @return {}
  */
  _downloadSelectedFiles = (downloadList) => {
    const { state, props } = this;
    const { downloadDatasetFiles } = state.mutations;
    const { owner, name } = props;
    const data = {
      owner,
      datasetName: name,
      keys: downloadList,
    };

    data.successCall = () => {
      this.setState({ downloadingEdges: null });
    };
    data.failureCall = () => {
      this.setState({ downloadingEdges: null });
    };

    const callback = (response, error) => {
      if (error) {
        this.setState({ downloadingEdges: null });
      }
    };

    this.setState({ downloadingEdges: new Set(downloadList) });
    downloadDatasetFiles(data, callback);
  }

  /**
  *  @param {}
  *  selects all or unselects files
  *  @return {}
  */
  _selectFiles = () => {
    const { state } = this;
    const { childrenState } = state;
    const count = Object.keys(state.childrenState).length;
    const childrenStateKeys = Object.keys(state.childrenState);

    let multiSelect = (count === state.selectedCount) ? 'none' : 'all';
    let isSelectedCount = 0;

    childrenStateKeys.forEach((key) => {
      if (childrenState[key]) {
        const isSelected = (childrenState[key].edge.node.key !== 'untracked/') && (multiSelect === 'all');
        childrenState[key].isSelected = isSelected;
        if (isSelected) {
          childrenState[key].isIncomplete = false;
          isSelectedCount += 1;
        }
      }
    });

    multiSelect = (isSelectedCount > 0) ? multiSelect : 'none';

    this.setState({ multiSelect, childrenState });
  }

  /**
  *  @param {Array:[string]} filePaths
  *  @param {Array:[Object]} edges
  *  triggers delete muatation
  *  @return {}
  */
  _deleteMutation = (filePaths, edges) => {
    const { state } = this;
    const data = {
      filePaths,
      edges,
    };
    this.setState({ multiSelect: 'none' });
    state.mutations.deleteLabbookFiles(data, () => {});
  }

  /**
  *  @param {Boolean} showLinkModal
  *  toggles showLinkModal in state
  *  @return {}
  */
  _showLinkModal = (showLinkModal) => {
    this.setState({ showLinkModal });
  }

  /**
  *  @param {string} key
  *  @param {boolean} value
  *  updates boolean state of a given key
  *  @return {}
  */
  _updateStateBoolean = (key, value) => {
    this.setState({ [key]: value });
  }

  /**
  *  @param {}
  *  checks if folder refs has props.isOver === true
  *  @return {boolean} isSelected - returns true if a child has been selected
  */
  _checkChildState = () => {
    const { state } = this;
    const childrenStateKeys = Object.keys(state.childrenState);
    let isSelected = false;

    childrenStateKeys.forEach((key) => {
      if (state.childrenState[key].isSelected) {
        isSelected = true;
      }
    });

    return { isSelected };
  }

  /**
  *  @param {evt}
  *  update state
  *  @return {}
  */
  _updateSearchState = (evt) => {
    this.setState({ search: evt.target.value });
  }

  /**
  *  @param {boolean} isOverChildFile
  *  update state to update drop zone
  *  @return {}
  */
  _updateDropZone = (isOverChildFile) => {
    this.setState({ isOverChildFile });
  }

  /**
  *  @param {Array:[Object]} array
  *  @param {string} type
  *  @param {boolean} reverse
  *  @param {Object} children
  *  @param {string} section
  *  returns sorted children
  *  @return {}
  */
  _childSort = (array, type, reverse, children, section) => {
    const { props } = this;
    array.sort((a, b) => {
      const isAUntracked = (a === 'untracked')
        && (section === 'folder')
        && (props.section !== 'data');
      const isBUntracked = (b === 'untracked')
        && (section === 'folder')
        && (props.section !== 'data');
      let lowerA;
      let lowerB;

      if ((type === 'az') || ((type === 'size') && (section === 'folder'))) {
        lowerA = a.toLowerCase();
        lowerB = b.toLowerCase();
        if (type === 'size' || !reverse) {
          return isAUntracked ? -1 : isBUntracked ? 1 : (lowerA < lowerB) ? -1 : (lowerA > lowerB) ? 1 : 0;
        }
        return isAUntracked ? -1 : isBUntracked ? 1 : (lowerA < lowerB) ? 1 : (lowerA > lowerB) ? -1 : 0;
      } if (type === 'modified') {
        lowerA = children[a].edge.node.modifiedAt;
        lowerB = children[b].edge.node.modifiedAt;
        return isAUntracked ? -1 : isBUntracked ? 1 : reverse ? lowerB - lowerA : lowerA - lowerB;
      } if (type === 'size') {
        lowerA = children[a].edge.node.size;
        lowerB = children[b].edge.node.size;
        return isAUntracked ? -1 : isBUntracked ? 1 : reverse ? lowerB - lowerA : lowerA - lowerB;
      }
      return 0;
    });
    return array;
  }

  /**
  *  @param {String} Type
  *  handles state changes for type
  *  @return {}
  */
  _handleSort = (type) => {
    const { state } = this;
    if (type === state.sort) {
      this.setState({ reverse: !state.reverse });
    } else {
      this.setState({ sort: type, reverse: false });
    }
  }

  /**
  *  @param {}
  *  show modal to prompt user to continue upload or not
  *  @return {}
  */
  _promptUserToAcceptUpload = () => {
    this.setState({ fileSizePromptVisible: true });
  }

  /**
  *  set computed connector data into state to be triggered after user makes its decision
  *  show modal to prompt user to continue upload or not
  *  @param {object} dndItem - prop passed from react dnd that contains files and dirContent
  *  @param {object} props - props from the component triggering the upload process
  *  @param {object} mutationData - mutation data from the component
  *                                 triggering the upload process
  *  @param {object} uploadCallback - function in Connectors.js that will kick
  *                                   off the upload process once the users
  *                                   decision has been made
  *  @param {object} fileSizeData - object with 2 arrays, fileSizeNotAllowed files
  *                                 that are too big for the code section,
  *                                 fileSizePrompt files that are between
  *                                 10MB and 100MB and require the user to confirm
  *  @return {}
  */
  _fileSizePrompt = (fileSizeData, uploadCallback) => {
    this.setState({
      uploadData: {
        uploadCallback,
        fileSizeData,
      },
    });

    this._promptUserToAcceptUpload();
  }

  /**
  *  @param {} -
  *  creates a file using AddLabbookFileMutation by passing a blob
  *  set state of user prompt modal
  */
  _userAcceptsUpload = () => {
    const {
      fileSizeData,
      uploadCallback,
    } = this.state.uploadData;
    const files = fileSizeData.filesAllowed.concat(fileSizeData.fileSizePrompt);

    fileSizeData.filesAllowed = files;
    fileSizeData.fileSizePrompt = [];

    uploadCallback(fileSizeData);

    this.setState({ fileSizePromptVisible: false });
  }

  /**
  *  @param {} -
  *  creates a file using AddLabbookFileMutation by passing a blob
  *  set state of user prompt modal
  */
  _userRejectsUpload = () => {
    const {
      fileSizeData,
      uploadCallback,
    } = this.state.uploadData;
    const fileSizeNotAllowed = fileSizeData.fileSizeNotAllowed.concat(fileSizeData.fileSizePrompt);

    fileSizeData.fileSizePrompt = [];
    fileSizeData.fileSizeNotAllowed = fileSizeNotAllowed;

    uploadCallback(fileSizeData);

    this.setState({ fileSizePromptVisible: false });
  }

  /**
  *  @param {} -
  *  user cancels upload
  */
  _cancelUpload = () => {
    const { owner, name } = this.props;
    this.setState({ fileSizePromptVisible: false });
    setUploadMessageRemove('', null, 0);
    setFileBrowserLock(owner, name, false);
  }

  /**
  *  @param {} -
  *  gets file prompt text individual sections
  *  @return {string}
  */
  _getFilePromptText = () => {
    const { section } = this.props;
    const size = (section === 'code') ? '100MB' : '500MB';
    return `Click 'Continue' to upload all files under the ${size} limit. \nFiles over the limit will be ignored.`
  }

  /**
  *  @param {Array} files
  *  sends file selection upload to be prepared for upload
  *  @return {string}
  */
  _uploadFiles = (files) => {
    const { props, state } = this;
    prepareUpload(
      files,
      props,
      false,
      state.mutationData,
      this, // component
    );
  }

  /**
  *  @param {} -
  *  fires updateUnmanagedDataset mutation
  *  @return {}
  */
  _updateUnmanagedDatasetMutation = () => {
    const { state } = this;
    const { updateUnmanagedDataset } = state.mutations;

    updateUnmanagedDataset(
      {
        fromRemote: true,
        fromLocal: false,
      },
      () => {
        this.setState({ confirmUpdateVisible: false });
      },
    );
  }

  /**
  *  @param {Array} files
  *  @param {String} type
  *  fires updateUnmanagedDataset mutation
  *  @return {}
  */
  _getKeys = (files, type) => {
    const { state } = this;
    const isDir = (type === 'folder');
    let keys = [];

    if (files) {
      keys = Object.keys(files).filter((child) => {
        const hasEdge = files[child].edge;
        return (hasEdge && (files[child].edge.node.isDir === isDir));
      });
    }

    return this._childSort(keys, state.sort, state.reverse, files, type);
  }

  /**
  *  @param {Array} files
  *  @param {String} type
  *  fires updateUnmanagedDataset mutation
  *  @return {}
  */
  _updateVisibleFolder = () => {
    this.setState((state) => {
      const addFolderVisible = !state.addFolderVisible;
      return {
        ...state,
        addFolderVisible,
      };
    });
  }


  /**
  *  @param {Array} files
  *  @param {String} type
  *  fires updateUnmanagedDataset mutation
  *  @return {}
  */
  _updateConfirmVisible = (value) => {
    this.setState((state) => {
      const confirmUpdateVisible = (value !== undefined)
        ? value
        : !state.confirmUpdateVisible;
      return {
        ...state,
        confirmUpdateVisible,
      };
    });
  }

  render() {
    const { props, state } = this;
    const { files, mutationData, uploadData } = this.state;
    const {
      isOver,
      canDrop,
      name,
      owner,
      section,
    } = this.props;
    const { isSelected } = this._checkChildState();
    const allFilesLocal = checkLocalAll(files);
    const uploadPromptText = this._getFilePromptText();
    // TODO move this to a function
    const folderKeys = this._getKeys(files, 'folder');
    const fileKeys = this._getKeys(files, 'files');
    const childrenKeys = folderKeys.concat(fileKeys);
    const readOnly = props.section === 'data' && !props.isManaged;
    const downloadList = getDownloadList(props, state);
    const downloadDisabled = props.isLocked || state.downloadingEdges || state.downloadingAll;
    const { fileTooLarge, filePrompted } = getQueuedFiles(uploadData);
    // declare css here
    const fileBrowserCSS = classNames({
      FileBrowser: true,
      'FileBrowser--linkVisible': state.showLinkModal,
      'FileBrowser--highlight': isOver,
      'FileBrowser--cursor-drop': isOver && canDrop,
      'FileBrowser--cursor-no-drop': isOver && !canDrop,
      'FileBrowser--dropzone': fileKeys.length === 0,
    });
    const multiSelectButtonCSS = classNames({
      CheckboxMultiselect: true,
      CheckboxMultiselect__check: state.multiSelect === 'all',
      CheckboxMultiselect__uncheck: state.multiSelect === 'none',
      CheckboxMultiselect__partial: state.multiSelect === 'partial',
    });
    const nameHeaderCSS = classNames({
      'FileBrowser__name-text FileBrowser__header--name flex justify--start Btn--noStyle': true,
      'FileBroser__sort--asc': state.sort === 'az' && !state.reverse,
      'FileBroser__sort--desc': state.sort === 'az' && state.reverse,
    });
    const sizeHeaderCSS = classNames({
      'FileBrowser__header--size Btn--noStyle': true,
      'FileBroser__sort--asc': state.sort === 'size' && !state.reverse,
      'FileBroser__sort--desc': state.sort === 'size' && state.reverse,
    });
    const modifiedHeaderCSS = classNames({
      'FileBrowser__header--date Btn--noStyle': true,
      'FileBroser__sort--asc': state.sort === 'modified' && !state.reverse,
      'FileBroser__sort--desc': state.sort === 'modified' && state.reverse,
    });

    const multiSelectCSS = classNames({
      'FileBrowser__multiselect flex justify--start': true,
    });
    const dropBoxCSS = classNames({
      'Dropbox Dropbox--fileBrowser flex flex--column align-items--center': true,
      'Dropbox--hovered': isOver,
    });
    return (
      props.connectDropTarget(
        <div
          ref={ref => ref}
          className={fileBrowserCSS}
          style={{ zIndex: state.fileSizePromptVisible ? 13 : 0 }}
        >
          {
            (props.section === 'input')
            && (
              <div>
                <Datasets
                  linkedDatasets={props.linkedDatasets}
                  files={state.files}
                  showLinkModal={this._showLinkModal}
                  isLocked={props.isLocked}
                  checkLocal={checkLocalIndividual}
                  mutationData={mutationData}
                  mutations={state.mutations}
                  section={props.section}
                  name={name}
                  owner={owner}
                />
              </div>
            )
          }
          { state.showLinkModal
            && (
              <LinkModal
                closeLinkModal={() => this._showLinkModal(false)}
                linkedDatasets={props.linkedDatasets || []}
                name={name}
                owner={owner}
              />
            )
          }
          { state.fileSizePromptVisible
             && (
               <FileSizePromptModal
                 cancelUpload={this._cancelUpload}
                 userRejectsUpload={this._userRejectsUpload}
                 userAcceptsUpload={this._userAcceptsUpload}
                 uploadPromptText={uploadPromptText}
                 fileTooLarge={fileTooLarge}
                 filePrompted={filePrompted}
                 name={name}
                 owner={owner}
                 section={section}
               />
             )
           }

          <h4 className="margin--0 regular">Files</h4>

          <FileBrowserTools
            updateVisibleFolder={this._updateVisibleFolder}
            updateSearchState={this._updateSearchState}
            uploadFiles={this._uploadFiles}
            handleDownloadAll={this._handleDownloadAll}
            updateUnmanagedDatasetMutation={this._updateUnmanagedDatasetMutation}
            updateConfirmVisible={this._updateConfirmVisible}
            confirmUpdateVisible={state.confirmUpdateVisible}
            downloadingAll={state.downloadingAll}
            readOnly={readOnly}
            allFilesLocal={allFilesLocal}
            section={props.section}
            mutations={state.mutations}
            name={name}
            owner={owner}
          />

          {
            isSelected
            && (
              <FileBrowserToolbar
                deleteSelectedFiles={this._deleteSelectedFiles}
                downloadSelectedFiles={this._downloadSelectedFiles}
                togglePopup={this._togglePopup}
                isLocked={props.isLocked}
                downloadList={downloadList}
                downloadDisabled={downloadDisabled}
                section={props.section}
                selectedCount={state.selectedCount}
                popupVisible={state.popupVisible}
                name={name}
                owner={owner}
              />
            )
          }
          <div className="FileBrowser__header">
            {
              !readOnly
              && (
                <div className={multiSelectCSS}>
                  <button
                    className={multiSelectButtonCSS}
                    onClick={() => { this._selectFiles(); }}
                    type="button"
                  />
                </div>
              )
            }
            <button
              className={nameHeaderCSS}
              onClick={() => this._handleSort('az')}
              type="button"
            >
              File
            </button>

            <button
              className={sizeHeaderCSS}
              onClick={() => this._handleSort('size')}
              type="button"
            >
              Size
            </button>

            <button
              className={modifiedHeaderCSS}
              onClick={() => this._handleSort('modified')}
              type="button"
            >
              Modified
            </button>
            <div className="FileBrowser__header--menu flex flex--row justify--left">
              Actions
            </div>
          </div>
          <div className="FileBrowser__body">

            <AddSubfolder
              key="rootAddSubfolder"
              folderKey=""
              mutationData={mutationData}
              mutations={state.mutations}
              setAddFolderVisible={visibility => this.setState({ addFolderVisible: visibility })}
              addFolderVisible={state.addFolderVisible}
              name={name}
              owner={owner}
            />

            { childrenKeys.map((file) => {
              const isDir = files[file] && files[file].edge && files[file].edge.node.isDir;
              const isFile = files[file] && files[file].edge && !files[file].edge.node.isDir;
              const isDataset = files[file] && files[file].edge && files[file].edge.node.isDataset;
              const parentDownloading = state.downloadingAll
                || (state.downloadingEdges
                && state.downloadingEdges.has(files[file].edge.node.key));

              if (isDataset) {
                return (
                  <div
                    key={files[file].edge.node.key}
                  />
                );
              } if (isDir) {
                return (
                  <Folder
                    ref={file}
                    filename={file}
                    readOnly={readOnly}
                    key={files[file].edge.node.key}
                    multiSelect={state.multiSelect}
                    mutationData={mutationData}
                    fileData={files[file]}
                    isLocal={checkLocalIndividual(files[file])}
                    mutations={state.mutations}
                    setState={this._setState}
                    rowStyle={{}}
                    sort={state.sort}
                    reverse={state.reverse}
                    childrenState={state.childrenState}
                    section={props.section}
                    updateChildState={this._updateChildState}
                    parentDownloading={parentDownloading}
                    rootFolder
                    relay={props.relay}
                    fileSizePrompt={this._fileSizePrompt}
                    checkLocal={checkLocalIndividual}
                    containerStatus={props.containerStatus}
                    refetch={this._refetch}
                    name={name}
                    owner={owner}
                  />
                );
              } if (isFile) {
                return (
                  <File
                    ref={file}
                    filename={file}
                    readOnly={readOnly}
                    key={files[file].edge.node.key}
                    multiSelect={state.multiSelect}
                    mutationData={mutationData}
                    fileData={files[file]}
                    isLocal={checkLocalIndividual(files[file])}
                    childrenState={state.childrenState}
                    mutations={state.mutations}
                    expanded
                    section={props.section}
                    isOverChildFile={state.isOverChildFile}
                    updateParentDropZone={this._updateDropZone}
                    parentDownloading={parentDownloading}
                    updateChildState={this._updateChildState}
                    checkLocal={checkLocalIndividual}
                    containerStatus={props.containerStatus}
                    name={name}
                    owner={owner}
                  />
                );
              }

              return (
                <div
                  key={file}
                >
                  Loading
                </div>
              );
            })}

            { (childrenKeys.length === 0) && (state.search !== '')
                && (
                <div className="FileBrowser__empty">
                  <h5>No files match your search.</h5>
                </div>
                )
            }

            { (childrenKeys.length === 0) && (state.search === '')
                && (
                  <div className={dropBoxCSS}>
                    <div className="Dropbox--menu">
                      Drag and drop files here
                      <br />
                      <span>or</span>
                    </div>
                    <label
                      htmlFor="add_file"
                      className="flex justify--center"
                    >
                      <div
                        className="Btn Btn--allStyling"
                      >
                        Choose Files...
                      </div>
                      <input
                        id="add_file"
                        className="hidden"
                        type="file"
                        onChange={(evt) => {
                          this._uploadFiles(Array.prototype.slice.call(evt.target.files));
                        }}
                      />
                    </label>
                  </div>
                )
            }

            { (props.isProcessing || props.lockFileBrowser)
              && (
                <div className="FileBrowser__lock">
                  <span />
                </div>
              )
            }
          </div>
        </div>,
      )
    );
  }
}

export default DropTarget(
  ['card', NativeTypes.FILE],
  Connectors.targetSource,
  Connectors.targetCollect,
)(FileBrowser);
