// vendor
import React, { Component } from 'react';
import store from 'JS/redux/store';
import { DropTarget } from 'react-dnd';
import { NativeTypes } from 'react-dnd-html5-backend';
import classNames from 'classnames';
// assets
import './FileBrowser.scss';
// components
import File from './fileRow/File';
import Folder from './fileRow/Folder';
import AddSubfolder from './fileRow/AddSubfolder';
import FileBrowserMutations from './utilities/FileBrowserMutations';
import Connectors from './utilities/Connectors';

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
      };

      this._deleteSelectedFiles = this._deleteSelectedFiles.bind(this);
      this._setState = this._setState.bind(this);
      this._updateChildState = this._updateChildState.bind(this);
      this._checkChildState = this._checkChildState.bind(this);
      this._updateDropZone = this._updateDropZone.bind(this);
    }
    static getDerivedStateFromProps(props, state) {
        let previousCount = state.count;
        let count = props.files.edges.length;
        let childrenState = {};
        props.files.edges.forEach((edge) => {
          if (edge.node && edge.node.key) {
            let key = edge.node.key.split('/').join('');
            childrenState[key] = {
              isSelected: (state.childrenState && state.childrenState[key]) ? state.childrenState[key].isSelected : false,
              edge,
            };
          }
        });

        return {
          ...state,
          childrenState,
          search: count === previousCount ? state.search : '',
          count,
        };
    }
    /*
      resets search
    */
    componentDidUpdate() {
      let element = document.getElementsByClassName('FileBrowser__input')[0];
      if (this.state.search === '' && element.value !== '') {
        element.value = '';
      }
    }
    /**
    *  @param {string} key - key of file to be updated
    *  @param {boolean} isSelected - update if the value is selected
    *  @return {}
    */
    _updateChildState(key, isSelected) {
      let isChildSelected = false;
      let count = 0;
      let selectedCount = 0;
      let { childrenState } = this.state;
      let santizedKey = key.split('/').join('');
      childrenState[santizedKey].isSelected = isSelected;

      for (let key in childrenState) {
        if (childrenState[key]) {
          if (childrenState[key].isSelected) {
            isChildSelected = true;
            selectedCount++;
          }
          count++;
        }
      }

      let multiSelect = !isChildSelected ? 'none' : (selectedCount === count) ? 'all' : 'partial';

      this.setState({ childrenState, multiSelect });
    }
    /**
    *  @param {}
    *  update state of component for a given key value pair
    *  @return {}
    */
    _setState(stateKey, value) {
       this.setState({ [stateKey]: value });
    }
    /**
    *  @param {}
    *  sorts files into an object for rendering
    *  @return {}
    */
    _processFiles() {
        let edges = this.props.files.edges;
        let edgesToSort = JSON.parse(JSON.stringify(edges));
        let fileObject = {};
        const { search } = this.state;
        const searchLowerCase = search.toLowerCase();

        if (search !== '') {
          let edgesSearchMatch = edgesToSort.filter((edge) => {
            const lowerCaseKey = edge.node.key.toLowerCase();
            return (lowerCaseKey.indexOf(searchLowerCase) > -1);
          });

          edgesToSort = edgesToSort.filter((edge) => {
            let keyMatch = false;
            edgesSearchMatch.forEach((matchEdge) => {
              if (matchEdge.node.key.indexOf(edge.node.key) > -1) {
                keyMatch = true;
              }
            });
            return keyMatch;
          });
        }

        edgesToSort.forEach((edge, index) => {
            let key = edge.node.key.toLowerCase();
            let searchLowerCase = search.toLowerCase();


            if (edge.node) {
              let currentObject = fileObject;
              let splitKey = edge.node.key.split('/').filter(key => key.length);

              splitKey.forEach((key, index) => {
                  if (currentObject && (index === (splitKey.length - 1))) {
                      if (!currentObject[key]) {
                        currentObject[key] = {
                          edge,
                          index,
                        };
                      } else {
                        currentObject[key].edge = edge;
                      }
                  } else if (currentObject && !currentObject[key]) {
                      currentObject[key] = {
                        children: {},
                      };
                      currentObject = currentObject[key].children;
                  } else if (currentObject && currentObject[key] && !currentObject[key].children) {
                      currentObject[key].children = {};
                      currentObject = currentObject[key].children;
                  } else {
                    currentObject = currentObject[key].children;
                  }
              });
           }
        });
        return fileObject;
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
      favoriteConnection,
      section,
    } = this.props;
    const { owner, labbookName } = store.getState().routes;

    return {
      owner,
      labbookName,
      parentId,
      connection,
      favoriteConnection,
      section,
    };
  }
  /**
  *  @param {}
  *  loops through selcted files and deletes them
  *  @return {}
  */
  _deleteSelectedFiles() {
    let self = this;
    let filePaths = [];
    let dirList = [];
    let comparePaths = [];
    let edges = [];

    for (let key in this.state.childrenState) {
      if (this.state.childrenState[key].isSelected) {
        let { edge } = this.state.childrenState[key];
        delete this.state.childrenState[key];
        comparePaths.push(edge.node.key);
        filePaths.push(edge.node.key);
        edges.push(edge);
        if (edge.node.isDir) {
          dirList.push(edge.node.key);
        }
      }
    }

    let filteredPaths = filePaths.filter((key) => {
      let folderKey = key.substr(0, key.lastIndexOf('/'));
      folderKey = `${folderKey}/`;

      let hasDir = dirList.some(dir => ((key.indexOf(dir) > -1) && (dir !== key)));
      return !hasDir;
    });
    self._deleteMutation(filteredPaths, edges);
  }

  /**
  *  @param {}
  *  selects all or unselects files
  *  @return {}
  */
  _selectFiles() {
    let isSelected = false;
    let count = 0;
    let selectedCount = 0;

    for (let key in this.state.childrenState) {
      if (this.state.childrenState[key]) {
        if (this.state.childrenState[key].isSelected) {
          isSelected = true;
          selectedCount++;
        }
        count++;
      }
    }
    let multiSelect = (count === selectedCount) ? 'none' : 'all';

    let { childrenState } = this.state;

    for (let key in childrenState) {
      if (childrenState[key]) {
        childrenState[key].isSelected = (multiSelect === 'all');
        count++;
      }
    }
    this.setState({ multiSelect, childrenState });
  }

  /**
  *  @param {}
  *  triggers delete muatation
  *  @return {}
  */
  _deleteMutation(filePaths, edges) {
    const data = {
      filePaths,
      edges,
    };
    this.setState({ multiSelect: 'none' });
    this.state.mutations.deleteLabbookFiles(data, (response) => {});
  }
  /**
  *  @param {string, boolean}
  *  updates boolean state of a given key
  *  @return {}
  */
  _updateStateBoolean(key, value) {
    this.setState({ [key]: value });
  }
  /**
  *  @param {}
  *  checks if folder refs has props.isOver === true
  *  @return {boolean}
  */
  _checkRefs() {
    let isOver = this.props.isOverCurrent || this.props.isOver, // this.state.isOverChildFile,
        { refs } = this;

        Object.keys(refs).forEach((childname) => {
          if (refs[childname].getDecoratedComponentInstance && refs[childname].getDecoratedComponentInstance() && refs[childname].getDecoratedComponentInstance().getDecoratedComponentInstance && refs[childname].getDecoratedComponentInstance().getDecoratedComponentInstance()) {
            const child = refs[childname].getDecoratedComponentInstance().getDecoratedComponentInstance();
            if (child.props.data && !child.props.data.edge.node.isDir) {
              if (child.props.isOverCurrent) {
                isOver = true;
              }
            }
          }
        });
    return ({
      isOver,
    });
  }
  /**
  *  @param {}
  *  checks if folder refs has props.isOver === true
  *  @return {boolean} isSelected - returns true if a child has been selected
  */
  _checkChildState() {
    let isSelected = false;

    for (let key in this.state.childrenState) {
      if (this.state.childrenState[key].isSelected) {
        isSelected = true;
      }
    }

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
  _updateDropZone(isOverChildFile) {
    this.setState({ isOverChildFile });
  }
  /**
  *  @param {Array, String, Boolean, Object, String} array, type, reverse, children, section
  *  returns sorted children
  *  @return {}
  */
 _childSort(array, type, reverse, children, section) {
  array.sort((a, b) => {
    let lowerA,
    lowerB;
    if (type === 'az' || type === 'size' && section === 'folder') {
      lowerA = a.toLowerCase();
      lowerB = b.toLowerCase();
      if (type === 'size' || !reverse) {
        return (lowerA < lowerB) ? -1 : (lowerA > lowerB) ? 1 : 0;
      }
      return (lowerA < lowerB) ? 1 : (lowerA > lowerB) ? -1 : 0;
    } else if (type === 'modified') {
      lowerA = children[a].edge.node.modifiedAt;
      lowerB = children[b].edge.node.modifiedAt;
      return reverse ? lowerB - lowerA : lowerA - lowerB;
    } else if (type === 'size') {
      lowerA = children[a].edge.node.size;
      lowerB = children[b].edge.node.size;
      return reverse ? lowerB - lowerA : lowerA - lowerB;
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
    if (type === this.state.sort) {
      this.setState({ reverse: !this.state.reverse });
    } else {
      this.setState({ sort: type, reverse: false });
    }
  }

  render() {
    const files = this._processFiles(),
          { mutationData } = this.state,
          { isOver } = this.props;
    let folderKeys = files && Object.keys(files).filter(child => files[child].edge && files[child].edge.node.isDir) || [];
    folderKeys = this._childSort(folderKeys, this.state.sort, this.state.reverse, files, 'folder');
    let fileKeys = files && Object.keys(files).filter(child => files[child].edge && !files[child].edge.node.isDir) || [];
    fileKeys = this._childSort(fileKeys, this.state.sort, this.state.reverse, files, 'files');
    let childrenKeys = folderKeys.concat(fileKeys);

   const { isSelected } = this._checkChildState();

   const fileBrowserCSS = classNames({
           FileBrowser: true,
           'FileBrowser--highlight': isOver,
           'FileBrowser--dropzone': fileKeys.length === 0,
         }),
         deleteButtonCSS = classNames({
           'Btn Btn--round Btn--delete': true,
           hidden: !isSelected,
         }),
         multiSelectButtonCSS = classNames({
           'Btn Btn--round': true,
           'Btn--check': this.state.multiSelect === 'all',
           'Btn--uncheck': this.state.multiSelect === 'none',
           'Btn--partial': this.state.multiSelect === 'partial',
         }),
         nameHeaderCSS = classNames({
          'FileBrowser__name-text': true,
          'FileBroser__sort--asc': this.state.sort === 'az' && !this.state.reverse,
          'FileBroser__sort--desc': this.state.sort === 'az' && this.state.reverse,
         }),
         sizeHeaderCSS = classNames({
          'FileBrowser__header--size': true,
          'FileBroser__sort--asc': this.state.sort === 'size' && !this.state.reverse,
          'FileBroser__sort--desc': this.state.sort === 'size' && this.state.reverse,
         }),
         modifiedHeaderCSS = classNames({
          'FileBrowser__header--date': true,
          'FileBroser__sort--asc': this.state.sort === 'modified' && !this.state.reverse,
          'FileBroser__sort--desc': this.state.sort === 'modified' && this.state.reverse,
         });

   return (
       this.props.connectDropTarget(<div className={fileBrowserCSS}>

                <div className="FileBrowser__tools flex justify--space-between">
                  <div className="FileBrowser__multiselect flex justify--start">
                    <button
                      className={multiSelectButtonCSS}
                      onClick={() => { this._selectFiles(); }} />
                    <button
                      className={deleteButtonCSS}
                      onClick={() => { this._deleteSelectedFiles(); }} />
                  </div>
                  <div className="FileBrowser__search flex-1">
                    <input
                      className="FileBrowser__input full--border"
                      type="text"
                      placeholder="Search Files Here"
                      onChange={(evt) => { this._updateSearchState(evt); } }
                      onKeyUp={(evt) => { this._updateSearchState(evt); } }
                    />
                  </div>
                </div>
                <div className="FileBrowser__header">
                    <div
                      className="FileBrowser__header--name flex justify--start"
                      onClick={() => this._handleSort('az')}
                    >
                      <div
                        className={nameHeaderCSS}
                      >
                        File
                      </div>
                    </div>

                    <div
                      className={sizeHeaderCSS}
                      onClick={() => this._handleSort('size')}
                    >
                        Size
                    </div>

                    <div
                      className={modifiedHeaderCSS}
                      onClick={() => this._handleSort('modified')}
                    >
                        Modified
                    </div>

                    <div className="FileBrowser__header--menu">
                    </div>
                </div>
            <div className="FileBrowser__body">
                <AddSubfolder
                  key={'rootAddSubfolder'}
                  folderKey=""
                  mutationData={mutationData}
                  mutations={this.state.mutations}
                />
                {
                    childrenKeys.map((file, index) => {
                        if (files[file] && files[file].edge && files[file].edge.node.isDir) {
                            return (
                                <Folder
                                    ref={file}
                                    filename={file}
                                    key={files[file].edge.node.key}
                                    multiSelect={this.state.multiSelect}
                                    mutationData={mutationData}
                                    data={files[file]}
                                    mutations={this.state.mutations}
                                    setState={this._setState}
                                    rowStyle={{}}
                                    sort={this.state.sort}
                                    reverse={this.state.reverse}
                                    updateChildState={this._updateChildState}>
                                </Folder>
                            );
                        } else if (files[file] && files[file].edge && !files[file].edge.node.isDir) {
                          return (
                              <File
                                  ref={file}
                                  filename={file}
                                  key={files[file].edge.node.key}
                                  multiSelect={this.state.multiSelect}
                                  mutationData={mutationData}
                                  data={files[file]}
                                  mutations={this.state.mutations}
                                  expanded
                                  isOverChildFile={this.state.isOverChildFile}
                                  updateParentDropZone={this._updateDropZone}
                                  updateChildState={this._updateChildState}>

                              </File>
                          );
                        } else if (files[file]) {
                          return (
                            <div
                              key={file + index}
                            />
                            );
                        }
                        return (
                          <div
                              key={file + index}
                          >
                            Loading
                          </div>
                          );
                    })
                }
                { (childrenKeys.length === 0) &&
                  <div className="FileBrowser__empty">
                    <h5>Upload Files by Dragging & Dropping Here</h5>
                  </div>
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
