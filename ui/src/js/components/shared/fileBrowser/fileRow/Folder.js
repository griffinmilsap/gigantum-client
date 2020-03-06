// vendor
import React, { Component } from 'react';
import classNames from 'classnames';
import Moment from 'moment';
import { DragSource, DropTarget } from 'react-dnd';
import { NativeTypes } from 'react-dnd-html5-backend';
import { boundMethod } from 'autobind-decorator';
import ReactTooltip from 'react-tooltip';
// components
import ActionsMenu from './ActionsMenu';
import File from './File';
import AddSubfolder from './AddSubfolder';
import DatasetActionsMenu from './dataset/DatasetActionsMenu';
// utils
import Connectors from '../utilities/Connectors';
// assets
import './Folder.scss';


class Folder extends Component {
  constructor(props) {
    super(props);

    this.state = {
      isDragging: props.isDragging,
      expanded: this.props.childrenState[this.props.fileData.edge.node.key].isExpanded || false,
      isSelected: (props.isSelected || this.props.childrenState[this.props.fileData.edge.node.key].isSelected) || false,
      isIncomplete: this.props.childrenState[this.props.fileData.edge.node.key].isIncomplete || false,
      hoverId: '',
      isOver: false,
      prevIsOverState: false,
      addFolderVisible: this.props.childrenState[this.props.fileData.edge.node.key].isAddingFolder || false,
      renameEditMode: false,
      isOverChildFile: false,
      renameValue: props.filename,
      isDownloading: false,
      forceUpdate: false,
    };
  }


  static getDerivedStateFromProps(nextProps, state) {
    let isSelected = (nextProps.multiSelect === 'none') ? false : state.isSelected;
    isSelected = ((nextProps.multiSelect === 'all') && !state.forceUpdate) ? true : isSelected;

    const isIncomplete = ((nextProps.multiSelect === 'none') || (nextProps.multiSelect === 'all'))
      ? false
      : state.isIncomplete;
    return {
      ...state,
      isOver: nextProps.isOver,
      prevIsOverState: state.isOver,
      isSelected,
      isIncomplete,
      forceUpdate: false,

    };
  }

  componentDidUpdate(prevProps, prevState, snapshot) {
    if (this.state.renameEditMode) {
      this.reanmeInput.focus();
    }
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
    *  @param {} -
    *  calls parent refetch method
    *  @return {boolean}
    */
  _refetch = () => {
    const { props } = this;
    props.refetch();
  }

  /**
    *  @param {boolean} isSelected
    *  sets child elements to be selected and current folder item
    *  @return {}
    */
  _setSelected = (evt, isSelected) => {
    // evt.preventDefault();
    evt.stopPropagation();
    const { props, state } = this;
    props.updateChildState(
      props.fileData.edge.node.key,
      isSelected,
      false,
      state.expanded,
      state.addFolderVisible,
    );

    this.setState(
      {
        isSelected,
        forceUpdate: true,
        isIncomplete: false,
      },
      () => {
        Object.keys(this.refs).forEach((ref) => {
          const folder = this.refs[ref];

          if (folder._setSelected) {
            folder._setSelected(evt, isSelected);
          } else if (folder.getDecoratedComponentInstance && folder.getDecoratedComponentInstance().getDecoratedComponentInstance) {
            folder.getDecoratedComponentInstance().getDecoratedComponentInstance()._setSelected(evt, isSelected);
          } else {
            folder.getDecoratedComponentInstance()._setSelected(evt, isSelected);
          }
        });
        if (props.checkParent) {
          props.checkParent();
        }
      },
    );
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
    *  @param {}
    *  sets parents element to selected if count matches child length
    *  @return {}
    */
  _setIncomplete = () => {
    this.setState({
      isIncomplete: true,
      isSelected: false,
    });
  }

  /**
    *  @param {}
    *  checks parent item
    *  @return {}
    */
  _checkParent = () => {
    const { props, state } = this;
    const { key } = props.fileData.edge.node;
    const {
      expanded,
      addFolderVisible,
      isSelected,
      isIncomplete,
    } = state;
    let checkCount = 0;
    let incompleteCount = 0;
    // TODO remove refs, this has been deprecated
    const refs = Object.keys(this.refs);

    refs.forEach((ref) => {
      const parentState = (this.refs[ref] && this.refs[ref].getDecoratedComponentInstance && this.refs[ref].getDecoratedComponentInstance().getDecoratedComponentInstance)
      ? this.refs[ref].getDecoratedComponentInstance().getDecoratedComponentInstance().state : this.refs[ref].getDecoratedComponentInstance().state;

      if (parentState.isSelected) {
        checkCount += 1;
      }
      if (parentState.isIncomplete) {
        incompleteCount += 1;
      }
    });

    if ((checkCount === 0) && (incompleteCount === 0)) {
      props.updateChildState(key, false, false, expanded, addFolderVisible);
      this.setState(
        {
          isIncomplete: false,
          isSelected: false,
        },
        () => {
          if (props.checkParent) {
            props.checkParent();
          }
        },
      );
    } else if (checkCount === Object.keys(this.refs).length && isSelected) {
      props.updateChildState(key, true, false, expanded, addFolderVisible);
      this.setState(
        {
          isIncomplete: false,
          isSelected: true,
        },
        () => {
          if (props.checkParent) {
            props.checkParent();
          }
        },
      );
    } else {
      props.updateChildState(key, false, true, expanded, addFolderVisible);

      this.setState(
        {
          isIncomplete: true,
          isSelected: false,
        },
        () => {
          if (props.setIncomplete) {
            props.setIncomplete();
          }
        },
      );
    }
  }

  /**
    *  @param {Object} evt
    *  sets item to expanded
    *  @return {}
    */
  _expandSection = (evt) => {
    const { props, state } = this;
    const { classList } = evt.target;
    const { key } = props.fileData.edge.node;
    const {
      addFolderVisible,
      expanded,
      isIncomplete,
      isSelected,
    } = state;

    if (!classList.contains('Folder__btn') &&
      !classList.contains('ActionsMenu__item') &&
      !classList.contains('Btn--round') &&
      !classList.contains('DatasetActionsMenu__item') &&
      !classList.contains('File__btn--round')) {
      this.setState({ expanded: !state.expanded }, () => {
        props.updateChildState(key, isSelected, isIncomplete, expanded, addFolderVisible);
      });
    }
    if (evt.target.classList.contains('Btn__addFolder')) {
      this.setState({ expanded: true }, () => {
        props.updateChildState(key, isSelected, isIncomplete, expanded, addFolderVisible);
      });
    }
  }

  /**
    *  @param {jsx} render
    *  sets elements to be selected and parent
    */
  connectDND = (render) => {
    const { props, state } = this;
    let renderType;

    if ((state.isDragging || props.parentIsDragged) && !props.readOnly) {
      renderType = props.connectDragSource(render);
    } else {
      renderType = props.connectDropTarget(render);
    }

    return renderType;
  }

  /**
    *  @param {}
    *  sets dragging state
    */
  _mouseEnter = () => {
    const { props } = this;
    if (props.setParentDragFalse) {
      props.setParentDragFalse();
    }
    this.setState({ isDragging: true, isHovered: true });
  }

  /**
    *  @param {}
    *  sets dragging state
    *  @return {}
    */
  _mouseLeave = () => {
    const { props } = this;
    if (props.setParentDragTrue) {
      props.setParentDragTrue();
    }
    this.setState({ isDragging: false, isHovered: false });
  }

  /**
    *  @param {}
    *  sets dragging state to true
    *  @return {}
    */
  _checkHover = () => {
    const { state } = this;
    if (state.isHovered && !state.isDragging) {
      this.setState({ isDragging: true });
    }
  }

  /**
      *  @param {}
      *  sets addFolderVisible state
      *  @return {}
    */
  _addFolderVisible = (reverse) => {
    const { props, state } = this;
    const {
      isSelected,
      isIncomplete,
      expanded,
      addFolderVisible,
    } = state;
    const { updateChildState, fileData } = props;
    if (reverse) {
      updateChildState(
        fileData.edge.node.key,
        isSelected,
        isIncomplete,
        expanded,
        !addFolderVisible,
      );

      this.setState({ addFolderVisible: !addFolderVisible });
    } else {
      updateChildState(
        fileData.edge.node.key,
        isSelected,
        isIncomplete,
        expanded,
        false,
      );
      this.setState({ addFolderVisible: false });
    }
  }

  /**
    *  @param {}
    *  checks if folder refs has props.isOver === true
    *  @return {boolean}
    */
  _checkRefs = () => {
    let isOver = this.props.isOverCurrent || this.props.isOver;
    // this.state.isOverChildFile,

    const { refs } = this;

    Object.keys(refs).forEach((childname) => {
      if (refs[childname].getDecoratedComponentInstance &&
        refs[childname].getDecoratedComponentInstance() &&
        refs[childname].getDecoratedComponentInstance().getDecoratedComponentInstance &&
        refs[childname].getDecoratedComponentInstance().getDecoratedComponentInstance()) {
        const child = refs[childname].getDecoratedComponentInstance().getDecoratedComponentInstance();
        if (child.props.fileData && !child.props.fileData.edge.node.isDir) {
          if (child.props.isOverCurrent) {
            isOver = true;
          }
        }
      }
    });

    return (isOver);
  }

  /**
    *  @param {event}
    *  @param {boolean} hover - boolean that sets if the component should show a hover state
    *  sets hover state
    *  @return {}
    */
  _setHoverState = (evt, hover) => {
    const { props } = this;
    evt.preventDefault();
    evt.stopPropagation();
    this.setState({ hover });

    if (props.setParentHoverState && hover) {
      const fakeEvent = {
        preventDefault: () => {},
        stopPropagation: () => {},
      };
      props.setParentHoverState(fakeEvent, false);
    }
  }

  /**
    *  @param {event}
    *  sets dragging state
    *  @return {}
    */
  _updateFileName = (evt) => {
    this.setState({ renameValue: evt.target.value });
  }

  /**
    *  @param {event}
    *  sumbit or clear
    *  @return {}
    */
  _submitCancel = (evt, folderName) => {
    const { state } = this;
    if ((evt.key === 'Enter') && (state.renameValue !== folderName)) {
      this._triggerMutation();
    }

    if (evt.key === 'Escape') {
      this._clearState();
    }
  }

  /**
    *  @param {}
    *  sets state on a boolean value
    *  @return {}
    */
  _clearState = () => {
    const { filename } = this.props;
    this.setState({
      renameValue: filename,
      renameEditMode: false,
    });
  }

  /**
    *  @param {}
    *  sets state on a boolean value
    *  @return {}
    */
  _triggerMutation = () => {
    const { props, state } = this;
    const { fileData } = props;
    const fileKeyArray = fileData.edge.node.key.split('/');
    fileKeyArray.pop();
    fileKeyArray.pop();
    const folderKeyArray = fileKeyArray;
    const folderKey = folderKeyArray.join('/');
    const removeIds = [fileData.edge.node.id];
    const currentHead = fileData;

    const searchChildren = (parent) => {
      if (parent.children) {
        Object.keys(parent.children).forEach((childKey) => {
          if (parent.children[childKey].edge) {
            removeIds.push(parent.children[childKey].edge.node.id);
            searchChildren(parent.children[childKey]);
          }
        });
      }
    };

    searchChildren(currentHead);

    const data = {
      newKey: (folderKey === '') ? `${state.renameValue}/` : `${folderKey}/${state.renameValue}/`,
      edge: fileData.edge,
      removeIds,
    };
    if (props.section !== 'data') {
      props.mutations.moveLabbookFile(data, () => {
        this._clearState();
      });
    } else {
      props.mutations.moveDatasetFile(data, () => {
        this._clearState();
      });
    }
  }

  /**
    *  @param {boolean} renameEditMode -sets
    *  sets hover state
    *  @return {}
    */
  _renameEditMode = (renameEditMode) => {
    this.setState({ renameEditMode });
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
      if ((type === 'az') || (type === 'size') && (section === 'folder')) {
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
    const { node } = props.fileData.edge;
    const isLocal = props.checkLocal(props.fileData);
    const cantDrag = !isLocal && props.section === 'data';
    const { children, index } = props.fileData;
    const { isOver } = props;
    const splitKey = node.key.split('/');
    const folderName = props.filename;
    const paddingLeft = 40 * index;
    const rowStyle = { paddingLeft: `${paddingLeft}px` };
    const addRowStyle = {
      paddingLeft: `${paddingLeft + 155}px`,
      backgroundPositionX: `${112 + paddingLeft}px`,
    };
    let folderKeys = children && Object.keys(children).filter(child => children[child].edge && children[child].edge.node.isDir) || [];
    folderKeys = this._childSort(folderKeys, props.sort, props.reverse, children, 'folder');
    let fileKeys = children && Object.keys(children).filter(child => children[child].edge && !children[child].edge.node.isDir) || [];
    fileKeys = this._childSort(fileKeys, props.sort, props.reverse, children, 'files');
    const childrenKeys = folderKeys.concat(fileKeys);
    const isUntrackedDirectory = (node.key === 'untracked/')
      && (props.section !== 'data');

    // declare css here
    const folderRowCSS = classNames({
      Folder__row: true,
      'Folder__row--expanded': state.expanded,
      'Folder__row--hover': state.hover,
      'Folder__row--noDrag': props.isDragging && cantDrag,
      'Folder__row--canDrag': props.isDragging && !cantDrag,
    });
    const buttonCSS = classNames({
      CheckboxMultiselect: true,
      CheckboxMultiselect__uncheck: !state.isSelected && !state.isIncomplete,
      CheckboxMultiselect__check: state.isSelected && !state.isIncomplete,
      CheckboxMultiselect__partial: state.isIncomplete,
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
      'Folder--dragging': props.isDragging,
      'Folder--highlight': isOver,
    });
    const renameCSS = classNames({
      'File__cell File__cell--edit': true,
      hidden: !state.renameEditMode,
    });

    const folder = (
      <div
        onMouseOver={(evt) => { this._setHoverState(evt, true); }}
        onMouseOut={(evt) => { this._setHoverState(evt, false); }}
        onMouseLeave={() => { this._mouseLeave(); }}
        onMouseEnter={() => { this._mouseEnter(); }}
        style={props.style}
        className={folderCSS}
      >
        <div
          className={folderRowCSS}
          style={rowStyle}
          onClick={evt => this._expandSection(evt)}
        >
          {
            !props.readOnly
            && (
            <button
              disabled={node.key === 'untracked/'}
              type="button"
              className={buttonCSS}
              onClick={evt => this._setSelected(evt, !state.isSelected)}
            />
            )
          }
          <div className={folderNameCSS}>
            <div className="Folder__icon" />
            <div
              className="Folder__name"
              data-tip={folderName}
              data-for="Tooltip--folder"
            >
              {folderName}
            </div>
            <ReactTooltip
              place="bottom"
              id="Tooltip--folder"
              delayShow={500}
            />
            { isUntrackedDirectory
              && (
              <div
                className="Folder__info"
                data-tip="Files in this folder will not be versioned or synced."
                data-for="Tooltip--untracked"
              />
              )
            }
            { isUntrackedDirectory
              && (
              <ReactTooltip
                place="bottom"
                id="Tooltip--untracked"
              />
              )
            }
          </div>
          <div className={renameCSS}>

            <div className="File__container">
              <input
                draggable
                ref={(input) => { this.reanmeInput = input; }}
                placeholder="Rename File"
                type="text"
                className="File__input"
                value={state.renameValue}
                maxLength="255"
                onDragStart={(evt) => { evt.preventDefault(); evt.stopPropagation(); }}
                onChange={(evt) => { this._updateFileName(evt); }}
                onKeyDown={(evt) => { this._submitCancel(evt, folderName); }}
              />
            </div>
            <div className="flex justify-space-around">
              <button
                type="button"
                className="File__btn--round File__btn--cancel File__input--rename-cancel"
                onClick={() => { this._clearState(); }}
              />
              <button
                type="button"
                className="File__btn--round File__btn--add File__input--rename-add"
                disabled={state.renameValue === folderName}
                onClick={() => { this._triggerMutation(); }}
              />
            </div>
          </div>
          <div className="Folder__cell Folder__cell--size" />
          <div className="Folder__cell Folder__cell--date">
            {Moment((node.modifiedAt * 1000), 'x').fromNow()}
          </div>
          <div className="Folder__cell Folder__cell--menu">
            {
              !props.readOnly
              && (
                <ActionsMenu
                  edge={props.fileData.edge}
                  mutationData={props.mutationData}
                  mutations={props.mutations}
                  addFolderVisible={this._addFolderVisible}
                  fileData={props.fileData}
                  section={props.section}
                  isLocal={isLocal}
                  folder
                  renameEditMode={this._renameEditMode}
                />
              )
            }
            { (props.section === 'data')
              && (
              <DatasetActionsMenu
                edge={props.fileData.edge}
                mutationData={props.mutationData}
                mutations={props.mutations}
                addFolderVisible={this._addFolderVisible}
                folder
                renameEditMode={this._renameEditMode}
                section={props.section}
                fullEdge={props.fileData}
                isDownloading={state.isDownloading || props.isDownloading}
                parentDownloading={props.parentDownloading}
                setFolderIsDownloading={this._setFolderIsDownloading}
                isLocal={isLocal}
                isDragging={props.isDragging}
              />
              )
            }
          </div>
        </div>
        <div className={folderChildCSS}>
          { state.expanded
            && (
            <AddSubfolder
              rowStyle={addRowStyle}
              key={`${node.key}__subfolder`}
              folderKey={node.key}
              mutationData={props.mutationData}
              mutations={props.mutations}
              setAddFolderVisible={this._addFolderVisible}
              addFolderVisible={state.addFolderVisible}
            />
            )
          }
          { state.expanded
            && childrenKeys.map((file, index) => {
              if ((children
                && children[file]
                && children[file].edge
                && children[file].edge.node.isDir)) {
                return (
                  <FolderDND
                    filename={file}
                    index={index}
                    readOnly={props.readOnly}
                    key={children[file].edge.node.key}
                    ref={children[file].edge.node.key}
                    mutations={props.mutations}
                    mutationData={props.mutationData}
                    fileData={children[file]}
                    isLocal={props.checkLocal(children[file])}
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
                    parentDownloading={state.downloadingAll}
                    section={props.section}
                    relay={props.relay}
                    isDownloading={state.isDownloading || props.isDownloading}
                    fileSizePrompt={props.fileSizePrompt}
                    checkLocal={props.checkLocal}
                    containerStatus={props.containerStatus}
                    refetch={props.refetch}
                  />
                );
              } if ((children
                  && children[file]
                  && children[file].edge
                  && !children[file].edge.node.isDir)) {
                return (
                  <File
                    filename={file}
                    readOnly={props.readOnly}
                    isLocal={props.checkLocal(children[file])}
                    mutations={props.mutations}
                    mutationData={props.mutationData}
                    ref={children[file].edge.node.key}
                    fileData={children[file]}
                    key={children[file].edge.node.key}
                    isSelected={state.isSelected}
                    multiSelect={props.multiSelect}
                    checkParent={this._checkParent}
                    section={props.section}
                    expanded={state.expanded}
                    setParentHoverState={this._setHoverState}
                    setParentDragFalse={(() => this.setState({ isDragging: false }))}
                    setParentDragTrue={this._checkHover}
                    isOverChildFile={state.isOverChildFile}
                    updateParentDropZone={this._updateDropZone}
                    childrenState={props.childrenState}
                    parentDownloading={state.downloadingAll}
                    isDownloading={state.isDownloading || props.isDownloading}
                    updateChildState={props.updateChildState}
                    checkLocal={props.checkLocal}
                    containerStatus={props.containerStatus}
                  />
                );
              } if (children[file]) {
                return (<div key={`${file}${index}`} />);
              }
              return (<div key={`${file}${index}`}>Loading</div>);
            })
          }
        </div>
      </div>
    );

    return (
      this.connectDND(folder)
    );
  }
}

const FolderDND = DragSource(
  'card',
  Connectors.dragSource,
  Connectors.dragCollect,
)(DropTarget(
  ['card', NativeTypes.FILE],
  Connectors.targetSource,
  Connectors.targetCollect,
)(Folder));


export default FolderDND;
