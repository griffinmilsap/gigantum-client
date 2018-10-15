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

const sortFolders = (a, b) => {
  if (a.node.isDir && !b.node.isDir) {
    return -1;
  } else if (!a.node.isDir && b.node.isDir) {
    return 1;
  }
  return 0;
};

class FileBrowser extends Component {
    constructor(props) {
      super(props);

      this.state = {
        mutations: new FileBrowserMutations(this._getMutationData()),
        mutationData: this._getMutationData(),
        hoverId: '',
      };

      this._deleteSelectedFiles = this._deleteSelectedFiles.bind(this);
      this._setState = this._setState.bind(this);
    }
    /**
    *  @param {}
    *  update state of component for a given key value pair
    *  @return {}
    */
    _setState(stateKey, value) {
       console.log(stateKey)
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
        console.log(edges)
        // console.log(edgesSort)
        // edgesSort.sort(sortFolders);
        let edgeSorted = edgesToSort.sort(sortFolders)
        console.log(edgeSorted)

        let fileObject = {};


        edgeSorted.forEach((edge) => {
            let splitKey = edge.node.key.split('/', -1).filter(key => key.length);
            let currentFileObjectPosition = fileObject;

            splitKey.forEach((key) => {

                if (!fileObject[key]) {
                    fileObject[key] = {
                      children: {},
                      edge,
                    };
                }
                currentFileObjectPosition = currentFileObjectPosition[key].children;
            }

            if (splitKey.length === 1) {
                if (currentFileObjectPosition && currentFileObjectPosition[splitKey[0]]) {
                    currentFileObjectPosition[splitKey[0]].edge = edge;
                } else if (currentFileObjectPosition) {
                    currentFileObjectPosition[splitKey[0]] = { edge };
                }
                if (edge.node.isDir && !currentFileObjectPosition[splitKey[0]]) {
                    currentFileObjectPosition[splitKey[0]] = { edge, children: {} };
                }
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
    function loopDelete(refs) {
      Object.keys(refs).forEach((filename) => {
        const file = refs[filename].getDecoratedComponentInstance().getDecoratedComponentInstance();

        const { edge } = file.props.data;

        if (file.state.isSelected) {
          self._deleteMutation(edge.node.key, edge);
        } else if (file.props.data.edge.node.isDir && !file.state.isSelected) {
          loopDelete(file.refs);
        }
      });
    }

    loopDelete(this.refs);
  }

  /**
  *  @param {}
  *  triggers delete muatation
  *  @return {}
  */
  _deleteMutation(key, edge) {
    const data = {
      key,
      edge,
    };

    this.state.mutations.deleteLabbookFile(data, (response) => {
      console.log(response, edge);
    });
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
    let isOver = this.props.isOver;

    function checkRefs(refs) {
      Object.keys(refs).forEach((childname) => {
        if (refs[childname].getDecoratedComponentInstance && refs[childname].getDecoratedComponentInstance() && refs[childname].getDecoratedComponentInstance().getDecoratedComponentInstance && refs[childname].getDecoratedComponentInstance().getDecoratedComponentInstance()) {
          const child = refs[childname].getDecoratedComponentInstance().getDecoratedComponentInstance();
          if (child.props.data && child.props.data.edge.node.isDir) {
            if (child.props.isOver) {

              isOver = false;
            } else if (Object.keys(child.refs).length > 0) {
              checkRefs(child.refs);
            }
          }
        }
      });
    }

    if (Object.keys(this.refs).length > 0) {
      checkRefs(this.refs);
    }
    return (isOver);
  }

  render() {
    const files = this._processFiles(),
          { mutationData } = this.state,
          isOver = this._checkRefs();

   const fileBrowserCSS = classNames({
     FileBrowser: true,
     'FileBrowser--highlight': isOver,
   });

   return (
       this.props.connectDropTarget(<div className={fileBrowserCSS}>
                <div className="FileBrowser__header">
                    <div>
                        <button className="FileBrowser__btn FileBrowser__btn --delete"
                          onClick={() => { this._deleteSelectedFiles(); }} />
                        File
                    </div>

                    <div>
                        Size
                    </div>

                    <div>
                        Modified
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
                    Object.keys(files).map((file) => {
                        if (files[file].children) {
                            return (
                                <Folder
                                    ref={file}
                                    key={files[file].edge.node.key}
                                    mutationData={mutationData}
                                    data={files[file]}
                                    mutations={this.state.mutations}
                                    setState={this._setState}>
                                </Folder>
                            );
                        }
                        return (
                            <File
                                ref={file}
                                key={files[file].edge.node.key}
                                mutationData={mutationData}
                                data={files[file]}
                                mutations={this.state.mutations}>
                            </File>
                        );
                    })
                }
            </div>
            {/* <div className={drogTargetCSS}>
              <h3 className="FileBrowser__h3">Add file to root</h3>
            </div> */}
        </div>)
    );
  }
}


export default DropTarget(
    ['card', NativeTypes.FILE],
    Connectors.targetSource,
    Connectors.targetCollect,
  )(FileBrowser);
