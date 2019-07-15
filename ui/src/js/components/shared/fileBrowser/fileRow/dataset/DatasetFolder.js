// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import Moment from 'moment';
// components
import ActionsMenu from './DatasetActionsMenu';
import File from './DatasetFile';
// assets
import './DatasetFolder.scss';


class Folder extends Component {
  constructor(props) {
    super(props);
    this.state = {
      expanded: false,
      isDownloading: false,
      renameEditMode: false,
    };
  }

  /**
    *  @param {boolean} value
    *  sets visibility of edit mode
    *  @return {}
    */
  _renameEditMode(value) {
    this.setState({ renameEditMode: value });
  }

  /**
    *  @param {string} key
    *  @param {string || boolean} value - updates key value in state
    *  update state of component for a given key value pair
    *  @return {}
    */
  _setState = (key, value) => {
    this.setState({ [key]: value });
  }

  /**
    *  @param {Boolean} isDownloading
    *  sets parents element's isdownloading state
    *  @return {}
    */
  _setFolderIsDownloading = (isDownloading) => {
    this.setState({ isDownloading });
  }

  /**
    *  @param {Object} evt
    *  sets item to expanded
    *  @return {}
    */
  _expandSection = (evt) => {
    const { state } = this;
    if (!evt.target.classList.contains('Folder__btn')
      && !evt.target.classList.contains('ActionsMenu__item')
      && !evt.target.classList.contains('Btn--round')
      && !evt.target.classList.contains('DatasetActionsMenu__item')
      && !evt.target.classList.contains('File__btn--round')) {
      this.setState({ expanded: !state.expanded });
    }
    if (evt.target.classList.contains('ActionsMenu__item--AddSubfolder')) {
      this.setState({ expanded: true });
    }
  }

  /**
    *  @param {Array} array
    *  @param {String} type
    *  @param {Boolean} reverse
    *  @param {Object} children
    *  @param {String} section
    *  returns sorted children
    *  @return {}
    */
  _childSort = (array, type, reverse, children, section) => {
    array.sort((a, b) => {
      let lowerA;


      let lowerB;
      if (type === 'az' || type === 'size' && section === 'folder') {
        lowerA = a.toLowerCase();
        lowerB = b.toLowerCase();
        if (type === 'size' || !reverse) {
          return (lowerA < lowerB) ? -1 : (lowerA > lowerB) ? 1 : 0;
        }
        return (lowerA < lowerB) ? 1 : (lowerA > lowerB) ? -1 : 0;
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

  render() {
    const { props, state } = this;
    const isLocal = props.checkLocal(props.fileData);
    const { node } = props.fileData.edge;
    const { children, index } = props.fileData;
    const { isOver } = props;
    const splitKey = node.key.split('/');
    const folderName = props.filename;
    const paddingLeft = 40 * index;
    const rowStyle = { paddingLeft: `${paddingLeft}px` };
    const addRowStyle = {
      paddingLeft: `${paddingLeft + 120}px`,
      backgroundPositionX: `${99 + paddingLeft}px`,
    };
    let folderKeys = children && Object.keys(children).filter(child => children[child].edge && children[child].edge.node.isDir) || [];
    folderKeys = this._childSort(folderKeys, this.props.sort, this.props.reverse, children, 'folder');
    let fileKeys = children && Object.keys(children).filter(child => children[child].edge && !children[child].edge.node.isDir) || [];
    fileKeys = this._childSort(fileKeys, this.props.sort, this.props.reverse, children, 'files');
    const childrenKeys = folderKeys.concat(fileKeys);
    // declare css here
    const folderRowCSS = classNames({
      Folder__row: true,
      'Folder__row--expanded': state.expanded,
      'Folder__row--hover': state.hover,
    });
    const folderChildCSS = classNames({
      Folder__child: true,
      hidden: !state.expanded,
    });
    const folderNameCSS = classNames({
      'Folder__cell Folder__cell--name': true,
      'Folder__cell--open': state.expanded,
      hidden: state.renameEditMode,
    });
    const folderCSS = classNames({
      Folder: true,
      'Folder--highlight': isOver,
      'Folder--background': props.isDragging,
    });
    const renameCSS = classNames({
      'File__cell File__cell--edit': true,
      hidden: !state.renameEditMode,
    });

    return (
      <div
        style={props.style}
        className={folderCSS}
      >
        <div
          className={folderRowCSS}
          style={rowStyle}
          onClick={evt => this._expandSection(evt)}
        >
          <div className={folderNameCSS}>
            <div className="Folder__icon" />
            <div className="Folder__name">
              {folderName}
            </div>
          </div>
          <div className={renameCSS}>

            <div className="File__container">
              <input
                ref={(input) => { this.reanmeInput = input; }}
                placeholder="Rename File"
                type="text"
                className="File__input"
                onKeyUp={(evt) => { this._updateFileName(evt); }}
              />
            </div>
            <div className="flex justify-space-around">
              <button
                type="button"
                className="File__btn--round File__btn--cancel"
                onClick={() => { this._clearState(); }}
              />
              <button
                type="button"
                className="File__btn--round File__btn--add"
                onClick={() => { this._triggerMutation(); }}
              />
            </div>
          </div>
          <div className="Folder__cell Folder__cell--size" />
          <div className="Folder__cell Folder__cell--date">
            {Moment((node.modifiedAt * 1000), 'x').fromNow()}
          </div>
          <div className="Folder__cell Folder__cell--menu">
            <ActionsMenu
              edge={props.fileData.edge}
              mutationData={props.mutationData}
              mutations={props.mutations}
              addFolderVisible={this._addFolderVisible}
              folder
              section={props.section}
              renameEditMode={this._renameEditMode}
              fullEdge={props.fileData}
              isLocal={isLocal}
              isDownloading={state.isDownloading || props.isDownloading}
              setFolderIsDownloading={this._setFolderIsDownloading}
            />
          </div>
        </div>
        <div className={folderChildCSS}>
          { state.expanded
              && childrenKeys.map((file, fileIndex) => {
                if ((children
                  && children[file]
                  && children[file].edge
                  && children[file].edge.node.isDir)) {
                  return (
                    <Folder
                      filename={file}
                      index={fileIndex}
                      key={children[file].edge.node.key}
                      ref={children[file].edge.node.key}
                      mutations={props.mutations}
                      mutationData={props.mutationData}
                      fileData={children[file]}
                      isSelected={state.isSelected}
                      multiSelect={props.multiSelect}
                      setIncomplete={this._setIncomplete}
                      checkParent={this._checkParent}
                      setState={this._setState}
                      setParentHoverState={this._setHoverState}
                      expanded={state.expanded}
                      setParentDragFalse={() => this.setState({ isDragging: false })}
                      setParentDragTrue={this._checkHover}
                      parentIsDragged={state.isDragging || props.parentIsDragged}
                      childrenState={props.childrenState}
                      listRef={props.listRef}
                      updateChildState={props.updateChildState}
                      isDownloading={state.isDownloading || props.isDownloading}
                      codeDirUpload={props.codeDirUpload}
                      checkLocal={props.checkLocal}
                    />
                  );
                } if ((children
                  && children[file]
                  && children[file].edge
                  && !children[file].edge.node.isDir)) {
                  return (
                    <File
                      filename={file}
                      mutations={props.mutations}
                      mutationData={props.mutationData}
                      ref={children[file].edge.node.key}
                      fileData={children[file]}
                      key={children[file].edge.node.key}
                      isSelected={state.isSelected}
                      multiSelect={props.multiSelect}
                      checkParent={this._checkParent}
                      expanded={state.expanded}
                      setParentHoverState={this._setHoverState}
                      setParentDragFalse={(() => this.setState({ isDragging: false }))}
                      setParentDragTrue={this._checkHover}
                      isOverChildFile={state.isOverChildFile}
                      updateParentDropZone={this._updateDropZone}
                      isDownloading={state.isDownloading || props.isDownloading}
                      childrenState={props.childrenState}
                      updateChildState={props.updateChildState}
                    />
                  );
                } if (children[file]) {
                  return (<div key={`${file}_empty`} />);
                }
                return (<div key={`${file}_loading`}>Loading</div>);
              })
          }
        </div>
      </div>
    );
  }
}


export default Folder;
