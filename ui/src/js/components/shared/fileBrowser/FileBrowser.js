// vendor
import React, { Component } from 'react';
import store from 'JS/redux/store';
import { DropTarget } from 'react-dnd';
import { NativeTypes } from 'react-dnd-html5-backend';
import classNames from 'classnames';
import isEqual from 'react-fast-compare';
import { boundMethod } from 'autobind-decorator';
// assets
import './FileBrowser.scss';
// components
import Modal from 'Components/common/Modal';
import LinkModal from './LinkModal';
import File from './fileRow/File';
import Folder from './fileRow/Folder';
import Datasets from './fileRow/dataset/Datasets';
import AddSubfolder from './fileRow/AddSubfolder';
// util
import prepareUpload from './utilities/PrepareUpload';
import FileBrowserMutations from './utilities/FileBrowserMutations';
import Connectors from './utilities/Connectors';
import FileFormatter, { fileHandler } from './utilities/FileFormatter';


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
  @boundMethod
  _refetch() {
    const { relay } = this.props;
    this.setState({ isRefetching: true })
    relay.refetchConnection(
      100,
      (response, error) => {

        if (error) {
          console.log(error);
        }

        this.props.loadMore();
      },
    );
  }

  /**
    *  @param {Boolean} allFilesLocal
    *  handles downloading all files in data-filebrowser
    *  @return {}
    */
  _handleDownloadAll(allFilesLocal) {
    if (!this.state.downloadingAll && !allFilesLocal) {
      const { owner, labbookName } = store.getState().routes;
      const data = {
        owner,
        datasetName: labbookName,
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
      this.state.mutations.downloadDatasetFiles(data, callback);
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
  _updateChildState = (key, isSelected, isIncomplete, isExpanded, isAddingFolder) => {
    let multiCount = 0;
    let multiSelect;
    const { state, props } = this;
    const { childrenState } = state;
    childrenState[key].isSelected = isSelected;
    childrenState[key].isIncomplete = isIncomplete;
    childrenState[key].isExpanded = isExpanded;
    childrenState[key].isAddingFolder = isAddingFolder;

    Object.keys(childrenState).forEach((childKey) => {
      if (childrenState[childKey].isSelected) {
        multiCount += 1;
      }
    });

    multiSelect = (multiCount >= props.files.edges.length) ? 'all' : 'partial';
    multiSelect = multiCount === 0 ? 'none' : multiSelect;

    this.setState({ childrenState, multiSelect });
  }

  /**
    *  @param {string} stateKey
    *  @param {string || boolean || number} value
    *  update state of component for a given key value pair
    *  @return {}
    */
  @boundMethod
  _setState(key, value) {
    this.setState({ [key]: value });
  }

  /**
  *  @param {}
  *  sorts files into an object for rendering
  *  @return {object}
  */
  _getMutationData() {
    const {
      parentId,
      connection,
      section,
    } = this.props;
    const { owner, labbookName } = store.getState().routes;

    return {
      owner,
      labbookName,
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
  _togglePopup(popupVisible) {
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
        const { edge } = this.state.childrenState[key];
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

    Object.keys(this.state.childrenState).forEach((key) => {
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
  *  @param {Array} toDownload
  *  loops through selcted files and downloads them
  *  @return {}
  */
  _downloadSelectedFiles = (toDownload) => {
    const { state, props } = this;
    const { owner } = props;
    const datasetName = props.name;
    const data = {
      owner,
      datasetName,
      keys: toDownload,
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

    this.setState({ downloadingEdges: new Set(toDownload) });
    state.mutations.downloadDatasetFiles(data, callback);
  }

  /**
  *  @param {}
  *  selects all or unselects files
  *  @return {}
  */
  _selectFiles() {
    const { state } = this;
    const count = Object.keys(state.childrenState).length;

    let multiSelect = (count === state.selectedCount) ? 'none' : 'all';
    const { childrenState } = this.state;
    let isSelectedCount = 0;
    Object.keys(state.childrenState).forEach((key) => {
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
  _deleteMutation(filePaths, edges) {
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
  _updateStateBoolean(key, value) {
    this.setState({ [key]: value });
  }

  /**
  *  @param {}
  *  checks if folder refs has props.isOver === true
  *  @return {boolean} isSelected - returns true if a child has been selected
  */
  @boundMethod
  _checkChildState() {
    const { state } = this;
    let isSelected = false;

    Object.keys(state.childrenState).forEach((key) => {
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
  _updateSearchState(evt) {
    this.setState({ search: evt.target.value });
  }

  /**
  *  @param {boolean} isOverChildFile
  *  update state to update drop zone
  *  @return {}
  */
  @boundMethod
  _updateDropZone(isOverChildFile) {
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
  _childSort(array, type, reverse, children, section) {
    array.sort((a, b) => {
      const isAUntracked = (a === 'untracked') && (section === 'folder') && (this.props.section === 'output');
      const isBUntracked = (b === 'untracked') && (section === 'folder') && (this.props.section === 'output');
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
  _handleSort(type) {
    const { state } = this
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
  @boundMethod
  _promptUserToAcceptUpload() {
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
  @boundMethod
  _fileSizePrompt(fileSizeData, uploadCallback) {
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
  @boundMethod
  _userAcceptsUpload() {
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
  *  @param {}
  *  creates a file using AddLabbookFileMutation by passing a blob
  *  set state of user prompt modal
  */
  @boundMethod
  _userRejectsUpload() {
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
  *  @param {}
  *  user cancels upload
  */
  _cancelUpload() {
    this.setState({ fileSizePromptVisible: false });
  }

  /**
  *  @param {}
  *  gets file prompt text individual sections
  *  @return {string}
  */
  _getFilePromptText() {
    const { props } = this;
    const firstChar = props.section.charAt(0).toUpperCase();
    const allOtherChars = props.section.substr(1, props.section.length - 1);
    const section = `${firstChar}/${allOtherChars}`;

    const text = (props.section === 'code')
      ? "You're uploading some large files to the Code Section, are you sure you don't want to place these in the Input Section? Note, putting large files in the Code Section can hurt performance."
      : `You're uploading some large files to the ${section} Section, are you sure you don't want to place these in a Dataset?`;
    return text;
  }

  /**
  *  @param {Array} files
  *  sends file selection upload to be prepared for upload
  *  @return {string}
  */
  _uploadFiles(files) {
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
  _updateUnmanagedDatasetMutation() {
    const { state } = this;

    state.mutations.updateUnmanagedDataset(
      {
        fromRemote: true,
        fromLocal: false,
      },
      () => {
        this.setState({ confirmUpdateVisible: false });
      },
    );
  }

  render() {
    const { props, state } = this;
    const { files, mutationData } = state;
    const { isOver, canDrop } = props;
    const { isSelected } = this._checkChildState();
    const allFilesLocal = checkLocalAll(files);
    const uploadPromptText = this._getFilePromptText();
    // TODO move this to a function
    let folderKeys = files && Object.keys(files).filter(child => files[child].edge && files[child].edge.node.isDir) || [];
    folderKeys = this._childSort(folderKeys, state.sort, state.reverse, files, 'folder');
    let fileKeys = files && Object.keys(files).filter(child => files[child].edge && !files[child].edge.node.isDir) || [];
    fileKeys = this._childSort(fileKeys, state.sort, state.reverse, files, 'files');
    const childrenKeys = folderKeys.concat(fileKeys);
    const readOnly = props.section === 'data' && !props.isManaged;
    const toDownload = [];
    const folderPlural = state.selectedFolderCount > 1 ? 's' : '';
    const filePlural = state.selectedFileCount > 1 ? 's' : '';
    const folderToolbarText = `${state.selectedFolderCount} folder${folderPlural}`;
    const fileToolbarText = `${state.selectedFileCount} file${filePlural}`;
    let toolbarText = `${folderToolbarText} and ${fileToolbarText} selected`;
    toolbarText = !state.selectedFolderCount ? `${fileToolbarText} selected` : toolbarText;
    toolbarText = !state.selectedFileCount ? `${folderToolbarText} selected` : toolbarText;
    if (props.section === 'data') {
      Object.keys(state.childrenState).forEach((key) => {
        if (state.childrenState[key].isSelected && !state.childrenState[key].edge.node.isLocal) {
          toDownload.push(state.childrenState[key].edge.node.key);
        }
      });
    }
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
    const popupCSS = classNames({
      FileBrowser__popup: true,
      hidden: !state.popupVisible,
      Tooltip__message: true,
    });
    const multiSelectCSS = classNames({
      'FileBrowser__multiselect flex justify--start': true,
    });
    const downloadAllCSS = classNames({
      'Btn__FileBrowserAction Btn--action': true,
      'Btn__FileBrowserAction--download Btn__FileBrowserAction--download--data ': !state.downloadingAll,
      'Btn__FileBrowserAction--loading Btn__FileBrowserAction--downloading': state.downloadingAll,
      'Tooltip-data Tooltip-data--small': allFilesLocal,
    });
    const updateCSS = classNames({
      'FileBrowser__update-modal': true,
      hidden: !state.confirmUpdateVisible,
    });
    const dropBoxCSS = classNames({
      'Dropbox Dropbox--fileBrowser flex flex--column align-items--center': true,
      'Dropbox--hovered': isOver,
    });
    const downloadDisabled = props.isLocked || state.downloadingEdges || state.downloadingAll;
    return (
      props.connectDropTarget(<div
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
                owner={props.owner}
                name={props.name}
                mutationData={mutationData}
                mutations={state.mutations}
                section={props.section}
              />
            </div>
          )
        }
        { state.showLinkModal
          && (
          <LinkModal
            closeLinkModal={() => this._showLinkModal(false)}
            linkedDatasets={props.linkedDatasets || []}
          />
          )
        }
        { state.fileSizePromptVisible
             && (
             <Modal
               header="Large File Warning"
               handleClose={() => this._cancelUpload()}
               size="medium"
               renderContent={() => (
                 <div className="FileBrowser__modal-body flex justify--space-between flex--column">

                   <p>{ uploadPromptText }</p>

                   <div className="FileBrowser__button-container flex justify--space-around">

                     <button
                       className="Btn--flat"
                       onClick={() => this._cancelUpload()}
                       type="button"
                     >
                     Cancel Upload
                     </button>

                     <button
                       onClick={() => this._userRejectsUpload()}
                       type="button"
                     >
                      Skip Large Files
                     </button>

                     <button
                       onClick={() => this._userAcceptsUpload()}
                       type="button"
                     >
                      Continue Upload
                     </button>

                   </div>

                 </div>
               )

             }
             />
             )
         }
        <h4 className="margin--0 regular">Files</h4>
        <div className="FileBrowser__tools flex justify--space-between">

          <div className="FileBrowser__search flex-1">
            <input
              className="FileBrowser__input search"
              type="text"
              placeholder="Search Files Here"
              onChange={(evt) => { this._updateSearchState(evt); }}
              onKeyUp={(evt) => { this._updateSearchState(evt); }}
            />
          </div>
          {
            !readOnly
            && (
              <div className="flex justify--right FileBrowser__Primary-actions">
                <button
                  className="Btn Btn--action Btn__FileBrowserAction Btn__FileBrowserAction--newFolder"
                  data-click-id="addFolder"
                  onClick={() => this.setState({ addFolderVisible: !state.addFolderVisible })}
                  type="button"
                >
                  New Folder
                </button>
                <label
                  htmlFor="browser_upload"
                  className="FileBrowser__upload-label"
                >
                  <div className="Btn__FileBrowserAction Btn__FileBrowserAction--upload inline-block Btn">
                    Add Files
                  </div>
                  <input
                    id="browser_upload"
                    className="hidden"
                    type="file"
                    multiple
                    onChange={evt => this._uploadFiles(Array.prototype.slice.call(evt.target.files))}
                  />
                </label>
                { (props.section === 'data')
                  && (
                  <button
                    className={downloadAllCSS}
                    disabled={allFilesLocal || state.downloadingAll}
                    onClick={() => this._handleDownloadAll(allFilesLocal)}
                    data-tooltip="No files to download"
                    type="button"
                  >
                    Download All
                  </button>
                  )
                }
              </div>
            )
          }
          {
            readOnly
            && (
            <div className="flex">
              <button
                className="Btn Btn__menuButton Btn--noShadow FileBrowser__newFolder"
                onClick={() => { this.state.mutations.verifyDataset({}, () => {}) }}
                type="button"
              >
                <div
                  className="Btn--fileBrowser Btn--round Btn--bordered Btn__upArrow Btn"
                />
                Verify Dataset
              </button>
              <div>
                <button
                  className="Btn Btn__menuButton Btn--noShadow FileBrowser__newFolder"
                  onClick={() => { state.mutations.verifyDataset({}, () => {}) }}
                  type="button"
                >
                  <div
                    className="Btn--fileBrowser Btn--round Btn--bordered Btn__upArrow Btn"
                  />
                  Update from Remote
                </button>
                <div>
                  <button
                    className="Btn Btn__menuButton Btn--noShadow FileBrowser__newFolder"
                    onClick={() => this.setState({ confirmUpdateVisible: !state.confirmUpdateVisible })}
                    type="button"
                  >
                    <div
                      className="Btn--fileBrowser Btn--round Btn--bordered Btn__upArrow Btn"
                    />
                    Update from Remote
                  </button>
                  <div className={updateCSS}>
                    <p>This will update the Dataset with the external source. Do you wish to continue?</p>
                    <div className="flex">
                      <button
                        type="button"
                        className="Btn--flat"
                        onClick={() => this.setState({ confirmUpdateVisible: false })}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => this._updateUnmanagedDatasetMutation}
                      >
                        Confirm
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            )
          }
        </div>
        {
          isSelected
          && (
        <div className="FileBrowser__toolbar flex align-items--center justify--space-between">
          <div className="FileBrowser__toolbar-text">
            {toolbarText}
          </div>
          <div>
            {
              ((props.section === 'data') && toDownload.length > 0)
              && (
              <button
                className="Btn align-self--end Btn__download-white Btn--background-left Btn--action Btn--padding-left"
                type="button"
                disabled={downloadDisabled}
                onClick={() => this._downloadSelectedFiles(toDownload)}
              >
                Download
              </button>
              )
            }
            <button
              type="button"
              className="Btn align-self--end Btn__delete-white Btn--background-left Btn--action Btn--padding-left"
              onClick={() => this._togglePopup(true)}
              disabled={props.isLocked}
            >
              Delete
            </button>
            <div className={popupCSS}>
              <div className="Tooltip__pointer" />
              <p>Are you sure?</p>
              <div className="flex justify--space-around">
                <button
                  className="File__btn--round File__btn--cancel File__btn--delete"
                  onClick={() => { this._togglePopup(false); }}
                  type="button"
                />
                <button
                  className="File__btn--round File__btn--add File__btn--delete-files"
                  onClick={() => { this._deleteSelectedFiles(); }}
                  type="button"
                />
              </div>
            </div>
          </div>
        </div>
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
          />

          { childrenKeys.map((file) => {
            const isDir = files[file] && files[file].edge && files[file].edge.node.isDir;
            const isFile = files[file] && files[file].edge && !files[file].edge.node.isDir;
            const isDataset = files[file] && files[file].edge && files[file].edge.node.isDataset;
            const parentDownloading = state.downloadingAll || (state.downloadingEdges && state.downloadingEdges.has(files[file].edge.node.key))

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
          })
          }
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
                  onChange={evt => this._uploadFiles(Array.prototype.slice.call(evt.target.files))}
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
      </div>)
    );
  }
}

export default DropTarget(
  ['card', NativeTypes.FILE],
  Connectors.targetSource,
  Connectors.targetCollect,
)(FileBrowser);
