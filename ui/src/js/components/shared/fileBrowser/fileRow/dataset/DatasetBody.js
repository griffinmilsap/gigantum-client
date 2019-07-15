// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
// components
import File from './DatasetFile';
import Folder from './DatasetFolder';

/**
*  @param {Array:[Object]} array
*  @param {string} type
*  @param {boolean} reverse
*  @param {Object} children
*  @param {string} section
*  returns sorted children
*  @return {}
*/
const childSort = (array, type, reverse, children, section) => {
  array.sort((a, b) => {
    let lowerB;
    let lowerA;
    if ((type === 'az') || ((type === 'size') && (section === 'folder'))) {
      lowerA = a.toLowerCase();
      lowerB = b.toLowerCase();
      if (type === 'size' || !reverse) {
        if (lowerA < lowerB) {
          return -1;
        }
        return (lowerA > lowerB) ? 1 : 0;
      }
      if (lowerA < lowerB) {
        return 1;
      }
      return (lowerA > lowerB) ? -1 : 0;
    } if (type === 'modified') {
      lowerA = children[a].edge.node.modifiedAt;
      lowerB = children[b].edge.node.modifiedAt;
      return reverse ? lowerB - lowerA : lowerA - lowerB;
    } if (type === 'size') {
      lowerA = children[a].edge.node.size;
      lowerB = children[b].edge.node.size;
      return reverse ? lowerB - lowerA : lowerA - lowerB;
    }
    return 0;
  });
  return array;
}

export default class Datasets extends Component {
  state = {
    sort: 'az',
    reverse: false,
  }

  /**
  *  @param {String} Type
  *  handles state changes for type
  *  @return {}
  */
  _handleSort(type) {
    const { state } = this;
    if (type === state.sort) {
      this.setState({ reverse: !state.reverse });
    } else {
      this.setState({ sort: type, reverse: false });
    }
  }

  render() {
    const { state, props } = this;
    const { files } = props;
    let folderKeys = (files && Object.keys(files).filter(child => files[child].edge && files[child].edge.node.isDir)) || [];
    folderKeys = childSort(folderKeys, state.sort, state.reverse, files, 'folder');
    let fileKeys = (files && Object.keys(files).filter(child => files[child].edge && !files[child].edge.node.isDir)) || [];
    fileKeys = childSort(fileKeys, state.sort, state.reverse, files, 'files');
    const childrenKeys = folderKeys.concat(fileKeys);

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
    return (
      <div className="DatasetBody">
        <div className="FileBrowser__header">

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
          { childrenKeys.map((file) => {
            const isDir = files[file] && files[file].edge && files[file].edge.node.isDir;
            const isFile = files[file] && files[file].edge && !files[file].edge.node.isDir;

            if (isDir) {
              return (
                <Folder
                  ref={file}
                  filename={file}
                  key={files[file].edge.node.key}
                  mutationData={props.mutationData}
                  fileData={files[file]}
                  isLocal={props.checkLocal(files[file])}
                  mutations={props.mutations}
                  setState={this._setState}
                  rowStyle={{}}
                  sort={state.sort}
                  reverse={state.reverse}
                  section={props.section}
                  isDownloading={props.downloadPending}
                  rootFolder
                  fileSizePrompt={this._fileSizePrompt}
                  checkLocal={props.checkLocal}
                  containerStatus={props.containerStatus}
                  refetch={this._refetch}
                />
              );
            } if (isFile) {
              return (
                <File
                  ref={file}
                  filename={file}
                  key={files[file].edge.node.key}
                  mutationData={props.mutationData}
                  fileData={files[file]}
                  isLocal={props.checkLocal(files[file])}
                  mutations={props.mutations}
                  expanded
                  section={props.section}
                  isOverChildFile={state.isOverChildFile}
                  isDownloading={props.downloadPending}
                  checkLocal={props.checkLocal}
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
          { (childrenKeys.length === 0)
            && (
            <div className="FileBrowser__empty">
              <h5>This Dataset has no files.</h5>
            </div>
            )
          }
        </div>
      </div>
    );
  }
}
